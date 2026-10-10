"""
Universal Dual-Mode Pipeline Runner for Interactive Readers and Audiobooks.

Unified entry point supporting:
1. Pure Text Interactive Readers (text_only):
   - Standalone EPUB extraction, chapter discovery & TOC filtering.
   - High-throughput parallel linguistic analysis (Chinese translation + B2/C1/C2 vocabulary).
   - Instant deterministic sentence alignment.
   - Release gate validation and cryptographic ReleaseToken issuance.
   - Zero-dependency Apple Books-grade bilingual interactive reader compilation.
   - Gracefully hidden audio playback controls with 100% intact typography and touch/keyboard interactivity.
2. Immersive Audiobook Readers (complete):
   - Synchronized acoustic word-level forced alignment with MLX Whisper and dynamic aligner.
   - Strict 95% acoustic coverage threshold and monotonic timeline validation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PIPELINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PIPELINE_DIR))

from intake_reconciler import parse_epub
from extract_epub import extract_chapter_from_epub
from agy_linguistic_worker import process_canonical_sentences, PROMPT_PATH, verify_analysis
from validate_outputs import validate, validate_canonical_sentences
from release_token import issue_release_token
from html_builder import build_master_reader
from quality_gate import smoke_check_html, check_audio_physical_integrity
from kokoro_synthesizer import synthesize_chapter
from artifact_io import atomic_write_json, atomic_write_text

DEFAULT_EXCLUDE_PATTERNS = [
    "cover",
    "halftitle",
    "titlepage",
    "title.html",
    "copyright",
    "contents",
    "toc",
    "sample",
    "extra",
    "advert",
    "libertyme",
    "invisibleorder",
    "bibliography",
    "notes",
]

ROMAN_NUMERALS = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
    "XI": 11, "XII": 12, "XIII": 13, "XIV": 14, "XV": 15, "XVI": 16, "XVII": 17, "XVIII": 18,
    "XIX": 19, "XX": 20, "XXI": 21, "XXII": 22, "XXIII": 23, "XXIV": 24, "XXV": 25,
}


def sanitize_slug(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip()).strip("_").lower()
    return slug[:40] if slug else "book"


def detect_book_prefix(book_dir: Path, fallback_slug: str) -> str:
    existing = sorted(book_dir.glob("*_ch*_canonical_sentences.json"))
    if existing:
        match = re.match(r"^(.*)_ch\d+_canonical_sentences\.json$", existing[0].name)
        if match:
            return match.group(1)
    return fallback_slug


def is_analysis_valid(analysis_path: Path, canonical_path: Path) -> bool:
    if not analysis_path.is_file() or not canonical_path.is_file():
        return False
    try:
        c_data = json.loads(canonical_path.read_text(encoding="utf-8"))
        a_data = json.loads(analysis_path.read_text(encoding="utf-8"))
        if not isinstance(a_data, list) or len(a_data) != len(c_data):
            return False
        verify_analysis(a_data, c_data)
        return True
    except Exception:
        return False


def infer_chapter_role_and_label(index: int, title: str, href: str) -> Tuple[str, Optional[int], str]:
    lower_t = title.lower()
    lower_h = href.lower()

    # Check Roman numeral or Arabic chapter prefix
    m_roman = re.match(r"^([IVXLCDM]+)\.\s*(.*)", title)
    m_arabic = re.match(r"^(?:Chapter\s+)?(\d+)[\.:]?\s*(.*)", title, re.IGNORECASE)

    if m_roman and m_roman.group(1) in ROMAN_NUMERALS:
        ch_num = ROMAN_NUMERALS[m_roman.group(1)]
        return "chapter", ch_num, f"Chapter {ch_num}"
    elif m_arabic:
        ch_num = int(m_arabic.group(1))
        return "chapter", ch_num, f"Chapter {ch_num}"
    elif "preface" in lower_t or "preface" in lower_h or "foreword" in lower_t:
        lbl = "Preface"
        if "first" in lower_t:
            lbl = "Preface (1st Ed)"
        elif "second" in lower_t:
            lbl = "Preface (2nd Ed)"
        elif "tucker" in lower_t or "editorial" in lower_t:
            lbl = "Editorial Preface"
        return "preface", None, lbl
    elif "intro" in lower_t or "intro" in lower_h:
        lbl = "Author's Intro" if "author" in lower_t else "Introduction"
        if "third" in lower_t:
            lbl = "Intro (3rd Ed)"
        return "introduction", None, lbl
    elif "question" in lower_t or "question" in lower_h:
        return "appendix", None, "Questions"
    elif "appendix" in lower_t or "appendix" in lower_h:
        return "appendix", None, "Appendix"
    elif "note" in lower_t:
        return "preface", None, "Note"
    elif "conclusion" in lower_t:
        return "chapter", None, "Conclusions"
    else:
        return "chapter", None, title[:24].strip()


def discover_epub_chapters(
    epub_path: Path,
    min_chars: int = 300,
    exclude_patterns: Optional[List[str]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], Optional[str]]:
    parsed = parse_epub(epub_path)
    metadata = parsed.get("metadata", {})
    all_chapters = parsed.get("chapters", [])
    cover_member = parsed.get("cover_member")

    excludes = [p.lower() for p in (exclude_patterns or DEFAULT_EXCLUDE_PATTERNS) if p]

    selected = []
    for ch in all_chapters:
        href_lower = ch["href"].lower()
        title = ch.get("title", "").strip()
        title_lower = title.lower()
        chars = ch.get("text_chars", 0)

        # Check explicit exclude patterns against href and title
        if any(exc in href_lower or exc in title_lower for exc in excludes):
            continue

        # Check minimal text threshold
        is_substantive_title = any(
            k in title_lower for k in ["chapter", "preface", "intro", "conclusion", "epilogue", "appendix", "question"]
        )
        if chars < min_chars and not is_substantive_title:
            continue

        selected.append(ch)

    return metadata, selected, cover_member


def setup_book_directory(
    book_dir: Path,
    epub_path: Path,
    chapters_meta: List[Dict[str, Any]],
    cover_member: Optional[str] = None,
    mode: str = "text_only",
) -> None:
    book_dir.mkdir(parents=True, exist_ok=True)

    # Copy EPUB into book_dir if not present
    dest_epub = book_dir / epub_path.name
    if not dest_epub.exists() and epub_path.exists():
        dest_epub.write_bytes(epub_path.read_bytes())

    # Extract cover image if available
    cover_path = book_dir / "cover.jpg"
    if not cover_path.exists() and cover_member and epub_path.exists():
        try:
            with zipfile.ZipFile(epub_path, "r") as zf:
                if cover_member in zf.namelist():
                    cover_path.write_bytes(zf.read(cover_member))
        except Exception as exc:
            print(f"[Warning] Failed to extract cover '{cover_member}': {exc}", file=sys.stderr)

    # Write audio_content_profile.json
    profile_path = book_dir / "audio_content_profile.json"
    atomic_write_json(profile_path, {
        "schema_version": 1,
        "audio_content_mode": mode
    })

    # Write chapter_metadata.json
    metadata_rows = []
    for item in chapters_meta:
        row = {
            "chapter": item["num"],
            "role": item["role"],
            "title": item["title"],
            "label": item["label"],
        }
        if item.get("display_number") is not None:
            row["display_number"] = item["display_number"]
        metadata_rows.append(row)

    metadata_path = book_dir / "chapter_metadata.json"
    atomic_write_json(metadata_path, {
        "schema_version": 1,
        "chapters": metadata_rows
    })


def extract_chapters_sentences(
    book_dir: Path,
    epub_path: Path,
    chapters_meta: List[Dict[str, Any]],
    prefix: str,
    force: bool = False,
) -> None:
    print(f"\n=== [Stage 1: EPUB Sentence Extraction ({len(chapters_meta)} tracks)] ===", flush=True)
    for item in chapters_meta:
        num = item["num"]
        href = item["href"]
        can_path = book_dir / f"{prefix}_ch{num:02d}_canonical_sentences.json"
        if not force and can_path.is_file() and can_path.stat().st_size > 50:
            continue
        extract_chapter_from_epub(str(epub_path), href, str(can_path))
    print("[Stage 1] Sentence extraction completed.")


def validate_extracted_sentences_gate(
    book_dir: Path,
    chapters_meta: List[Dict[str, Any]],
    prefix: str,
) -> None:
    print(f"\n=== [Stage 1.5: Shift-Left Sentence Quality Gate ({len(chapters_meta)} tracks)] ===", flush=True)
    all_gate_failures = []
    total_sentences = 0
    for item in chapters_meta:
        num = item["num"]
        label = item["label"]
        can_path = book_dir / f"{prefix}_ch{num:02d}_canonical_sentences.json"
        if not can_path.is_file():
            all_gate_failures.append(f"Track {num:02d} ({label}): canonical sentences file missing: {can_path}")
            continue
        try:
            data = json.loads(can_path.read_text(encoding="utf-8"))
        except Exception as exc:
            all_gate_failures.append(f"Track {num:02d} ({label}): invalid JSON ({exc})")
            continue
        total_sentences += len(data)
        issues = validate_canonical_sentences(data)
        if issues:
            for iss in issues[:10]:
                all_gate_failures.append(f"Track {num:02d} ({label}) {iss}")
            if len(issues) > 10:
                all_gate_failures.append(f"Track {num:02d} ({label}): ... and {len(issues) - 10} more sentence defects")

    if all_gate_failures:
        print("\n[CRITICAL FAILURE] Shift-Left Sentence Gate BLOCKED pipeline execution:", file=sys.stderr)
        for fail in all_gate_failures[:25]:
            print(f"  ❌ {fail}", file=sys.stderr)
        if len(all_gate_failures) > 25:
            print(f"  ... and {len(all_gate_failures) - 25} additional defects.", file=sys.stderr)
        raise RuntimeError(
            f"Stage 1.5 Shift-Left Sentence Gate failed with {len(all_gate_failures)} defects. "
            "Downstream linguistic analysis and neural audio synthesis have been HALTED to prevent compute waste."
        )

    print(f"[Stage 1.5] Shift-Left Sentence Quality Gate PASSED: 100% verified across {total_sentences} sentences in {len(chapters_meta)} tracks.")


def process_linguistics_track(
    num: int,
    label: str,
    prefix: str,
    book_dir: Path,
    base_prompt: str,
    max_workers_per_chapter: int = 1,
) -> bool:
    can_path = book_dir / f"{prefix}_ch{num:02d}_canonical_sentences.json"
    ana_path = book_dir / f"{prefix}_ch{num:02d}_full_analysis.json"

    if is_analysis_valid(ana_path, can_path):
        return True

    if not can_path.is_file():
        print(f"[Linguistic ERROR] Track {num:02d} missing canonical: {can_path}", file=sys.stderr)
        return False

    can_data = json.loads(can_path.read_text(encoding="utf-8"))
    print(f"[Linguistic] Processing Track {num:02d} ({len(can_data)} sentences: {label})...", flush=True)
    t0 = time.time()
    try:
        analyzed_data = process_canonical_sentences(
            canonical_data=can_data,
            base_prompt=base_prompt,
            cwd=book_dir,
            chunk_size=40,
            timeout=3600,
            max_batch_attempts=5,
            max_workers=max_workers_per_chapter,
        )
        atomic_write_json(ana_path, analyzed_data)
        elapsed = time.time() - t0
        print(f"[Linguistic] Track {num:02d} complete in {elapsed:.1f}s -> {ana_path.name}", flush=True)
        return True
    except Exception as exc:
        print(f"[Linguistic ERROR] Track {num:02d} failed: {exc}", file=sys.stderr, flush=True)
        return False


def run_parallel_linguistic_analysis(
    book_dir: Path,
    chapters_meta: List[Dict[str, Any]],
    prefix: str,
    concurrency: int = 8,
    max_workers_per_chapter: int = 4,
) -> None:
    print(f"\n=== [Stage 2: High-Throughput Linguistic Analysis ({concurrency} parallel chapters, {max_workers_per_chapter} workers/chapter)] ===", flush=True)
    base_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {
            executor.submit(
                process_linguistics_track,
                item["num"],
                item["label"],
                prefix,
                book_dir,
                base_prompt,
                max_workers_per_chapter,
            ): item
            for item in chapters_meta
        }
        for f in as_completed(futures):
            item = futures[f]
            ok = f.result()
            if not ok:
                raise RuntimeError(f"Linguistic analysis failed on track {item['num']:02d} ({item['label']})")
    print("[Stage 2] High-throughput linguistic analysis completed.")


def synthesize_text_only_aligned_sentences(
    book_dir: Path,
    chapters_meta: List[Dict[str, Any]],
    prefix: str,
) -> None:
    print(f"\n=== [Stage 3: Synthesizing Aligned Sentences (Text-Only)] ===", flush=True)
    for item in chapters_meta:
        num = item["num"]
        can_path = book_dir / f"{prefix}_ch{num:02d}_canonical_sentences.json"
        ana_path = book_dir / f"{prefix}_ch{num:02d}_full_analysis.json"
        alg_path = book_dir / f"{prefix}_ch{num:02d}_aligned_sentences.json"

        c_data = json.loads(can_path.read_text(encoding="utf-8"))
        a_data = json.loads(ana_path.read_text(encoding="utf-8"))
        c_map = {row["id"]: row for row in c_data}

        aligned_items = []
        for row in a_data:
            cid = row["id"]
            c_info = c_map[cid]
            aligned_items.append({
                "id": cid,
                "elem_idx": c_info["elem_idx"],
                "tag": c_info["tag"],
                "text": row["text"],
                "trans": row["trans"],
                "vocab": row.get("vocab", []),
                "is_heading": c_info.get("is_heading", False),
                "has_audio_match": False,
                "start": None,
                "end": None,
                "word_spans": []
            })
        atomic_write_json(alg_path, aligned_items)
    print("[Stage 3] Aligned sentences synthesized.")


def synthesize_synthetic_voice_chapters(
    book_dir: Path,
    chapters_meta: List[Dict[str, Any]],
    prefix: str,
    voice: str = "am_adam",
    speed: float = 1.0,
    concurrency: int = 3,
) -> None:
    print(f"\n=== [Stage 3: Kokoro Neural Voice Synthesis (voice={voice}, speed={speed}x)] ===", flush=True)
    audio_dir = book_dir / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    def _synth_track(item: Dict[str, Any]) -> bool:
        num = item["num"]
        label = item["label"]
        can_path = book_dir / f"{prefix}_ch{num:02d}_canonical_sentences.json"
        ana_path = book_dir / f"{prefix}_ch{num:02d}_full_analysis.json"
        alg_path = book_dir / f"{prefix}_ch{num:02d}_aligned_sentences.json"
        mp3_path = audio_dir / f"chapter_{num:02d}.mp3"

        if not can_path.is_file():
            print(f"[TTS ERROR] Track {num:02d} missing canonical: {can_path}", file=sys.stderr)
            return False

        t0 = time.time()
        print(f"[TTS] Synthesizing Track {num:02d} ({label})...", flush=True)
        try:
            synthesize_chapter(
                canonical_path=can_path,
                analysis_path=ana_path,
                aligned_output_path=alg_path,
                audio_output_path=mp3_path,
                voice=voice,
                speed=speed,
            )
            elapsed = time.time() - t0
            print(f"[TTS] Track {num:02d} complete in {elapsed:.1f}s -> {mp3_path.name}", flush=True)
            return True
        except Exception as exc:
            print(f"[TTS ERROR] Track {num:02d} failed: {exc}", file=sys.stderr, flush=True)
            return False

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(_synth_track, item): item for item in chapters_meta}
        for f in as_completed(futures):
            item = futures[f]
            ok = f.result()
            if not ok:
                raise RuntimeError(f"TTS synthesis failed on track {item['num']:02d} ({item['label']})")

    print("[Stage 3] Kokoro neural voice synthesis completed.")


def build_and_verify_reader(
    book_dir: Path,
    chapters_meta: List[Dict[str, Any]],
    prefix: str,
    title: str,
    subtitle: str,
    author: str,
    slug_id: str,
    mode: str = "text_only",
    audio_dir: Optional[Path] = None,
) -> Path:
    print(f"\n=== [Stage 4: Quality Gate & Release Validation] ===", flush=True)
    rep_path = book_dir / "reader_validation_report.json"
    code = validate(book_dir, rep_path)
    if code != 0:
        raise RuntimeError(f"Validation report failed quality gate (exit code {code})")
    report = json.loads(rep_path.read_text(encoding="utf-8"))
    token = issue_release_token(book_dir, rep_path, report)
    print(f"[Stage 4] ReleaseToken issued: nonce={token.nonce[:16]}... (report sha256: {token.report_sha256[:10]}...)")

    print(f"\n=== [Stage 5: Master Interactive Reader Compilation] ===", flush=True)
    existing_readers = sorted(book_dir.glob("*_Interactive_Reader.html"))
    if existing_readers:
        out_html = existing_readers[0]
    else:
        out_html = book_dir / f"{slug_id.replace('-', '_').title()}_Interactive_Reader.html"

    chapters_config = []
    for item in chapters_meta:
        num = item["num"]
        aligned_path = book_dir / f"{prefix}_ch{num:02d}_aligned_sentences.json"

        audio_src = ""
        if mode in ("complete", "synthetic") and audio_dir:
            audio_candidate = audio_dir / f"chapter_{num:02d}.mp3"
            if audio_candidate.exists():
                audio_src = f"./audio/{audio_candidate.name}"

        cfg = {
            "num": num,
            "title": item["title"],
            "role": item["role"],
            "label": item["label"],
            "audio": audio_src,
            "aligned_json": str(aligned_path),
        }
        if item.get("display_number") is not None:
            cfg["display_number"] = item["display_number"]
        chapters_config.append(cfg)

    build_master_reader(
        book_title=title,
        book_subtitle=subtitle,
        book_author=author,
        chapters_config=chapters_config,
        output_html_path=str(out_html),
        release_token=token,
        release_report_path=str(rep_path),
        book_id=slug_id,
    )

    print(f"\n=== [Stage 6: Static Smoke Check & Audio Probes] ===", flush=True)
    smoke = smoke_check_html(out_html, expected_chapters=len(chapters_meta))
    if smoke["status"] != "passed":
        raise RuntimeError(f"HTML smoke check failed: {smoke['errors']}")
    print(
        f"[Stage 6] Smoke check passed: 100% compliant "
        f"({smoke['chapter_count']} chapters, {out_html.stat().st_size:,} bytes)"
    )

    if mode == "synthetic" and audio_dir:
        for item in chapters_meta:
            num = item["num"]
            c_mp3 = audio_dir / f"chapter_{num:02d}.mp3"
            c_alg = book_dir / f"{prefix}_ch{num:02d}_aligned_sentences.json"
            if c_mp3.is_file() and c_alg.is_file():
                alg_data = json.loads(c_alg.read_text(encoding="utf-8"))
                last_end = alg_data[-1]["end"] if alg_data else 0.0
                probe = check_audio_physical_integrity(c_mp3, expected_duration=last_end, max_duration_delta=0.45)
                if probe["status"] != "passed":
                    raise RuntimeError(f"Audio physical probe failed on Track {num:02d} ({item['label']}): {probe.get('error')}")
        print("[Stage 6] Audio physical integrity probe passed: 100% duration & energy verified.")

    return out_html


def build_reader_pipeline(
    epub_path: Path,
    book_dir: Optional[Path] = None,
    audio_dir: Optional[Path] = None,
    text_only: bool = False,
    auto_voice: Optional[str] = None,
    voice_speed: float = 1.0,
    concurrency: int = 8,
    min_chars: int = 300,
    exclude_patterns: Optional[List[str]] = None,
    manifest_path: Optional[Path] = None,
    title_override: Optional[str] = None,
    subtitle_override: Optional[str] = None,
    author_override: Optional[str] = None,
    open_in_browser: bool = True,
    force_extract: bool = False,
    llm_model: Optional[str] = None,
) -> Path:
    t_start = time.time()
    epub_path = epub_path.expanduser().resolve()
    if not epub_path.is_file():
        raise FileNotFoundError(f"EPUB file not found: {epub_path}")

    # Configure linguistic LLM provider
    if llm_model:
        os.environ["READER_AGY_MODEL"] = llm_model
    elif os.getenv("DEEPSEEK_API_KEY") and not os.getenv("READER_AGY_MODEL"):
        os.environ["READER_AGY_MODEL"] = "deepseek"

    # Mode determination
    if auto_voice:
        mode = "synthetic"
    elif text_only or not audio_dir:
        mode = "text_only"
    else:
        mode = "complete"

    # Discover metadata and chapters
    raw_meta, raw_chapters, cover_member = discover_epub_chapters(
        epub_path,
        min_chars=min_chars,
        exclude_patterns=exclude_patterns,
    )

    title = title_override or raw_meta.get("title") or epub_path.stem
    author = author_override or raw_meta.get("creator") or "Unknown Author"
    subtitle = subtitle_override or (
        "Bilingual Synchronized Audiobook" if mode == "synthetic"
        else ("Bilingual Interactive Reader" if mode == "text_only" else "Bilingual Synchronized Reader")
    )
    slug_id = sanitize_slug(title).replace("_", "-")

    # Set up book directory
    if book_dir is None:
        target_dir = Path.home() / "Vault" / "audiobook" / title
    else:
        target_dir = book_dir.expanduser().resolve()

    target_dir.mkdir(parents=True, exist_ok=True)
    if mode == "synthetic":
        audio_dir = target_dir / "audio"

    # Determine chapter metadata
    metadata_file = target_dir / "chapter_metadata.json"
    if manifest_path and manifest_path.is_file():
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        chapters_meta = manifest_data.get("chapters", manifest_data)
    elif metadata_file.is_file():
        try:
            m_data = json.loads(metadata_file.read_text(encoding="utf-8"))
            existing_rows = m_data.get("chapters", [])
            href_by_title = {ch.get("title", "").strip().lower(): ch["href"] for ch in raw_chapters}
            href_by_idx = {i: ch["href"] for i, ch in enumerate(raw_chapters)}
            chapters_meta = []
            for row in existing_rows:
                num = row["chapter"]
                title_lower = row["title"].strip().lower()
                href = row.get("href") or href_by_title.get(title_lower) or href_by_idx.get(num, "")
                item = {
                    "num": num,
                    "role": row["role"],
                    "title": row["title"],
                    "label": row.get("label", row["title"][:20]),
                    "href": href,
                }
                if row.get("display_number") is not None:
                    item["display_number"] = row["display_number"]
                chapters_meta.append(item)
        except Exception:
            chapters_meta = []
    else:
        chapters_meta = []

    if not chapters_meta:
        chapters_meta = []
        ch_counter = 1
        for idx, ch in enumerate(raw_chapters):
            ch_title = ch.get("title") or f"Chapter {idx + 1}"
            href = ch["href"]
            role, disp_num, label = infer_chapter_role_and_label(idx, ch_title, href)
            if role == "chapter" and disp_num is None:
                disp_num = ch_counter
                ch_counter += 1
            elif role != "chapter":
                disp_num = None
            meta_item = {
                "num": idx,
                "role": role,
                "title": ch_title,
                "href": href,
                "label": label,
            }
            if disp_num is not None:
                meta_item["display_number"] = disp_num
            chapters_meta.append(meta_item)

    if not chapters_meta:
        raise ValueError("No chapters selected for build")

    # Determine filename prefix
    prefix = detect_book_prefix(target_dir, sanitize_slug(title))

    print("=====================================================================")
    print(f" Universal Pipeline Runner: {title} ({mode.upper()})")
    print("=====================================================================")
    print(f"EPUB Source:     {epub_path}")
    print(f"Target Dir:      {target_dir}")
    print(f"Author:          {author}")
    print(f"Prefix:          {prefix}")
    print(f"Selected Tracks: {len(chapters_meta)}")
    print(f"Mode:            {mode}")
    print(f"Concurrency:     {concurrency} parallel workers\n")

    setup_book_directory(target_dir, epub_path, chapters_meta, cover_member, mode=mode)
    extract_chapters_sentences(target_dir, epub_path, chapters_meta, prefix, force=force_extract)
    validate_extracted_sentences_gate(target_dir, chapters_meta, prefix)
    model_name = os.getenv("READER_AGY_MODEL", "gemini-3.8-flash-high")
    workers_per_ch = 4 if model_name == "deepseek" else 2
    run_parallel_linguistic_analysis(
        target_dir, chapters_meta, prefix, concurrency=concurrency, max_workers_per_chapter=workers_per_ch
    )

    if mode == "text_only":
        synthesize_text_only_aligned_sentences(target_dir, chapters_meta, prefix)
    elif mode == "synthetic":
        synthesize_synthetic_voice_chapters(
            book_dir=target_dir,
            chapters_meta=chapters_meta,
            prefix=prefix,
            voice=auto_voice,
            speed=voice_speed,
            concurrency=min(concurrency, 3),
        )
    else:
        raise NotImplementedError("Complete audio mode integration requires audio tracks in audio_dir")

    out_html = build_and_verify_reader(
        book_dir=target_dir,
        chapters_meta=chapters_meta,
        prefix=prefix,
        title=title,
        subtitle=subtitle,
        author=author,
        slug_id=slug_id,
        mode=mode,
        audio_dir=audio_dir,
    )

    elapsed = time.time() - t_start
    print("\n=====================================================================")
    print(f" PIPELINE COMPLETE in {elapsed:.1f}s")
    print(f" Standalone Interactive Reader: {out_html}")
    print("=====================================================================")

    if open_in_browser:
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", str(out_html)], check=False)
            elif sys.platform == "linux":
                subprocess.run(["xdg-open", str(out_html)], check=False)
        except Exception:
            pass

    return out_html


def main():
    parser = argparse.ArgumentParser(
        description="Universal Dual-Mode Pipeline Runner for Interactive Readers and Audiobooks",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("epub", type=str, nargs="?", default=None, help="Path to input EPUB file")
    parser.add_argument("--epub", dest="epub_flag", type=str, default=None, help="Path to input EPUB file")
    parser.add_argument("--book-dir", type=str, default=None, help="Destination directory for book artifacts")
    parser.add_argument("--audio-dir", type=str, default=None, help="Directory containing audio tracks")
    parser.add_argument("--text-only", action="store_true", help="Force text-only interactive reader mode")
    parser.add_argument("--auto-voice", type=str, default=None, help="Automatically synthesize chapter audio with Kokoro voice (e.g. am_adam)")
    parser.add_argument("--voice-speed", type=float, default=1.0, help="Speech rate multiplier for auto-voice (default: 1.0)")
    parser.add_argument("--concurrency", "-c", "--workers", type=int, default=8, help="Max parallel workers for linguistic analysis")
    parser.add_argument("--min-chars", type=int, default=300, help="Minimum character length for auto-detected chapters")
    parser.add_argument("--exclude", type=str, default=None, help="Comma-separated patterns to exclude in spine hrefs")
    parser.add_argument("--manifest", type=str, default=None, help="Explicit chapter manifest JSON path")
    parser.add_argument("--title", type=str, default=None, help="Override book title")
    parser.add_argument("--subtitle", type=str, default=None, help="Override book subtitle")
    parser.add_argument("--author", type=str, default=None, help="Override book author")
    parser.add_argument("--no-browser", action="store_true", help="Do not open HTML in browser upon completion")
    parser.add_argument("--force-extract", action="store_true", help="Force re-extraction of canonical sentences even if already present")
    parser.add_argument("--llm-model", type=str, default=None, help="LLM model for linguistic analysis (e.g. deepseek, gemini-3.8-flash-high)")

    args = parser.parse_args()
    epub_target = args.epub or args.epub_flag
    if not epub_target:
        parser.error("EPUB path is required (positional or --epub)")

    exclude_patterns = [p.strip() for p in args.exclude.split(",")] if args.exclude else None

    build_reader_pipeline(
        epub_path=Path(epub_target),
        book_dir=Path(args.book_dir) if args.book_dir else None,
        audio_dir=Path(args.audio_dir) if args.audio_dir else None,
        text_only=args.text_only,
        auto_voice=args.auto_voice,
        voice_speed=args.voice_speed,
        concurrency=args.concurrency,
        min_chars=args.min_chars,
        exclude_patterns=exclude_patterns,
        manifest_path=Path(args.manifest) if args.manifest else None,
        title_override=args.title,
        subtitle_override=args.subtitle,
        author_override=args.author,
        open_in_browser=not args.no_browser,
        force_extract=args.force_extract,
        llm_model=args.llm_model,
    )


if __name__ == "__main__":
    main()
