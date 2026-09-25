"""
Module: pipeline.py
Description: Release orchestrator for prepared audiobook-reader artifacts.
It aligns, validates, and compiles prepared chapter data. EPUB extraction and MLX Whisper
transcription are separate preparation stages.
"""

import os
import sys
import argparse
import json
import glob
import re
import hashlib
import contextlib
import fcntl
import subprocess
from pathlib import Path

PIPELINE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PIPELINE_DIR)

from dynamic_aligner import align_sentences_with_audio
from html_builder import build_master_reader
from validate_outputs import validate_for_release
from chapter_resolver import discover_chapters
from audio_resolver import resolve_chapter_audio
from run_manifest import update_manifest
from quality_gate import smoke_check_html
from artifact_io import atomic_write_json
from chapter_metadata import load_chapter_metadata
from content_profile import COMPLETE, load_content_profile


@contextlib.contextmanager
def _book_run_lock(book_dir):
    """Prevent two processes from mutating one book's artifacts concurrently."""
    lock_path = Path(book_dir) / ".reader-pipeline.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"Another reader pipeline run is active for {book_dir}") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _existing_manifest(book_dir):
    path = Path(book_dir) / "reader_run_manifest.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError, TypeError):
        return {}


def _load_audio_manifest(book_dir):
    path = Path(book_dir) / "audio_manifest.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        raise RuntimeError(f"Invalid audio_manifest.json: {exc}") from exc
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("audio_manifest.json must contain a non-empty entries list")
    result = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("chapter"), int):
            raise RuntimeError("audio_manifest.json contains an invalid chapter entry")
        source = Path(entry.get("source_path", "")).expanduser().resolve()
        expected = entry.get("source_sha256")
        if not source.is_file() or not isinstance(expected, str) or _file_sha256(str(source)) != expected:
            raise RuntimeError(f"Audio manifest source missing or changed for chapter {entry['chapter']}")
        if entry["chapter"] in result:
            raise RuntimeError(f"audio_manifest.json has duplicate chapter {entry['chapter']}")
        result[entry["chapter"]] = entry
    return result


def _write_audio_manifest(book_dir, audio_by_chapter, public_audio_base_url=None, public_book_id=None):
    entries = []
    for chapter in sorted(audio_by_chapter):
        source = Path(audio_by_chapter[chapter]).resolve()
        entry = {
            "chapter": chapter,
            "source_path": str(source),
            "source_sha256": _file_sha256(str(source)),
            "bytes": source.stat().st_size,
            "object_key": f"{public_book_id or Path(book_dir).name}/chapter_{chapter:02d}.mp3",
        }
        if public_audio_base_url:
            entry["public_url"] = f"{public_audio_base_url.rstrip('/')}/{entry['object_key']}"
        entries.append(entry)
    path = Path(book_dir) / "audio_manifest.json"
    atomic_write_json(path, {"schema_version": 1, "book_id": public_book_id or Path(book_dir).name, "entries": entries})
    return _load_audio_manifest(book_dir)


def _analysis_ready(path, canonical_path):
    """Require complete, non-empty analysis before alignment can begin."""
    try:
        with open(path, encoding="utf-8") as handle:
            analysis = json.load(handle)
        with open(canonical_path, encoding="utf-8") as handle:
            canonical = json.load(handle)
    except (OSError, ValueError, TypeError):
        return False
    return (
        isinstance(analysis, list)
        and len(analysis) == len(canonical)
        and all(isinstance(item.get("trans"), str) and item.get("trans", "").strip() for item in analysis)
    )


def _find_chapter_audio(audio_dir, chapter_number):
    """Return a path only when exactly one explicit chapter candidate exists."""
    resolution = resolve_chapter_audio(audio_dir, chapter_number)
    return str(resolution.path) if resolution.path else None


def _public_audio_url(public_audio_base_url, public_book_id, chapter_number):
    """Return the canonical public name without depending on local filenames."""
    if not public_audio_base_url or not public_book_id:
        return None
    canonical_chapter = chapter_number + 1 if chapter_number == 0 else chapter_number
    return (
        f"{public_audio_base_url.rstrip('/')}/{public_book_id}/"
        f"chapter_{canonical_chapter:02d}.mp3"
    )

def _auto_discover_and_build(book_dir, book_title=None, book_subtitle="Bilingual Synchronized Reader", book_author=None,
                             force_realign=False, public_audio_base_url=None, public_book_id=None,
                             chapter_metadata_path=None):
    """
    Universally auto-discovers all chapters in a book directory,
    runs global alignment on ready pairs, and compiles the Master Interactive Reader.
    """
    book_dir = os.path.abspath(book_dir)
    audio_dir = os.path.join(book_dir, "audio")
    
    # Auto-infer book metadata if omitted
    folder_name = os.path.basename(book_dir)
    if " - " in folder_name and (not book_title or not book_author):
        parts = folder_name.split(" - ")
        if not book_title:
            book_title = parts[0].strip()
        if not book_author:
            book_author = parts[1].strip()
    elif not book_title:
        book_title = folder_name
    if not book_author:
        book_author = "Author"
        
    master_html_name = f"{book_title.replace(' ', '_')}_Interactive_Reader.html"
    master_html_path = os.path.join(book_dir, master_html_name)
    
    # Discover all chapter artifacts through the shared resolver.
    chapter_artifacts = discover_chapters(book_dir)
    if not chapter_artifacts:
        print(f"No canonical sentence files found in {book_dir}")
        return 0, master_html_path

    metadata_path = Path(chapter_metadata_path or (Path(book_dir) / "chapter_metadata.json"))
    chapter_metadata = None
    if metadata_path.is_file():
        chapter_metadata = load_chapter_metadata(
            metadata_path,
            expected_chapters=[artifact.chapter_number for artifact in chapter_artifacts],
        )

    profile_errors = []
    content_profile = load_content_profile(Path(book_dir), profile_errors)
    if profile_errors:
        raise RuntimeError("Invalid audio content profile: " + "; ".join(profile_errors))
    audio_manifest = _load_audio_manifest(book_dir)
    discovered_audio = {}
    if audio_manifest is None:
        if content_profile["audio_content_mode"] != COMPLETE:
            for artifact in chapter_artifacts:
                units = content_profile["units_by_chapter"].get(artifact.chapter_number, [])
                tracks = {str((Path(book_dir) / unit["audio_path"]).resolve()) for unit in units}
                if len(tracks) == 1:
                    discovered_audio[artifact.chapter_number] = tracks.pop()
        else:
            for artifact in chapter_artifacts:
                candidate = _find_chapter_audio(audio_dir, artifact.chapter_number)
                if candidate:
                    discovered_audio[artifact.chapter_number] = candidate
        if len(discovered_audio) != len(chapter_artifacts):
            raise RuntimeError("Create audio_manifest.json or resolve every chapter to exactly one audio file")
        audio_manifest = _write_audio_manifest(book_dir, discovered_audio, public_audio_base_url, public_book_id)
        
    aligned_configs = []
    manifest_chapters = []
    previous_manifest = _existing_manifest(book_dir)
    previous_chapters = {
        item.get("chapter"): item
        for item in previous_manifest.get("chapters", [])
        if isinstance(item, dict)
    }
    input_files = []
    
    for artifact in chapter_artifacts:
        c_path = str(artifact.canonical_path)
        prefix = artifact.prefix
        ch_num = artifact.chapter_number
            
        analysis_path = str(artifact.analysis_path)
        aligned_path = os.path.join(book_dir, f"{prefix}_aligned_sentences.json")
        acoustic_path = str(artifact.acoustic_path)
        
        # Audio file matching
        audio_entry = audio_manifest.get(ch_num)
        audio_file = audio_entry.get("source_path") if audio_entry else None
        public_audio_url = audio_entry.get("public_url") if audio_entry else None
        if not public_audio_url:
            public_audio_url = _public_audio_url(public_audio_base_url, public_book_id, ch_num)
        if public_audio_url:
            audio_file_rel = public_audio_url
        else:
            audio_file_rel = f"./audio/{os.path.basename(audio_file)}" if audio_file else f"./audio/chapter_{ch_num:02d}.mp3"
                
        has_analysis = os.path.exists(analysis_path) and _analysis_ready(analysis_path, c_path)
        has_acoustic = os.path.exists(acoustic_path) and os.path.getsize(acoustic_path) > 1000
        canonical_sha256 = _file_sha256(c_path) if os.path.exists(c_path) else None
        analysis_sha256 = _file_sha256(analysis_path) if os.path.exists(analysis_path) else None
        acoustic_sha256 = _file_sha256(acoustic_path) if os.path.exists(acoustic_path) else None
        audio_sha256 = _file_sha256(audio_file) if audio_file and os.path.exists(audio_file) else None
        for role, path in (
            ("canonical", c_path),
            ("analysis", analysis_path),
            ("acoustic", acoustic_path),
            ("audio", audio_file),
        ):
            if path and os.path.isfile(path):
                input_files.append((role, path))
        manifest_chapters.append({
            "chapter": ch_num,
            "status": "ready" if has_analysis and has_acoustic else "blocked",
            "canonical": os.path.relpath(c_path, book_dir),
            "analysis": os.path.relpath(analysis_path, book_dir),
            "acoustic": os.path.relpath(acoustic_path, book_dir),
            "aligned": os.path.relpath(aligned_path, book_dir),
            "canonical_sha256": canonical_sha256,
            "analysis_sha256": analysis_sha256,
            "acoustic_sha256": acoustic_sha256,
            "audio_sha256": audio_sha256,
        })
        
        if has_analysis and has_acoustic:
            needs_align = force_realign or not os.path.exists(aligned_path)
            previous = previous_chapters.get(ch_num, {})
            if any(previous.get(key) != value for key, value in (
                ("canonical_sha256", canonical_sha256),
                ("analysis_sha256", analysis_sha256),
                ("acoustic_sha256", acoustic_sha256),
                ("audio_sha256", audio_sha256),
            )):
                needs_align = True
            if not needs_align:
                if os.path.getmtime(acoustic_path) > os.path.getmtime(aligned_path) or os.path.getmtime(analysis_path) > os.path.getmtime(aligned_path):
                    needs_align = True
                    
            if needs_align:
                print(f"--> Aligning {prefix} with Full-Chapter Non-Monotonic Aligner...")
                align_sentences_with_audio(acoustic_path, analysis_path, aligned_path)
                
            # Extract Chapter Title
            with open(c_path, 'r', encoding='utf-8') as f:
                c_data = json.load(f)
            h_texts = [d["text"] for d in c_data if d.get("is_heading")]
            metadata = chapter_metadata.get(ch_num) if chapter_metadata else None
            if metadata:
                title = metadata["title"]
            elif ch_num == 0:
                title = "Preface"
            elif len(h_texts) >= 2:
                title = h_texts[1]
            elif len(h_texts) >= 1:
                title = h_texts[0]
            else:
                title = f"Chapter {ch_num}"
                
            chapter_config = {
                "num": ch_num,
                "title": title,
                # A verified public URL is authoritative for published readers;
                # local paths are only a preview fallback when no URL exists.
                "audio": audio_file_rel,
                "public_audio": public_audio_url,
                "aligned_json": aligned_path
            }
            if metadata:
                chapter_config.update(metadata)
            aligned_configs.append(chapter_config)
            
    for entry in manifest_chapters:
        aligned_file = Path(book_dir) / entry["aligned"]
        if aligned_file.exists():
            entry["aligned_sha256"] = _file_sha256(aligned_file)
            if entry["status"] == "ready":
                entry["status"] = "aligned"
    update_manifest(book_dir, manifest_chapters, status="prepared", input_files=input_files)
    print(f"\nDiscovered {len(aligned_configs)} / {len(chapter_artifacts)} ready aligned chapters for {book_title}")
    if not aligned_configs:
        update_manifest(book_dir, manifest_chapters, status="blocked", input_files=input_files)
        print("Release blocked: no chapters have complete analysis and acoustic artifacts.")
        return 0, master_html_path
    if aligned_configs:
        report_path = os.path.join(book_dir, "reader_validation_report.json")
        report, release_token = validate_for_release(Path(book_dir), Path(report_path), require_provenance=True)
        if release_token is None:
            update_manifest(book_dir, manifest_chapters, status="blocked", input_files=input_files)
            print(f"Release blocked. See {report_path}")
            return 0, master_html_path
        print("--> Compiling Master Multi-Chapter Interactive Reader...")
        build_master_reader(
            book_title=book_title,
            book_subtitle=book_subtitle,
            book_author=book_author,
            chapters_config=aligned_configs,
            output_html_path=master_html_path,
            release_token=release_token,
            release_report_path=report_path,
            book_id=public_book_id,
        )
        smoke = smoke_check_html(Path(master_html_path), expected_chapters=len(aligned_configs))
        if smoke["status"] != "passed":
            update_manifest(book_dir, manifest_chapters, status="blocked", input_files=input_files)
            raise RuntimeError("Reader smoke check failed: " + "; ".join(smoke["errors"]))
        # This command compiles locally; it does not upload or externally verify
        # the reader.  Keep the manifest honest so downstream publication steps
        # cannot mistake local compilation for a public release.
        update_manifest(book_dir, manifest_chapters, status="compiled", input_files=input_files)
        print(f"Successfully generated/updated: {master_html_path}")
        
    return len(aligned_configs), master_html_path


def auto_discover_and_build(book_dir, book_title=None, book_subtitle="Bilingual Synchronized Reader", book_author=None,
                            force_realign=False, public_audio_base_url=None, public_book_id=None,
                            chapter_metadata_path=None):
    book_dir = os.path.abspath(book_dir)
    with _book_run_lock(book_dir):
        return _auto_discover_and_build(
            book_dir, book_title, book_subtitle, book_author,
            force_realign, public_audio_base_url, public_book_id, chapter_metadata_path,
        )

def main():
    parser = argparse.ArgumentParser(description="Universal Interactive Audiobook Reader Industrial Pipeline")
    parser.add_argument("--book-dir", required=True, help="Path to book directory in Obsidian")
    parser.add_argument("--title", help="Book title (inferred automatically if omitted)")
    parser.add_argument("--author", help="Book author (inferred automatically if omitted)")
    parser.add_argument("--subtitle", default="Bilingual Synchronized Reader", help="Book subtitle")
    parser.add_argument("--realign", action="store_true", help="Force re-alignment across all chapters")
    parser.add_argument("--public-audio-base-url", help="Optional public audio CDN base URL")
    parser.add_argument("--public-book-id", help="Public audio namespace, required with --public-audio-base-url")
    parser.add_argument("--chapter-metadata", help="Validated display metadata JSON (defaults to BOOK_DIR/chapter_metadata.json)")
    parser.add_argument("--publish", action="store_true", help="Automatically upload to R2, chunk, seal, and deploy to Audible production portal")
    
    args = parser.parse_args()

    if args.publish:
        if not args.public_audio_base_url:
            args.public_audio_base_url = "https://audio.audiblelibrary.online"
        if not args.public_book_id:
            folder = Path(args.book_dir).name
            slug = re.sub(r'[^a-zA-Z0-9]+', '-', folder.lower()).strip('-')
            args.public_book_id = slug

    ready_count, master_html_path = auto_discover_and_build(
        book_dir=args.book_dir,
        book_title=args.title,
        book_subtitle=args.subtitle,
        book_author=args.author,
        force_realign=args.realign,
        public_audio_base_url=args.public_audio_base_url,
        public_book_id=args.public_book_id,
        chapter_metadata_path=args.chapter_metadata,
    )
    if ready_count == 0:
        raise SystemExit(1)

    if args.publish:
        audible_publisher = Path("/Users/lindy/Vault/Audible/scripts/publish_book.py")
        if not audible_publisher.is_file():
            print(f"❌ [PUBLISH FAILED] Publisher script not found at {audible_publisher}")
            raise SystemExit(1)

        audio_dir = Path(args.book_dir) / "audio"
        audio_dir_arg = str(audio_dir) if audio_dir.is_dir() else str(args.book_dir)
        print(f"\n🚀 [PIPELINE -> AUTO-PUBLISH] Triggering automated production release for '{args.public_book_id}'...")
        cmd = [
            sys.executable, str(audible_publisher),
            "--id", args.public_book_id,
            "--src", master_html_path,
            "--audio-dir", audio_dir_arg,
        ]
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print("❌ [PIPELINE -> AUTO-PUBLISH] Publication rejected by gatekeeper!")
            raise SystemExit(1)
        print(f"🎉 [PIPELINE -> AUTO-PUBLISH] Finished! '{args.public_book_id}' is live and verified on production.")

if __name__ == "__main__":
    main()
