"""Fail-closed profiles for complete, abridged, and course audio products."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


PROFILE_FILENAME = "audio_content_profile.json"
COMPLETE = "complete"
ABRIDGED = "abridged"
COURSE = "course"
TEXT_ONLY = "text_only"
SYNTHETIC = "synthetic"
VALID_MODES = {COMPLETE, ABRIDGED, COURSE, TEXT_ONLY, SYNTHETIC}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_content_profile(book_dir: Path, errors: list[str]) -> dict:
    """Load a fail-closed product profile; absent remains a complete audiobook."""
    path = book_dir / PROFILE_FILENAME
    if not path.exists():
        return {"audio_content_mode": COMPLETE, "units_by_chapter": {}, "profile_sha256": None}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f"{PROFILE_FILENAME}: invalid JSON ({exc})")
        return {"audio_content_mode": None, "units_by_chapter": {}, "profile_sha256": None}
    if not isinstance(raw, dict) or raw.get("schema_version") != 1:
        errors.append(f"{PROFILE_FILENAME}: schema_version must be 1")
        return {"audio_content_mode": None, "units_by_chapter": {}, "profile_sha256": _sha256(path)}
    mode = raw.get("audio_content_mode")
    if mode not in VALID_MODES:
        errors.append(f"{PROFILE_FILENAME}: invalid audio_content_mode")
        return {"audio_content_mode": None, "units_by_chapter": {}, "profile_sha256": _sha256(path)}
    if mode in (COMPLETE, TEXT_ONLY, SYNTHETIC):
        return {"audio_content_mode": mode, "units_by_chapter": {}, "profile_sha256": _sha256(path)}
    spoken = raw.get("spoken_source")
    if not isinstance(spoken, dict) or not isinstance(spoken.get("path"), str) or not isinstance(spoken.get("sha256"), str):
        errors.append(f"{PROFILE_FILENAME}: {mode} requires hash-bound spoken_source")
    else:
        source = (book_dir / spoken["path"]).resolve()
        try:
            source.relative_to(book_dir.resolve())
        except ValueError:
            errors.append(f"{PROFILE_FILENAME}: spoken_source.path escapes book directory")
        else:
            if not source.is_file() or _sha256(source) != spoken["sha256"]:
                errors.append(f"{PROFILE_FILENAME}: spoken_source hash does not match")
    units_by_chapter = {}
    seen = set()
    units = raw.get("units")
    if not isinstance(units, list) or not units:
        errors.append(f"{PROFILE_FILENAME}: {mode} requires non-empty units")
        return {"audio_content_mode": mode, "units_by_chapter": units_by_chapter, "profile_sha256": _sha256(path)}
    for index, unit in enumerate(units):
        prefix = f"{PROFILE_FILENAME}: units[{index}]"
        if not isinstance(unit, dict):
            errors.append(f"{prefix} must be an object")
            continue
        chapter, audio_path, sentence_ids = unit.get("chapter"), unit.get("audio_path"), unit.get("sentence_ids")
        start, end = unit.get("audio_start"), unit.get("audio_end")
        if not isinstance(chapter, int) or chapter < 1 or not isinstance(audio_path, str) or not isinstance(sentence_ids, list) or not sentence_ids:
            errors.append(f"{prefix} requires chapter, audio_path, sentence_ids")
            continue
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)) or start < 0 or end <= start:
            errors.append(f"{prefix} requires valid audio interval")
        track = (book_dir / audio_path).resolve()
        try:
            track.relative_to(book_dir.resolve())
        except ValueError:
            errors.append(f"{prefix}: audio_path escapes book directory")
        else:
            if not track.is_file():
                errors.append(f"{prefix}: audio_path does not exist")
        ids = []
        for sentence_id in sentence_ids:
            key = (chapter, sentence_id)
            if not isinstance(sentence_id, str) or not sentence_id.strip() or key in seen:
                errors.append(f"{prefix}: sentence_ids must be unique non-empty strings")
                continue
            seen.add(key)
            ids.append(sentence_id)
        units_by_chapter.setdefault(chapter, []).append({"audio_path": audio_path, "audio_start": start, "audio_end": end, "sentence_ids": ids})
    return {"audio_content_mode": mode, "units_by_chapter": units_by_chapter, "profile_sha256": _sha256(path)}
