"""Transactional local bookshelf publication (DEPRECATED).

DEPRECATION NOTICE:
Direct use of `local_publisher.py` is deprecated. Use `universal_runner.py --publish`
or `pipeline.py --publish` with `publish_book.py` as the canonical production release runner.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import Dict, Iterable

from artifact_io import atomic_write_json
from quality_gate import smoke_check_html


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_verified(source: Path, destination: Path) -> Dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    source_hash = _sha256(source)
    destination_hash = _sha256(destination)
    if source_hash != destination_hash:
        raise RuntimeError(f"copy verification failed: {source}")
    return {
        "path": str(destination.relative_to(destination.parents[1])),
        "bytes": destination.stat().st_size,
        "sha256": destination_hash,
    }


def publish_local_release(
    book_dir: Path,
    html_path: Path,
    shelf_root: Path,
    book_id: str,
    run_id: str,
) -> Dict:
    """Stage, verify, and atomically activate one local shelf release."""
    book_dir = Path(book_dir).resolve()
    html_path = Path(html_path).resolve()
    shelf_book = Path(shelf_root).expanduser().resolve() / book_id
    releases = shelf_book / "releases"
    staging = shelf_book / ".staging" / run_id
    final = releases / run_id
    if final.exists():
        receipt = final / "release.json"
        if receipt.is_file():
            return json.loads(receipt.read_text(encoding="utf-8"))
        raise RuntimeError(f"release directory already exists without receipt: {final}")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True)

    files = [_copy_verified(html_path, staging / "reader.html")]
    audio_manifest_path = book_dir / "audio_manifest.json"
    if not audio_manifest_path.is_file():
        raise RuntimeError("audio_manifest.json is required for publication")
    audio_manifest = json.loads(audio_manifest_path.read_text(encoding="utf-8"))
    entries = audio_manifest.get("entries", [])
    if not entries:
        raise RuntimeError("audio_manifest.json has no entries")
    for entry in entries:
        source = Path(entry["source_path"]).expanduser().resolve()
        expected = entry.get("source_sha256")
        if not source.is_file() or (expected and _sha256(source) != expected):
            raise RuntimeError(f"audio source missing or changed: {source}")
        files.append(_copy_verified(source, staging / "audio" / source.name))

    smoke = smoke_check_html(staging / "reader.html", expected_chapters=len(entries))
    if smoke["status"] != "passed":
        raise RuntimeError("staged reader smoke check failed: " + "; ".join(smoke["errors"]))
    receipt = {
        "schema_version": 1,
        "status": "verified",
        "book_id": book_id,
        "release_id": run_id,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "files": files,
        "smoke": smoke,
    }
    atomic_write_json(staging / "release.json", receipt)

    releases.mkdir(parents=True, exist_ok=True)
    os.replace(staging, final)
    shelf_book.mkdir(parents=True, exist_ok=True)
    next_link = shelf_book / f".current.{run_id}.tmp"
    next_link.symlink_to(Path("releases") / run_id, target_is_directory=True)
    os.replace(next_link, shelf_book / "current")
    receipt["status"] = "published"
    receipt["active_path"] = str((shelf_book / "current").resolve())
    atomic_write_json(final / "release.json", receipt)
    atomic_write_json(shelf_book / "current.json", receipt)
    return receipt


def rollback_local_release(shelf_root: Path, book_id: str, release_id: str) -> Dict:
    shelf_book = Path(shelf_root).expanduser().resolve() / book_id
    target = shelf_book / "releases" / release_id
    receipt_path = target / "release.json"
    if not receipt_path.is_file():
        raise FileNotFoundError(f"verified release not found: {target}")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    next_link = shelf_book / f".current.rollback.{os.getpid()}.tmp"
    next_link.symlink_to(Path("releases") / release_id, target_is_directory=True)
    os.replace(next_link, shelf_book / "current")
    receipt = {**receipt, "status": "published", "rollback_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    atomic_write_json(shelf_book / "current.json", receipt)
    return receipt
