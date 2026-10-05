"""Independent quality checks for compiled readers and human semantic review."""

import argparse
import json
import re
from pathlib import Path


REQUIRED_IDS = (
    "chapterSelectBtn",
    "chapterDropdown",
    "audioTrack",
    "drawerToggleBtn",
    "controlDrawer",
)
REQUIRED_FUNCTIONS = (
    "switchChapter",
    "handleSentenceClick",
    "toggleGlobalPlay",
    "syncPlayback",
)


def _check_temporal_integrity(content: str) -> list:
    """Audit compiled HTML for sentence timeline overlaps and duplicate word timestamps."""
    errors = []
    chapter_blocks = re.findall(r'<section\b[^>]*class="chapter-section[^>]*data-ch="(\d+)"[^>]*>(.*?)</section>', content, re.DOTALL)
    word_re = re.compile(r'<span class="w"[^>]*?data-s="([^"]+)"[^>]*?data-e="([^"]+)"[^>]*?(?:data-timing-source="([^"]+)")?[^>]*?>([^<]*)</span>')
    sent_re = re.compile(r'<div class="sentence-unit"[^>]*?id="([^"]+)"[^>]*?data-start="([^"]+)"[^>]*?data-end="([^"]+)"[^>]*?data-matched="([^"]+)"', re.DOTALL)

    for ch_num, ch_content in chapter_blocks:
        units = ch_content.split('<div class="sentence-unit"')
        prev_end = None
        for u in units[1:]:
            m = sent_re.search('<div class="sentence-unit"' + u[:400])
            if not m:
                continue
            uid, s_str, e_str, matched_str = m.group(1), m.group(2), m.group(3), m.group(4)
            if matched_str != "1" or s_str == "null" or e_str == "null":
                continue
            try:
                start = float(s_str)
                end = float(e_str)
            except ValueError:
                continue
            if prev_end is not None and start < (prev_end - 0.05):
                errors.append(f"Ch {ch_num} {uid}: sentence overlap (starts at {start:.2f}s before previous ended at {prev_end:.2f}s)")
            prev_end = max(prev_end or 0.0, end)

            # Check for adjacent duplicate word timestamps on observed words
            text_part = u.split('<div class="inspect-panel"')[0]
            span_tags = re.findall(r'<span class="w"([^>]*)>([^<]*)</span>', text_part)
            prev_s = None
            prev_w = None
            prev_src = None
            for attrs, text in span_tags:
                m_s = re.search(r'data-s="([^"]+)"', attrs)
                m_src = re.search(r'data-timing-source="([^"]+)"', attrs)
                s_val = m_s.group(1) if m_s else None
                src_val = m_src.group(1) if m_src else "observed"
                is_lexical = bool(re.search(r'[a-zA-Z0-9]', text))
                prev_is_lexical = bool(re.search(r'[a-zA-Z0-9]', prev_w or ""))
                if s_val is not None and s_val != "null" and s_val == prev_s and (src_val == "observed" or prev_src == "observed") and is_lexical and prev_is_lexical:
                    errors.append(f"Ch {ch_num} {uid}: duplicate word start timestamp ({s_val}s) between '{prev_w}' and '{text}'")
                    break
                prev_s = s_val
                prev_w = text
                prev_src = src_val
    return errors


def smoke_check_html(html_path: Path, expected_chapters=None):
    """Check the static reader contract without pretending to be a real browser."""
    html_path = Path(html_path)
    errors = []
    try:
        content = html_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return {"status": "failed", "errors": [f"cannot read HTML: {exc}"]}
    if not content.lstrip().startswith("<!DOCTYPE html>"):
        errors.append("missing HTML5 doctype")
    if not re.search(r'<html\b[^>]*\blang="[a-z]{2}', content, re.IGNORECASE):
        errors.append("missing two-letter html lang attribute")
    if 'name="viewport"' not in content:
        errors.append("missing responsive viewport metadata")
    for element_id in REQUIRED_IDS:
        if f'id="{element_id}"' not in content:
            errors.append(f"missing required element id: {element_id}")
    for function_name in REQUIRED_FUNCTIONS:
        if not re.search(rf"function\s+{re.escape(function_name)}\s*\(", content):
            errors.append(f"missing required JavaScript function: {function_name}")
    chapters = re.findall(r'<section\b[^>]*class="chapter-section[^>]*\bdata-ch="(\d+)"', content)
    if expected_chapters is not None and len(chapters) != expected_chapters:
        errors.append(f"expected {expected_chapters} chapter sections, found {len(chapters)}")
    if not re.search(r'<audio\b[^>]*\bid="audioTrack"[^>]*\bsrc="[^"]+"', content):
        errors.append("audioTrack has no source")
    if re.search(r'<h1 class="book-title">\s*([^<\n]+)\s*<br>\s*\1\s*</h1>', content, re.IGNORECASE):
        errors.append("found duplicate chapter title heading (e.g. TITLE<br>Title)")
    style_blocks = re.findall(r"<style[^>]*>(.*?)</style>", content, re.DOTALL)
    for idx, css in enumerate(style_blocks, 1):
        if css.count("{") != css.count("}"):
            errors.append(f"style block {idx} has unbalanced braces (open={css.count('{')}, close={css.count('}')})")
    errors.extend(_check_temporal_integrity(content))
    return {
        "status": "passed" if not errors else "failed",
        "errors": errors,
        "chapter_count": len(chapters),
    }


def validate_semantic_review(review_path: Path, required_chapters=None):
    """Validate a human review record; semantic correctness is not auto-inferred."""
    errors = []
    try:
        data = json.loads(Path(review_path).read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        return {"status": "failed", "errors": [f"invalid semantic review JSON: {exc}"]}
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        errors.append("semantic review schema_version must be 1")
    if data.get("status") != "approved":
        errors.append("semantic review status must be approved")
    for key in ("reviewer", "reviewed_at", "method"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            errors.append(f"semantic review missing {key}")
    samples = data.get("samples")
    if not isinstance(samples, list) or not samples:
        errors.append("semantic review needs at least one sampled chapter")
        samples = []
    seen_chapters = set()
    required_checks = ("translation_accuracy", "alignment_semantics", "vocabulary_quality")
    for sample in samples:
        if not isinstance(sample, dict) or not isinstance(sample.get("chapter"), int):
            errors.append("semantic review sample has invalid chapter")
            continue
        chapter = sample["chapter"]
        seen_chapters.add(chapter)
        if not isinstance(sample.get("sentence_ids"), list) or not sample["sentence_ids"]:
            errors.append(f"chapter {chapter}: semantic review has no sentence samples")
        checks = sample.get("checks")
        if not isinstance(checks, dict) or any(checks.get(key) is not True for key in required_checks):
            errors.append(f"chapter {chapter}: all semantic checks must be explicitly true")
    if required_chapters is not None and not set(required_chapters).issubset(seen_chapters):
        missing = sorted(set(required_chapters) - seen_chapters)
        errors.append(f"missing semantic review samples for chapters: {missing}")
    return {"status": "passed" if not errors else "failed", "errors": errors, "sample_count": len(samples)}


def main():
    parser = argparse.ArgumentParser(description="Check reader quality contracts")
    parser.add_argument("html", type=Path)
    parser.add_argument("--semantic-review", type=Path)
    args = parser.parse_args()
    smoke = smoke_check_html(args.html)
    print(json.dumps({"smoke": smoke}, ensure_ascii=False, indent=2))
    if args.semantic_review:
        semantic = validate_semantic_review(args.semantic_review)
        print(json.dumps({"semantic": semantic}, ensure_ascii=False, indent=2))
        return 0 if smoke["status"] == semantic["status"] == "passed" else 1
    return 0 if smoke["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
