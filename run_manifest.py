"""Create reproducibility metadata without processing or copying book content."""

import argparse
import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from artifact_io import atomic_write_json


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_manifest(book_dir, source_files, audio_files, model="mlx-community/whisper-large-v3-turbo"):
    try:
        repo_dir = Path(__file__).resolve().parent
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_dir, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_revision": revision,
        "acoustic_model": model,
        "source_files": [{"path": str(path.resolve()), "sha256": sha256(path)} for path in source_files],
        "audio_files": [{"path": str(path.resolve()), "sha256": sha256(path)} for path in audio_files],
    }
    output = book_dir / "reader_run_manifest.json"
    atomic_write_json(output, manifest)
    return output


def _input_record(path, role):
    path = Path(path).expanduser().resolve()
    return {
        "role": role,
        "path": str(path),
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
    }


def update_manifest(book_dir, chapters, status="in_progress", model="mlx-community/whisper-large-v3-turbo", input_files=None):
    """Write a resumable chapter-stage manifest without copying book content."""
    try:
        repo_dir = Path(__file__).resolve().parent
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo_dir, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        revision = None
    existing = {}
    output = Path(book_dir) / "reader_run_manifest.json"
    if output.exists():
        try:
            existing = json.loads(output.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            existing = {}
    if input_files is None:
        recorded_inputs = existing.get("input_files", [])
    else:
        recorded_inputs = [_input_record(path, role) for role, path in input_files if Path(path).is_file()]
    manifest = {
        "schema_version": 2,
        "run_id": existing.get("run_id") or uuid.uuid4().hex,
        "created_at": existing.get("created_at") or datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_revision": revision,
        "acoustic_model": model,
        "status": status,
        "source_files": existing.get("source_files", []),
        "audio_files": existing.get("audio_files", []),
        "input_files": recorded_inputs,
        "chapters": chapters,
    }
    atomic_write_json(output, manifest)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("book_dir", type=Path)
    parser.add_argument("--source", type=Path, action="append", default=[])
    parser.add_argument("--audio", type=Path, action="append", default=[])
    parser.add_argument("--model", default="mlx-community/whisper-large-v3-turbo")
    args = parser.parse_args()
    print(create_manifest(args.book_dir.expanduser().resolve(), args.source, args.audio, args.model))


if __name__ == "__main__":
    main()
