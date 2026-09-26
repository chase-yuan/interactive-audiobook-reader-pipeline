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
from content_profile import COMPLETE, TEXT_ONLY, load_content_profile

MULTI_BOUNDARY = re.compile(r"(?:[.!?][\"'”’)]*|\*)\s+[A-Z]")
ABBREVIATION_BEFORE_CAPITAL = re.compile(
    r"(?:Mrs|Mr|Ms|Dr|Prof|Sr|Jr|Rev|Hon|Gen|Col|Maj|Capt|Lt|Sgt|Cpl|Pvt|Gov|Sen|Rep|Pres|Sec|Amb|Insp|Det|St|Mt|Ft|Mme|Mlle|Esq|Ph\.D|M\.D|B\.A|M\.A|U\.S|U\.K|U\.S\.A|e\.g|i\.e|vs|etc|al|fig|pp|vol|no|Jan|Feb|Mar|Apr|Aug|Sept|Oct|Nov|Dec|\b[A-Z])$"
)
INTENTIONAL_INTERJECTION = re.compile(
    r"(?:^|[.!?]\s+)[\"“‘']?(?:(?:oh|hell)\s+)?no$",
    re.IGNORECASE,
)
MIN_CHAPTER_AUDIO_COVERAGE = 0.95
MAX_NON_NARRATED_CHAPTER_RATIO = 0.10
MAX_NON_NARRATED_CHAPTER_COUNT = 15


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


def validate(book_dir: Path, report_path=None, *, require_provenance=False):
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
        record = {"chapter": number, "canonical_records": len(data), "suspicious_records": len(suspicious)}

        analysis = book_dir / canonical.name.replace("_canonical_sentences.json", "_full_analysis.json")
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
        if number is not None and content_mode not in (COMPLETE, TEXT_ONLY) and not chapter_units:
            errors.append(f"{label}: non-complete profile has no declared audio units")
        if number is not None and content_mode == COMPLETE:
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

        if content_mode == TEXT_ONLY:
            record["review_required_records"] = 0
            record["acoustic_coverage"] = 1.0
            record["covered_audio_tokens"] = 0
            record["expected_audio_tokens"] = 0
            record["status"] = "validated"
            chapters.append(record)
            continue

        previous_start = -1.0
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
            non_narrated = item.get("alignment_status") == "not-applicable" and item.get("alignment_reason") in {"non_narrated_content", "non_narrated_text", "duplicate_source_fragment", "out_of_scope_reference"}
            out_of_scope = item.get("alignment_reason") == "out_of_scope_reference"
            if content_mode != COMPLETE and not is_heading:
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
                if start is not None:
                    previous_start = start
            ratio = float(item.get("match_ratio", 0.0))
            matched = int(item.get("matched_token_count", 0))
            source_tokens = int(item.get("source_token_count", 0))
            if not is_heading and not non_narrated and not owner_accepted:
                expected_tokens += max(source_tokens, 0)
                covered_tokens += min(max(matched, 0), max(source_tokens, 0))
            physically_playable = _has_complete_physical_spans(item)
            if not is_heading and not non_narrated and not owner_accepted and (not item.get("has_audio_match", True) or item.get("fallback_used") or item.get("alignment_status") not in {"validated", "reviewed"} or matched < 1 or (ratio < 0.5 and not physically_playable)):
                review_ids.append(item_id)
        if content_mode != COMPLETE:
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
        non_narrated_records = sum(
            1 for item in aligned_data
            if item.get("alignment_status") == "not-applicable"
            and item.get("alignment_reason") in {"non_narrated_content", "non_narrated_text", "duplicate_source_fragment", "out_of_scope_reference"}
        )
        non_narrated_ratio = non_narrated_records / len(aligned_data) if aligned_data else 0.0
        is_excessive_omission = (
            non_narrated_records > MAX_NON_NARRATED_CHAPTER_COUNT
            or (len(aligned_data) >= 15 and non_narrated_records > 3 and non_narrated_ratio > MAX_NON_NARRATED_CHAPTER_RATIO)
        )
        if content_mode == COMPLETE and is_excessive_omission:
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
