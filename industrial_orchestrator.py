"""Durable, book-scoped coordinator for the immersive reader pipeline.

The coordinator owns state and stage transitions. LLMs and audio engines are
workers: they receive explicit file paths through environment variables and
must produce contract files. Publication is intentionally not a stage here.
"""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from artifact_io import atomic_write_json
from chapter_resolver import discover_chapters
from intake_reconciler import verify_gate


SCHEMA_VERSION = 1
STAGES = ("intake", "linguistic", "acoustic", "alignment", "validation", "compile")


@contextlib.contextmanager
def _book_run_lock(book_dir: Path):
    """Prevent concurrent orchestrator executions against the same book directory."""
    lock_path = Path(book_dir) / ".orchestrator.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, OSError) as exc:
            raise RuntimeError(f"Another orchestrator run is active for {book_dir}") from exc
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _natural_sort_key(p: Path):
    match = re.search(r"\d+", p.stem)
    return int(match.group()) if match else p.stem


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_record(path: Optional[Path]) -> Optional[Dict]:
    if not path or not path.is_file():
        return None
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha256(path)}


def _load_state(path: Path) -> Dict:
    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "run_id": str(uuid.uuid4()),
            "status": "created",
            "current_stage": None,
            "chapters": {},
            "events": [],
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError(f"Unsupported or invalid coordinator state: {path}")
    data.setdefault("chapters", {})
    data.setdefault("events", [])
    return data


def _save_state(path: Path, state: Dict) -> None:
    state["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    atomic_write_json(path, state)


def _event(state: Dict, kind: str, **details) -> None:
    state.setdefault("events", []).append({
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "kind": kind,
        **details,
    })


def _chapter_rows(book_dir: Path) -> List[Dict]:
    rows = []
    for artifact in discover_chapters(str(book_dir)):
        rows.append({
            "chapter": artifact.chapter_number,
            "prefix": artifact.prefix,
            "canonical": str(artifact.canonical_path),
            "analysis": str(artifact.analysis_path),
            "acoustic": str(artifact.acoustic_path),
            "aligned": str(book_dir / f"{artifact.prefix}_aligned_sentences.json"),
        })
    return rows


def _set_chapters(state: Dict, rows: Iterable[Dict]) -> None:
    for row in rows:
        current = state["chapters"].setdefault(str(row["chapter"]), {
            "chapter": row["chapter"],
            "attempts": {stage: 0 for stage in STAGES},
            "status": "discovered",
            "failures": [],
        })
        current.update({key: value for key, value in row.items() if key != "chapter"})


def _attach_audio_mapping(book_dir: Path, rows: List[Dict]) -> None:
    """Attach only explicit intake mappings; never guess around a mismatch."""
    mapping_path = book_dir / "raw_intake_mapping.json"
    if not mapping_path.is_file():
        return
    data = json.loads(mapping_path.read_text(encoding="utf-8"))
    entries = data.get("entries", []) if isinstance(data, dict) else []
    by_chapter = {item.get("chapter"): item for item in entries if isinstance(item, dict)}
    audio_dir = book_dir / "audio"
    for row in rows:
        entry = by_chapter.get(row["chapter"], {})
        source_name = entry.get("audio_source")
        if source_name:
            source = audio_dir / source_name
            row["audio"] = str(source.resolve()) if source.is_file() else str(source)
        row["audio_mapping_status"] = entry.get(
            "audio_mapping_status",
            data.get("audio_mapping_status", "unknown") if isinstance(data, dict) else "unknown",
        )


def _attach_intake_plan(rows: List[Dict], plan: Dict) -> None:
    """Apply reconciled audio groups to canonical chapters in deterministic order."""
    audio = plan.get("audio", [])
    for mapping in plan.get("mappings", []):
        if mapping.get("kind") != "match":
            continue
        sources = [audio[index]["path"] for index in mapping.get("audio_indices", [])]
        for chapter_index in mapping.get("chapter_indices", []):
            if chapter_index >= len(rows):
                raise RuntimeError("intake plan chapter index exceeds discovered canonical chapters")
            rows[chapter_index]["audio_sources"] = sources
            if sources:
                rows[chapter_index]["audio"] = sources[0]
            rows[chapter_index]["audio_mapping_status"] = "approved"


def _worker_command(raw: Optional[str]) -> Optional[List[str]]:
    return shlex.split(raw) if raw else None


def _artifact_ready(stage: str, row: Dict) -> bool:
    """Validate an existing worker artifact before allowing resumable reuse."""
    output = Path(row["analysis"] if stage == "linguistic" else row["acoustic"])
    if not output.is_file() or output.stat().st_size == 0:
        return False
    try:
        data = json.loads(output.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return False
    if stage == "linguistic":
        try:
            canonical = json.loads(Path(row["canonical"]).read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            return False
        if not isinstance(data, list) or len(data) != len(canonical):
            return False
        for generated, source in zip(data, canonical):
            if generated.get("id") != source.get("id") or generated.get("text") != source.get("text"):
                return False
            if not isinstance(generated.get("trans"), str) or not generated["trans"].strip():
                return False
            if not isinstance(generated.get("vocab"), list):
                return False
        return True
    if stage == "acoustic":
        return (isinstance(data, dict) and bool(data.get("words"))) or (isinstance(data, list) and bool(data))
    return False


def _run_worker(stage: str, row: Dict, command: List[str], state: Dict, state_path: Path, max_attempts: int) -> bool:
    chapter = row["chapter"]
    record = state["chapters"][str(chapter)]
    output_key = "analysis" if stage == "linguistic" else "acoustic"
    output = Path(row[output_key])
    source = Path(row["canonical"] if stage == "linguistic" else row.get("audio", ""))
    env = os.environ.copy()
    env.update({
        "READER_STAGE": stage,
        "READER_CHAPTER": str(chapter),
        "READER_CANONICAL_PATH": row["canonical"],
        "READER_OUTPUT_PATH": str(output),
        "READER_AUDIO_PATH": row.get("audio", ""),
        "READER_AUDIO_PATHS_JSON": json.dumps(row.get("audio_sources", [row.get("audio", "")])),
    })
    for attempt in range(record["attempts"].get(stage, 0) + 1, max_attempts + 1):
        record["attempts"][stage] = attempt
        record["status"] = f"{stage}_running"
        _event(state, "worker_started", stage=stage, chapter=chapter, attempt=attempt)
        _save_state(state_path, state)
        worker_timeout = int(os.getenv("READER_WORKER_TIMEOUT", "1800"))
        try:
            completed = subprocess.run(command, cwd=str(Path.cwd()), env=env, text=True, capture_output=True, timeout=worker_timeout)
        except (OSError, subprocess.TimeoutExpired) as exc:
            completed = None
            error = f"{type(exc).__name__}: {exc}"
        else:
            error = (completed.stderr or completed.stdout or "worker exited non-zero").strip()[-4000:]
        if completed is not None and completed.returncode == 0 and output.is_file() and output.stat().st_size > 0:
            record[output_key + "_file"] = _file_record(output)
            record["status"] = f"{stage}_passed"
            _event(state, "worker_passed", stage=stage, chapter=chapter, attempt=attempt)
            _save_state(state_path, state)
            return True
        failure = {"stage": stage, "attempt": attempt, "reason": error or "worker did not produce output"}
        record["failures"].append(failure)
        record["status"] = f"{stage}_failed"
        _event(state, "worker_failed", chapter=chapter, **failure)
        _save_state(state_path, state)
    return False


def run(book_dir: Path, state_path: Path, linguistic_command: Optional[str] = None,
        acoustic_command: Optional[str] = None, max_attempts: int = 2, dry_run: bool = False,
        intake_plan_path: Optional[Path] = None,
        unsafe_allow_unapproved_workers: bool = False) -> int:
    book_dir = Path(book_dir).resolve()
    state_path = Path(state_path).resolve()
    with _book_run_lock(book_dir):
        state = _load_state(state_path)
        state["book_dir"] = str(book_dir)
        state["status"] = "running"
        rows = _chapter_rows(book_dir)
        if not rows:
            state["status"] = "blocked"
            _event(state, "blocked", stage="intake", reason="no canonical chapter artifacts")
            _save_state(state_path, state)
            return 1
        audio_candidates = sorted((book_dir / "audio").glob("*.mp3"), key=_natural_sort_key)
        for idx, row in enumerate(rows):
            if not row.get("audio") and len(audio_candidates) == len(rows):
                row["audio"] = str(audio_candidates[idx].resolve())
        _attach_audio_mapping(book_dir, rows)
        _set_chapters(state, rows)
        state["current_stage"] = "intake"
        state["intake"] = {"chapters": len(rows), "canonical_records": sum(len(json.loads(Path(r["canonical"]).read_text())) for r in rows)}
        _event(state, "intake_passed", chapters=len(rows))
        _save_state(state_path, state)
        if dry_run:
            state["status"] = "dry_run_passed"
            state["current_stage"] = None
            _save_state(state_path, state)
            return 0

        if (linguistic_command or acoustic_command) and not unsafe_allow_unapproved_workers:
            gate_path = Path(intake_plan_path or (book_dir / "intake_plan.json")).resolve()
            try:
                approved_plan = verify_gate(gate_path)
            except Exception as exc:
                state["status"] = "blocked"
                state["current_stage"] = "intake_gate"
                _event(state, "blocked", stage="intake_gate", reason=str(exc))
                _save_state(state_path, state)
                return 1
            state["intake_gate"] = {
                "status": "passed",
                "plan_path": str(gate_path),
                "plan_sha256": approved_plan["plan_sha256"],
                "minimum_confidence": approved_plan["minimum_confidence"],
            }
            _attach_intake_plan(rows, approved_plan)
            _set_chapters(state, rows)
            _event(state, "intake_gate_passed", plan_sha256=approved_plan["plan_sha256"])
            _save_state(state_path, state)

        for stage, raw_command in (("linguistic", linguistic_command), ("acoustic", acoustic_command)):
            state["current_stage"] = stage
            command = _worker_command(raw_command)
            for row in rows:
                output = Path(row["analysis"] if stage == "linguistic" else row["acoustic"])
                if _artifact_ready(stage, row):
                    state["chapters"][str(row["chapter"])]["status"] = f"{stage}_passed"
                    continue
                if output.is_file() and output.stat().st_size > 0:
                    state["chapters"][str(row["chapter"])]["failures"].append({
                        "stage": stage,
                        "reason": "existing artifact failed contract validation",
                    })
                    _event(state, "invalid_existing_artifact", stage=stage, chapter=row["chapter"])
                if not command:
                    state["chapters"][str(row["chapter"])]["failures"].append({"stage": stage, "reason": "worker command not configured"})
                    state["chapters"][str(row["chapter"])]["status"] = f"{stage}_blocked"
                    _event(state, "blocked", stage=stage, chapter=row["chapter"], reason="worker command not configured")
                    _save_state(state_path, state)
                    continue
                _run_worker(stage, row, command, state, state_path, max_attempts)
            if any(state["chapters"][str(r["chapter"])].get("status") in (f"{stage}_blocked", f"{stage}_failed") for r in rows):
                state["status"] = "blocked"
                _save_state(state_path, state)
                return 1

        state["current_stage"] = "delegated_pipeline"
        _event(state, "handoff", target="pipeline.py", reason="worker stages complete or externally prepared")
        state["status"] = "ready_for_pipeline"
        state["current_stage"] = None
        _save_state(state_path, state)
        return 0


run_orchestrator = run


def main() -> int:
    parser = argparse.ArgumentParser(description="Durable coordinator for the immersive reader pipeline")
    parser.add_argument("--book-dir", required=True, type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--linguistic-command", help="Worker command; receives READER_* environment variables")
    parser.add_argument("--acoustic-command", help="Worker command; receives READER_* environment variables")
    parser.add_argument("--max-attempts", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--intake-plan", type=Path, help="Approved hash-bound intake plan (defaults to BOOK_DIR/intake_plan.json)")
    parser.add_argument(
        "--unsafe-allow-unapproved-workers", action="store_true",
        help="Emergency legacy escape hatch; permits costly workers without the P2 intake gate",
    )
    args = parser.parse_args()
    state = args.state or args.book_dir / "industrial_run_state.json"
    return run(
        args.book_dir, state, args.linguistic_command, args.acoustic_command,
        max(1, args.max_attempts), args.dry_run, args.intake_plan,
        args.unsafe_allow_unapproved_workers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
