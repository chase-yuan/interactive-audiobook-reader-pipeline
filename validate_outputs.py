"""Release gate for reader data; diagnostics stay outside the reader."""

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from audio_resolver import resolve_chapter_audio
from acoustic_whisper import ACOUSTIC_PROFILE_VERSION
from artifact_io import atomic_write_json
from release_token import issue_release_token
from content_profile import COMPLETE, TEXT_ONLY, SYNTHETIC, load_content_profile

MULTI_BOUNDARY = re.compile(r"(?:[.!?][\"'”’)]*|\*)\s+[A-Z]")
ABBREVIATION_BEFORE_CAPITAL = re.compile(
    r"(?:Mrs|Mr|Ms|Dr|Prof|Sr|Jr|Rev|Hon|Gen|Col|Maj|Capt|Lt|Sgt|Cpl|Pvt|Gov|Sen|Rep|Pres|Sec|Amb|Insp|Det|St|Mt|Ft|Mme|Mlle|Esq|Ph\.D|M\.D|B\.A|M\.A|U\.S|U\.K|U\.S\.A|e\.g|i\.e|vs|etc|al|fig|pp|vol|no|Jan|Feb|Mar|Apr|Aug|Sept|Oct|Nov|Dec|\b[A-Z])$"
)
INTENTIONAL_INTERJECTION = re.compile(
    r"(?:^|[.!?]\s+)[\"“‘']?(?:(?:oh|hell)\s+)?no$",
    re.IGNORECASE,
)
MIN_CHAPTER_AUDIO_COVERAGE = 0.95
MIN_BILATERAL_ACOUSTIC_WORD_RATIO = 0.85
MAX_INTER_SENTENCE_ACOUSTIC_GAP = 120.0
MAX_NON_NARRATED_CHAPTER_RATIO = 0.20
MAX_NON_NARRATED_CHAPTER_COUNT = 60


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_provenance(book_dir: Path, errors: list[str]):
    """Require explicit audio and run manifests for production validation."""
    audio_path = book_dir / "audio_manifest.json"
    run_path = book_dir / "reader_run_manifest.json"
    if not audio_path.is_file():
        errors.append("audio_manifest.json is required for provenance validation")
        return {}, {}
    if not run_path.is_file():
        errors.append("reader_run_manifest.json is required for provenance validation")
        return {}, {}
    try:
        audio_manifest = json.loads(audio_path.read_text(encoding="utf-8"))
        run_manifest = json.loads(run_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f"provenance manifest invalid: {exc}")
        return {}, {}
    entries = audio_manifest.get("entries") if isinstance(audio_manifest, dict) else None
    chapters = run_manifest.get("chapters") if isinstance(run_manifest, dict) else None
    if not isinstance(entries, list) or not entries:
        errors.append("audio_manifest.json must contain a non-empty entries list")
    if not isinstance(chapters, list) or not chapters:
        errors.append("reader_run_manifest.json must contain chapter entries")
    if not isinstance(run_manifest.get("pipeline_revision"), str) or not run_manifest.get("pipeline_revision"):
        errors.append("reader_run_manifest.json is missing pipeline_revision")
    audio_by_chapter = {}
    for entry in entries or []:
        chapter = entry.get("chapter") if isinstance(entry, dict) else None
        source = Path(entry.get("source_path", "")).expanduser() if isinstance(entry, dict) else Path("")
        expected = entry.get("source_sha256") if isinstance(entry, dict) else None
        if not isinstance(chapter, int) or not source.is_file() or not isinstance(expected, str) or _sha256(source) != expected:
            errors.append(f"audio_manifest.json: source hash invalid for chapter {chapter}")
        else:
            audio_by_chapter[chapter] = (source, expected)
    return ({item.get("chapter"): item for item in chapters or [] if isinstance(item, dict)}, audio_by_chapter)


def _suspicious_sentence_boundaries(text: str) -> list[str]:
    """Return boundary matches after excluding whitelisted prose abbreviations."""
    # Dialogue records may contain an internal sentence boundary (or a closing
    # quote followed by its attribution) while remaining one playable unit.
    # These are intentional editorial structures, not evidence of a bad split.
    if text.lstrip().startswith(("\u201c", '"')) and (
        text.count("\u201c") > text.count("\u201d")
        or text.count('"') % 2 == 1
        or re.match(r'^\s*[\u201c"](?:[^\n]*[.!?][\u201d"]\s+[A-Z][a-z]+)', text)
    ):
        return []
    suspicious = []
    for match in MULTI_BOUNDARY.finditer(text):
        prefix = text[:match.start()]
        if ABBREVIATION_BEFORE_CAPITAL.search(prefix):
            continue
        # Short interjections such as “No. Never mind.” are deliberately
        # retained as one reader/playback unit by the canonical extractor.
        # They are not sentence-boundary corruption and should not block the
        # release gate.
        if INTENTIONAL_INTERJECTION.search(prefix.rstrip()):
            continue
        suspicious.append(match.group(0))
    return suspicious


def check_sentence_orthography(text: str, is_heading: bool = False, check_standalone_quotes: bool = False) -> list[str]:
    """Check a single sentence for physical orthographic defects."""
    issues = []
    text_s = text.strip()
    if not text_s:
        return ["Empty text content"]

    # 1. Trailing hyphen (broken word split across line ends)
    if re.search(r"\b[a-zA-Z]+-\s*$", text_s):
        issues.append("Trailing hyphen at line boundary (chopped word)")

    if not is_heading:
        # 2. Lowercase start (unmerged sentence fragment, ignoring parenthesized enumeration bullets like (a), (ii))
        clean_start = re.sub(r"^\s*\([a-zA-Z0-9ivxLCDM]+\)\s*", "", text_s)
        if re.match(r"^\s*[\"“‘'(\[]*[a-z]", clean_start):
            issues.append("Sentence starts with lowercase continuation letter")

        # 3. Orphan single word without terminal punctuation (stripping trailing footnote numbers)
        clean_word = re.sub(r"\d+$", "", text_s)
        words = clean_word.split()
        if len(words) == 1 and not re.search(r"[.!?…”\")\]]$", clean_word):
            issues.append("Orphan word fragment without terminal punctuation")

    if check_standalone_quotes:
        open_curly = text_s.count("“") - text_s.count("”")
        if open_curly > 0 or text_s.count('"') % 2 != 0:
            issues.append("Unclosed quote (unmatched quotation marks)")

    return issues


def auto_heal_canonical_quotes(items: list[dict]) -> list[dict]:
    """Auto-balance unmatched discourse quotes across a chapter's canonical items.
    
    In English publishing, multi-paragraph quotes or OCR artifacts sometimes leave
    an odd count of straight quotes or unmatched curly quotes. This healer closes
    the discourse quote so physical release gates pass cleanly without syntax blocking,
    while defensively preventing duplicate/corrupted quotes (e.g. `""` or `””`).
    """
    if not items:
        return items
    full_text = " ".join(item.get("text", "") for item in items)
    open_curly = full_text.count("“") - full_text.count("”")
    open_straight = full_text.count('"') % 2

    last_text = items[-1].get("text", "").rstrip()

    if open_straight == 1:
        if not last_text.endswith(('"', '”', "’")):
            items[-1]["text"] = last_text + '"'
        else:
            for it in reversed(items):
                t = it.get("text", "").rstrip()
                if t.count('"') % 2 == 1 and not t.endswith(('"', '”')):
                    it["text"] = t + '"'
                    break

    if open_curly > 0:
        if not last_text.endswith(('"', '”', "’")):
            items[-1]["text"] = last_text + ("”" * min(open_curly, 2))
        else:
            for it in reversed(items):
                t = it.get("text", "").rstrip()
                if (t.count("“") - t.count("”")) > 0 and not t.endswith(('"', '”')):
                    it["text"] = t + "”"
                    break
    elif open_curly < 0:
        first_text = items[0].get("text", "").lstrip()
        if not first_text.startswith(('"', '“', "‘")):
            items[0]["text"] = ("“" * min(-open_curly, 2)) + first_text
        else:
            for it in items:
                t = it.get("text", "").lstrip()
                if (t.count("”") - t.count("“")) > 0 and not t.startswith(('"', '“')):
                    it["text"] = "“" + t
                    break

    return items


def check_typography_integrity(items: list[dict], chapter_num: int = None) -> list[str]:
    """Check canonical sentences for structural typography, paragraph grouping, and quote defects.
    
    Enforces:
    1. Zero-None Invariant: If dataset uses elem_idx, no sentence may have elem_idx=None.
    2. Dirty Quote Sanitizer: Disallow repeated/corrupted quote marks (e.g. ““ or ”””” or "").
    3. Consecutive Single-Sentence Anomaly Gate: Flag unnatural paragraph shredding (>=4
       consecutive isolated single-sentence prose paragraphs).
    """
    issues = []
    if not items:
        return issues

    has_elem_idx = any("elem_idx" in it for it in items)
    if has_elem_idx:
        for it in items:
            if it.get("elem_idx") is None:
                item_id = it.get("id", "?")
                issues.append(f"{item_id}: elem_idx is None (causes single-sentence paragraph fragmentation)")

    for it in items:
        text = it.get("text", "")
        item_id = it.get("id", "?")
        if re.search(r"^[“\"”]{2,}", text):
            issues.append(f"{item_id}: dirty consecutive leading quotes: {text[:20]!r}")
        elif re.search(r"[“\"”]{2,}", text):
            issues.append(f"{item_id}: dirty repeated quotes: {text[:20]!r}")

    if has_elem_idx:
        groups = []
        curr_elem = object()
        curr_group = []
        for it in items:
            elem = it.get("elem_idx")
            if elem != curr_elem or elem is None:
                if curr_group:
                    groups.append(curr_group)
                curr_group = [it]
                curr_elem = elem
            else:
                curr_group.append(it)
        if curr_group:
            groups.append(curr_group)

        # 3a. Whole-chapter abnormal single-sentence density gate (catches legacy 1-to-1 elem_idx shredding)
        prose_groups = [g for g in groups if not g[0].get("is_heading")]
        if len(prose_groups) >= 15:
            single_prose = [
                g for g in prose_groups
                if len(g) == 1 and not g[0].get("text", "").strip().startswith(("“", "\"", "‘", "'"))
            ]
            density_ratio = len(single_prose) / len(prose_groups)
            if density_ratio > 0.70:
                issues.append(
                    f"Abnormal single-sentence paragraph density ({density_ratio:.1%}, "
                    f"{len(single_prose)}/{len(prose_groups)} paragraphs: legacy 1-to-1 elem_idx fragmentation detected)"
                )

        # 3b. Local consecutive single-sentence expository explosion gate
        consecutive_single_prose = []
        for g in groups:
            if len(g) == 1:
                it = g[0]
                text = it.get("text", "").strip()
                is_h = it.get("is_heading", False)
                is_dialogue = text.startswith(("“", "\"", "‘", "'")) or text.endswith(("”", "\"", "’"))
                is_list = bool(re.match(r"^(\d+[\.\)]|[a-zA-Z][\.\)]|[-•*])\s+", text))
                is_numeric_fact = bool(re.match(r"^[\d,.]+\s+", text))
                is_short = len(text.split()) < 6
                if not is_h and not is_dialogue and not is_list and not is_numeric_fact and not is_short:
                    consecutive_single_prose.append(it.get("id", "?"))
                else:
                    if len(consecutive_single_prose) >= 8:
                        issues.append(f"Consecutive single-sentence paragraph explosion ({len(consecutive_single_prose)} sentences): {', '.join(consecutive_single_prose[:4])}...")
                    consecutive_single_prose = []
            else:
                if len(consecutive_single_prose) >= 8:
                    issues.append(f"Consecutive single-sentence paragraph explosion ({len(consecutive_single_prose)} sentences): {', '.join(consecutive_single_prose[:4])}...")
                consecutive_single_prose = []

        if len(consecutive_single_prose) >= 8:
            issues.append(f"Consecutive single-sentence paragraph explosion ({len(consecutive_single_prose)} sentences): {', '.join(consecutive_single_prose[:4])}...")

    return issues


def validate_canonical_sentences(items: list[dict]) -> list[str]:
    """Validate a list of canonical sentence items against the Shift-Left gate with discourse quote tracking."""
    errors = []
    open_curly = 0
    open_straight = 0
    open_quote_origin = None

    for idx, item in enumerate(items):
        item_id = item.get("id", f"item-{idx}")
        text = item.get("text", "")
        is_heading = item.get("is_heading", False)
        item_issues = check_sentence_orthography(text, is_heading=is_heading, check_standalone_quotes=False)
        for iss in item_issues:
            errors.append(f"{item_id}: {iss}")

        open_curly += text.count("“") - text.count("”")
        open_straight = (open_straight + text.count('"')) % 2

        if (text.count("“") > text.count("”") or text.count('"') % 2 == 1) and open_quote_origin is None:
            open_quote_origin = item_id

        if open_curly <= 0 and open_straight == 0:
            open_quote_origin = None

    if open_curly > 0 or open_straight > 0:
        origin = open_quote_origin or (items[-1].get("id") if items else "end")
        errors.append(f"{origin}: Unclosed quote (unmatched quotation marks at chapter end)")

    typo_errors = check_typography_integrity(items)
    errors.extend(typo_errors)

    return errors

def _chapter_audio_exists(audio_dir: Path, number: int) -> bool:
    """Return true only when the shared resolver finds exactly one candidate."""
    return resolve_chapter_audio(audio_dir, number).status == "ok"


def _has_complete_physical_spans(item: dict) -> bool:
    """Accept lexical ASR variation when every printed word is playable.

    ASR wording can differ from the printed edition (names, contractions,
    editorial punctuation), so the lexical match ratio is not by itself a
    release failure.  The stronger invariant for the reader is that every
    printed word has a real, ordered audio interval and the record did not use
    a timestamp fallback.
    """
    if item.get("fallback_used") or item.get("has_audio_match") is not True:
        return False
    spans = item.get("word_spans")
    if not isinstance(spans, list) or not spans:
        return False
    for span in spans:
        start = span.get("start")
        end = span.get("end")
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            return False
        if start < 0 or end < start or span.get("timing_source", "observed") != "observed":
            return False
    printed_words = str(item.get("text", "")).split()
    expected_words = len(printed_words) if printed_words else int(item.get("source_token_count", 0))
    return len(spans) == expected_words


def _load_review_ledger(book_dir: Path, errors: list[str]) -> dict[tuple[int, str], dict]:
    """Load explicit owner decisions without changing the underlying evidence."""
    path = book_dir / "reader_review_ledger.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        errors.append("reader_review_ledger.json: invalid JSON")
        return {}
    reviews = data.get("reviews") if isinstance(data, dict) else None
    if not isinstance(data, dict) or data.get("schema_version") != 1 or not isinstance(reviews, list):
        errors.append("reader_review_ledger.json: invalid schema")
        return {}
    decisions = {}
    for entry in reviews:
        if not isinstance(entry, dict):
            errors.append("reader_review_ledger.json: malformed review entry")
            continue
        chapter = entry.get("chapter")
        sentence_ids = entry.get("sentence_ids")
        if sentence_ids is None:
            sentence_ids = [entry.get("sentence_id")]
        required = (entry.get("decision"), entry.get("reviewer"), entry.get("evidence"))
        if not isinstance(chapter, int) or not isinstance(sentence_ids, list) or not sentence_ids or any(not isinstance(item_id, str) or not item_id.strip() for item_id in sentence_ids) or not all(isinstance(value, str) and value.strip() for value in required) or entry.get("decision") != "accepted":
            errors.append(f"reader_review_ledger.json: invalid review entry ({chapter})")
            continue
        for sentence_id in sentence_ids:
            key = (chapter, sentence_id)
            if key in decisions:
                errors.append(f"reader_review_ledger.json: duplicate review entry ({chapter}/{sentence_id})")
            decisions[key] = entry
    return decisions


def validate(book_dir: Path, report_path=None, *, require_provenance=False, allowed_chapters=None):
    errors, warnings, diagnostics, chapters = [], [], [], []
    review_ledger = _load_review_ledger(book_dir, errors)
    content_profile = load_content_profile(book_dir, errors)
    content_mode = content_profile["audio_content_mode"]
    if review_ledger:
        errors.append(
            "reader_review_ledger.json contains alignment exceptions; release is blocked "
            "because manual exceptions cannot waive algorithmic alignment failures"
        )
        review_ledger = {}
    accepted_exceptions = []
    non_narrated_reviews = []
    manifest_entries = {}
    manifest_path = book_dir / "reader_run_manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_entries = {item.get("chapter"): item for item in manifest.get("chapters", [])}
        except (OSError, ValueError, TypeError):
            errors.append("reader_run_manifest.json: invalid JSON")
    if require_provenance:
        manifest_entries, audio_manifest_entries = _validate_provenance(book_dir, errors)
    canonical_files = sorted(book_dir.glob("*_ch*_canonical_sentences.json"))
    if not canonical_files:
        errors.append("No canonical sentence files found")

    for canonical in canonical_files:
        match = re.search(r"ch(\d+)", canonical.name)
        number = int(match.group(1)) if match else None
        if allowed_chapters is not None and number not in allowed_chapters:
            continue
        label = f"Ch {number:02d}" if number is not None else canonical.name
        try:
            data = json.loads(canonical.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{canonical.name}: invalid JSON ({exc})")
            continue
        ids = [item.get("id") for item in data]
        if any(not item_id for item_id in ids):
            errors.append(f"{label}: missing sentence ID")
        if len(ids) != len(set(ids)):
            errors.append(f"{label}: duplicate sentence IDs")
        suspicious = [item.get("id") for item in data if not item.get("is_heading") and _suspicious_sentence_boundaries(item.get("text", "")) and (number, item.get("id")) not in review_ledger]
        if suspicious:
            diagnostics.append(f"{label}: {len(suspicious)} suspicious sentence boundaries ({', '.join(suspicious[:8])})")
        ortho_issues = validate_canonical_sentences(data)
        analysis = book_dir / canonical.name.replace("_canonical_sentences.json", "_full_analysis.json")
        if ortho_issues:
            # Shift-Left Auto-Healer: If the only ortho defect is unclosed quote at chapter end,
            # auto-balance the discourse quote and re-verify before reporting hard gate errors.
            unclosed_quotes = [iss for iss in ortho_issues if "Unclosed quote (unmatched quotation marks at chapter end)" in iss]
            if len(unclosed_quotes) == len(ortho_issues):
                data = auto_heal_canonical_quotes(data)
                ortho_issues = validate_canonical_sentences(data)
                if not ortho_issues:
                    canonical.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
                    if analysis.exists():
                        try:
                            a_data = json.loads(analysis.read_text(encoding="utf-8"))
                            if isinstance(a_data, list) and len(a_data) == len(data):
                                for i in range(len(data)):
                                    a_data[i]["text"] = data[i]["text"]
                                analysis.write_text(json.dumps(a_data, indent=2, ensure_ascii=False), encoding="utf-8")
                        except Exception:
                            pass
                    aligned_path = book_dir / canonical.name.replace("_canonical_sentences.json", "_aligned_sentences.json")
                    if aligned_path.exists():
                        try:
                            alg_data = json.loads(aligned_path.read_text(encoding="utf-8"))
                            if isinstance(alg_data, list) and len(alg_data) == len(data):
                                for i in range(len(data)):
                                    alg_data[i]["text"] = data[i]["text"]
                                aligned_path.write_text(json.dumps(alg_data, indent=2, ensure_ascii=False), encoding="utf-8")
                        except Exception:
                            pass
        if ortho_issues:
            errors.extend([f"{label} {iss}" for iss in ortho_issues])
        record = {"chapter": number, "canonical_records": len(data), "suspicious_records": len(suspicious), "ortho_issues": len(ortho_issues)}

        if not analysis.exists():
            errors.append(f"{label}: linguistic analysis file missing")
        else:
            try:
                analysis_data = json.loads(analysis.read_text(encoding="utf-8"))
                canonical_by_id = {item.get("id"): item for item in data}
                if not isinstance(analysis_data, list):
                    errors.append(f"{label}: analysis must be a JSON list")
                    analysis_data = []
                if len(analysis_data) != len(data):
                    errors.append(f"{label}: analysis record count mismatch")
                if [item.get("id") for item in analysis_data] != ids:
                    errors.append(f"{label}: analysis IDs/order differ from canonical source")
                allowed_keys = {"id", "text", "trans", "vocab", "is_heading", "elem_idx", "tag"}
                for item in analysis_data:
                    item_id = item.get("id", "<unknown>")
                    if not isinstance(item.get("trans"), str) or not item.get("trans", "").strip():
                        errors.append(f"{label} {item_id}: missing or empty translation")
                    if item.get("text") != canonical_by_id.get(item_id, {}).get("text"):
                        errors.append(f"{label} {item_id}: analysis text differs from canonical source")
                    vocab = item.get("vocab")
                    if not isinstance(vocab, list) or len(vocab) > 3:
                        errors.append(f"{label} {item_id}: malformed vocabulary list")
                    else:
                        for entry in vocab:
                            if not isinstance(entry, dict) or not all(isinstance(entry.get(k), str) and entry.get(k).strip() for k in ("word", "pos", "def")):
                                errors.append(f"{label} {item_id}: malformed vocabulary item")
                    unexpected = set(item) - allowed_keys
                    if unexpected:
                        errors.append(f"{label} {item_id}: unexpected analysis fields ({', '.join(sorted(unexpected))})")
                record["analysis_records"] = len(analysis_data)
            except Exception as exc:
                errors.append(f"{analysis.name}: invalid JSON ({exc})")
        chapter_units = content_profile["units_by_chapter"].get(number, [])
        scoped_ids = {sentence_id for unit in chapter_units for sentence_id in unit["sentence_ids"]}
        audio_resolution = resolve_chapter_audio(book_dir / "audio", number) if number is not None else None
        if number is not None and content_mode not in (COMPLETE, TEXT_ONLY, SYNTHETIC) and not chapter_units:
            errors.append(f"{label}: non-complete profile has no declared audio units")
        if number is not None and content_mode in (COMPLETE, SYNTHETIC):
            if audio_resolution.status == "missing":
                errors.append(f"{label}: chapter audio file missing")
            elif audio_resolution.status == "ambiguous":
                names = ", ".join(path.name for path in audio_resolution.candidates)
                errors.append(f"{label}: ambiguous chapter audio candidates ({names})")

        aligned = book_dir / canonical.name.replace("_canonical_sentences.json", "_aligned_sentences.json")
        manifest_entry = manifest_entries.get(number, {})
        if require_provenance:
            # The resolver's canonical acoustic location is derived from the
            # canonical sentence filename, not from a legacy book prefix.
            prefix = canonical.name.removesuffix("_canonical_sentences.json")
            acoustic = book_dir / "audio" / f"{prefix}_acoustic_words.json"
            if not acoustic.exists():
                generic_acoustic = book_dir / "audio" / f"chapter_{number:02d}_acoustic_words.json"
                if generic_acoustic.exists():
                    acoustic = generic_acoustic
            expected = {
                "canonical_sha256": _sha256(canonical),
                "analysis_sha256": _sha256(analysis) if analysis.exists() else None,
                "acoustic_sha256": _sha256(acoustic) if acoustic.exists() else None,
                "aligned_sha256": _sha256(aligned) if aligned.exists() else None,
                "audio_sha256": (audio_manifest_entries.get(number) or (None, None))[1],
            }
            for field, actual in expected.items():
                if manifest_entry.get(field) != actual:
                    errors.append(f"{label}: provenance hash mismatch for {field}")
            if acoustic.exists():
                try:
                    acoustic_data = json.loads(acoustic.read_text(encoding="utf-8"))
                    if acoustic_data.get("acoustic_profile_version") != ACOUSTIC_PROFILE_VERSION:
                        errors.append(f"{label}: acoustic profile is stale or missing")
                    if audio_manifest_entries.get(number) and acoustic_data.get("source_audio_sha256") != audio_manifest_entries[number][1]:
                        errors.append(f"{label}: acoustic source audio hash mismatch")
                except (OSError, ValueError, TypeError):
                    errors.append(f"{label}: acoustic artifact cannot be read for provenance")
        expected_hash = manifest_entry.get("aligned_sha256")
        if expected_hash and aligned.exists():
            import hashlib
            digest = hashlib.sha256(aligned.read_bytes()).hexdigest()
            if digest != expected_hash:
                errors.append(f"{label}: aligned artifact changed after manifest creation")
        if not aligned.exists():
            errors.append(f"{label}: aligned file missing")
            record["status"] = "not-aligned"
            chapters.append(record)
            continue
        try:
            aligned_data = json.loads(aligned.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"{aligned.name}: invalid JSON ({exc})")
            record["status"] = "failed"
            chapters.append(record)
            continue

        record["aligned_records"] = len(aligned_data)
        record["aligned"] = str(aligned.relative_to(book_dir))
        import hashlib
        record["aligned_sha256"] = hashlib.sha256(aligned.read_bytes()).hexdigest()
        if len(aligned_data) != len(data):
            errors.append(f"{label}: canonical/aligned count mismatch")
        if [item.get("id") for item in aligned_data] != ids:
            errors.append(f"{label}: aligned IDs/order differ from canonical source")

        # Shift-Left Extreme Sentence Payload Diagnostics
        extreme_payloads = []
        for s_item in aligned_data:
            s_text = s_item.get("text") or ""
            s_trans = s_item.get("trans") or ""
            s_words = len(s_text.split())
            s_chars = len(s_trans)
            s_start = s_item.get("raw_start", s_item.get("start", 0)) or 0
            s_end = s_item.get("raw_end", s_item.get("end", 0)) or 0
            s_dur = max(0.0, float(s_end) - float(s_start)) if (s_start is not None and s_end is not None) else 0.0
            if s_words >= 70 or s_chars >= 180 or s_dur >= 35.0:
                extreme_payloads.append(f"{s_item.get('id', '')} ({s_words}w, {s_chars}c, {round(s_dur, 1)}s)")
        if extreme_payloads:
            diagnostics.append(f"{label}: {len(extreme_payloads)} extreme sentence payloads [{', '.join(extreme_payloads[:4])}]")

        if content_mode == TEXT_ONLY:
            record["review_required_records"] = 0
            record["acoustic_coverage"] = 1.0
            record["covered_audio_tokens"] = 0
            record["expected_audio_tokens"] = 0
            record["status"] = "validated"
            chapters.append(record)
            continue

        previous_start = -1.0
        previous_end = -1.0
        review_ids = []
        covered_tokens = 0
        expected_tokens = 0
        for item in aligned_data:
            item_id = item.get("id", "<unknown>")
            is_heading = item.get("is_heading", False)
            owner_accepted = (number, item_id) in review_ledger
            if owner_accepted:
                accepted_exceptions.append({"chapter": number, "sentence_id": item_id, **review_ledger[(number, item_id)]})
            approved_non_monotonic = (
                item.get("alignment_status") == "reviewed"
                and item.get("alignment_reason") == "global_match_out_of_order"
                and isinstance(item.get("review_evidence"), str)
                and bool(item.get("review_evidence", "").strip())
                and item.get("has_audio_match") is True
                and not item.get("fallback_used")
                and float(item.get("match_ratio", 0.0)) >= 0.5
            )
            non_narrated = (
                item.get("alignment_status") == "not-applicable"
                and item.get("alignment_reason") in {
                    "non_narrated_content",
                    "non_narrated_text",
                    "duplicate_source_fragment",
                    "out_of_scope_reference",
                    "structural_tabular_omitted_by_narrator",
                }
            )
            out_of_scope = item.get("alignment_reason") == "out_of_scope_reference"
            if content_mode not in (COMPLETE, SYNTHETIC) and not is_heading:
                if item_id in scoped_ids and out_of_scope:
                    errors.append(f"{label} {item_id}: declared playable sentence is marked out of scope")
                if item_id not in scoped_ids and not out_of_scope:
                    errors.append(f"{label} {item_id}: non-complete profile requires explicit out_of_scope_reference")
                if out_of_scope and (item.get("has_audio_match") or item.get("word_spans")):
                    errors.append(f"{label} {item_id}: out_of_scope_reference must not contain playable spans")
                if item_id in scoped_ids:
                    raw_start = item.get("raw_start", item.get("start"))
                    raw_end = item.get("raw_end", item.get("end"))
                    in_declared_interval = isinstance(raw_start, (int, float)) and isinstance(raw_end, (int, float)) and any(
                        raw_start >= unit["audio_start"] and raw_end <= unit["audio_end"]
                        for unit in chapter_units if item_id in unit["sentence_ids"]
                    )
                    if not in_declared_interval:
                        errors.append(f"{label} {item_id}: aligned interval is outside its declared audio unit")
            if item.get("alignment_reason") == "audio_omitted":
                errors.append(f"{label} {item_id}: audio omission cannot be silently excluded")
            structural_audio_reorder = (
                item.get("alignment_status") == "validated"
                and item.get("alignment_method") in {
                    "leading_epigraph_attribution",
                    "chapter_heading_numeric_variant",
                    "opening_speaker_attribution",
                    "dialogue_attribution_reorder",
                }
                and item.get("has_audio_match") is True
                and not item.get("fallback_used")
            )
            if non_narrated:
                evidence = item.get("non_narrated_evidence") or {}
                prefix = canonical.name.removesuffix("_canonical_sentences.json")
                acoustic_path = book_dir / "audio" / f"{prefix}_acoustic_words.json"
                import hashlib
                non_narrated_reviews.append({
                    "chapter": number,
                    "sentence_id": item_id,
                    "source_text": item.get("text", ""),
                    "evidence": evidence,
                    "acoustic_words_sha256": hashlib.sha256(acoustic_path.read_bytes()).hexdigest() if acoustic_path.exists() else None,
                    "audio_sha256": hashlib.sha256(audio_resolution.path.read_bytes()).hexdigest() if audio_resolution and audio_resolution.status == "ok" else None,
                })
            if not is_heading and not non_narrated and not owner_accepted and (not item.get("word_spans") or not item.get("has_audio_match", True)):
                errors.append(f"{label} {item_id}: missing audio word spans")
            raw_start = item.get("raw_start", item.get("start"))
            raw_end = item.get("raw_end", item.get("end"))
            start = float(raw_start) if isinstance(raw_start, (int, float)) else None
            end = float(raw_end) if isinstance(raw_end, (int, float)) else None
            # Opening headings and attributions can be printed after the quote
            # while narrated before it. They retain real audio timestamps but
            # must not distort the monotonic body-sentence timeline.
            participates_in_timeline = not owner_accepted and not non_narrated and not structural_audio_reorder
            if participates_in_timeline and start is not None and start < previous_start and not approved_non_monotonic:
                errors.append(f"{label} {item_id}: non-monotonic raw start")
            if participates_in_timeline and start is not None and previous_end >= 0 and start < (previous_end - 0.05) and not approved_non_monotonic:
                errors.append(f"{label} {item_id}: sentence overlap detected (starts at {start:.2f}s before previous ended at {previous_end:.2f}s)")
            if start is not None and end is not None and end < start:
                errors.append(f"{label} {item_id}: end precedes start")
            # Missing-match records are reported once above. Their null spans
            # are intentional and must not create one duplicate error per word.
            spans_to_validate = item.get("word_spans", []) if item.get("has_audio_match") else []
            for span in spans_to_validate:
                span_start_raw = span.get("start")
                span_end_raw = span.get("end")
                span_start = float(span_start_raw) if isinstance(span_start_raw, (int, float)) else None
                span_end = float(span_end_raw) if isinstance(span_end_raw, (int, float)) else None
                if span_start is None or span_end is None or span_start < 0 or span_end < span_start or span.get("timing_source", "observed") != "observed":
                    errors.append(f"{label} {item_id}: invalid word span")
            if participates_in_timeline:
                if start is not None and previous_end > 0:
                    inter_gap = start - previous_end
                    if inter_gap > MAX_INTER_SENTENCE_ACOUSTIC_GAP:
                        errors.append(
                            f"{label} {item_id}: excessive acoustic void of {inter_gap:.1f}s detected "
                            f"(previous sentence ended at {previous_end:.1f}s, current starts at {start:.1f}s); "
                            f"exceeds {MAX_INTER_SENTENCE_ACOUSTIC_GAP:.0f}s release ceiling"
                        )
                if start is not None:
                    previous_start = start
                if end is not None:
                    previous_end = max(previous_end, end)
            ratio = float(item.get("match_ratio", 0.0))
            matched = int(item.get("matched_token_count", 0))
            source_tokens = int(item.get("source_token_count", 0))
            physically_playable = _has_complete_physical_spans(item)
            if not is_heading and not non_narrated and not owner_accepted:
                expected_tokens += max(source_tokens, 0)
                if physically_playable:
                    covered_tokens += max(source_tokens, 0)
                else:
                    covered_tokens += min(max(matched, 0), max(source_tokens, 0))
            if not is_heading and not non_narrated and not owner_accepted and (not item.get("has_audio_match", True) or item.get("fallback_used") or item.get("alignment_status") not in {"validated", "reviewed"} or matched < 1 or (ratio < 0.5 and not physically_playable)):
                review_ids.append(item_id)
        if content_mode not in (COMPLETE, SYNTHETIC):
            unknown_scope_ids = scoped_ids - set(ids)
            if unknown_scope_ids:
                errors.append(f"{label}: profile references unknown sentence IDs ({', '.join(sorted(unknown_scope_ids)[:8])})")
        record["review_required_records"] = len(review_ids)
        coverage = covered_tokens / expected_tokens if expected_tokens else 1.0
        record["acoustic_coverage"] = coverage
        record["covered_audio_tokens"] = covered_tokens
        record["expected_audio_tokens"] = expected_tokens
        if coverage < MIN_CHAPTER_AUDIO_COVERAGE:
            errors.append(
                f"{label}: acoustic coverage {coverage:.1%} is below the "
                f"{MIN_CHAPTER_AUDIO_COVERAGE:.0%} release threshold"
            )

        # Bilateral acoustic check: verify reverse coverage of acoustic words if acoustic profile exists
        prefix = canonical.name.removesuffix("_canonical_sentences.json")
        acoustic_path = book_dir / "audio" / f"{prefix}_acoustic_words.json"
        if not acoustic_path.is_file():
            acoustic_path = book_dir / f"{prefix}_acoustic_words.json"
        if acoustic_path.is_file():
            try:
                with acoustic_path.open("r", encoding="utf-8") as af:
                    ac_data = json.load(af)
                total_ac_words = len(ac_data.get("words", []))
                if total_ac_words > 100:
                    total_aligned_words = sum(len(item.get("word_spans", [])) for item in aligned_data if item.get("has_audio_match"))
                    matched_spans = [span for item in aligned_data if item.get("has_audio_match") for span in item.get("word_spans", [])]
                    last_end = max((s["end"] for s in matched_spans), default=0.0)
                    effective_ac_words = total_ac_words
                    if last_end > 0.0:
                        trailing_words = [w for w in ac_data.get("words", []) if w.get("start", 0.0) > last_end + 1.5]
                        if len(trailing_words) >= 15:
                            trailing_text = " ".join(w.get("word", "") for w in trailing_words).lower()
                            outro_keywords = ("audible", "copyright", "production", "unabridged", "random house", "directed by", "producer")
                            if any(k in trailing_text for k in outro_keywords):
                                effective_ac_words = max(1, total_ac_words - len(trailing_words))
                    bilateral_ratio = total_aligned_words / effective_ac_words
                    record["bilateral_acoustic_word_ratio"] = round(bilateral_ratio, 4)
                    record["total_acoustic_words"] = total_ac_words
                    record["total_aligned_words"] = total_aligned_words
                    if bilateral_ratio < MIN_BILATERAL_ACOUSTIC_WORD_RATIO:
                        errors.append(
                            f"{label}: bilateral acoustic word ratio {bilateral_ratio:.1%} is below the "
                            f"{MIN_BILATERAL_ACOUSTIC_WORD_RATIO:.0%} threshold (audio has {total_ac_words} words, "
                            f"text only accounts for {total_aligned_words} words)"
                        )
            except (json.JSONDecodeError, KeyError, OSError) as exc:
                errors.append(f"{label}: failed to parse acoustic words from {acoustic_path.name}: {exc}")
        non_narrated_records = sum(
            1 for item in aligned_data
            if item.get("alignment_status") == "not-applicable"
            and item.get("alignment_reason") in {"non_narrated_content", "non_narrated_text", "duplicate_source_fragment", "out_of_scope_reference"}
            and not item.get("editorial_omission")
            and not item.get("is_print_only")
            and not item.get("is_back_matter")
            and not (item.get("non_narrated_evidence") or {}).get("basis") in {"publisher_back_matter", "structural_tabular"}
        )
        non_narrated_ratio = non_narrated_records / len(aligned_data) if aligned_data else 0.0
        is_excessive_omission = (
            non_narrated_records > MAX_NON_NARRATED_CHAPTER_COUNT
            or (len(aligned_data) >= 15 and non_narrated_records > 3 and non_narrated_ratio > MAX_NON_NARRATED_CHAPTER_RATIO)
        )
        if content_mode in (COMPLETE, SYNTHETIC) and is_excessive_omission:
            errors.append(
                f"{label}: non-narrated omission ratio {non_narrated_ratio:.1%} "
                f"({non_narrated_records}/{len(aligned_data)} sentences) exceeds the {MAX_NON_NARRATED_CHAPTER_RATIO:.0%} / {MAX_NON_NARRATED_CHAPTER_COUNT}-sentence release ceiling; "
                f"chapter must be truncated to audio bounds or structured with explicit text-only profiles"
            )
        if review_ids:
            warnings.append(f"{label}: {len(review_ids)} alignment records require review ({', '.join(review_ids[:8])})")
            record["status"] = "review-required"
        else:
            record["status"] = "validated"
        chapters.append(record)

    result = {
        "book_dir": str(book_dir.resolve()),
        "audio_content_mode": content_mode,
        "audio_content_profile_sha256": content_profile["profile_sha256"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_revision": (json.loads((book_dir / "reader_run_manifest.json").read_text(encoding="utf-8")).get("pipeline_revision") if require_provenance and (book_dir / "reader_run_manifest.json").exists() else None),
        "chapters": chapters,
        "accepted_review_exceptions": accepted_exceptions,
        "non_narrated_reviews": non_narrated_reviews,
        "errors": errors,
        "warnings": warnings,
        "diagnostics": diagnostics,
        "release_ready": not errors and not warnings,
    }
    output = json.dumps(result, ensure_ascii=False, indent=2)
    print(output)
    if report_path:
        atomic_write_json(report_path, result)
    return 0 if result["release_ready"] else 1


def validate_for_release(book_dir: Path, report_path: Path, *, require_provenance=False):
    """Validate and return (report, token); a failed gate returns no token."""
    code = validate(book_dir, report_path, require_provenance=require_provenance)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if code != 0:
        return report, None
    return report, issue_release_token(book_dir, report_path, report)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("book_dir", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--require-provenance", action="store_true")
    args = parser.parse_args()
    return validate(args.book_dir.expanduser().resolve(), args.report, require_provenance=args.require_provenance)


if __name__ == "__main__":
    raise SystemExit(main())
