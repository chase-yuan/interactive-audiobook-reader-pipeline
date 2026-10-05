"""Journaled, idempotent publication to local archive, R2, and GitHub Pages.

Publication is an explicit protocol, not a shell script.  Every completed step is
recorded atomically and reused only while the release fingerprint is unchanged.
The public Git commit is created only after every audio object passes strict
beginning/middle/end HTTP 206 probes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
import re
from pathlib import Path
from typing import Callable, Dict, Optional
from urllib.request import Request, urlopen

from artifact_io import atomic_write_json
from intake_reconciler import verify_gate
from publication_verify import probe_audio_ranges
from r2_upload import sync_manifest


SCHEMA_VERSION = 1
STEPS = ("preflight", "archive", "r2_upload", "remote_verify", "git_stage", "git_push", "smoke_test")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _release_fingerprint(config: Dict) -> str:
    records = {"book_id": config["book_id"]}
    for key in ("reader_html", "audio_manifest", "cover", "intake_plan", "release_report"):
        if config.get(key):
            path = Path(config[key]).expanduser().resolve()
            records[key] = {"path": str(path), "sha256": _sha256(path) if path.is_file() else None}
    records["manifest_entry"] = resolve_manifest_entry(config)
    encoded = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _format_duration(seconds: float) -> str:
    minutes = int(round(max(0.0, seconds) / 60))
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes:02d}m" if hours else f"{minutes}m"


def resolve_manifest_entry(config: Dict) -> Dict:
    """Fill deterministic shelf fields from the reader and approved intake evidence."""
    entry = dict(config.get("manifest_entry") or {})
    book_id = config.get("book_id")
    if not book_id:
        return entry
    entry["id"] = book_id
    entry.setdefault("cover", f"assets/covers/{book_id}.jpg")
    entry.setdefault("readerUrl", f"books/{book_id}/index.html")

    reader_path = Path(config.get("reader_html", "")).expanduser()
    if "chaptersCount" not in entry and reader_path.is_file():
        reader_text = reader_path.read_text(encoding="utf-8")
        entry["chaptersCount"] = len(re.findall(r'<section class="chapter-section[^>]*\bid="chapter-', reader_text))

    duration = None
    if config.get("intake_plan"):
        plan = verify_gate(Path(config["intake_plan"]))
        used_indices = {
            index
            for mapping in plan.get("mappings", []) if mapping.get("kind") == "match"
            for index in mapping.get("audio_indices", [])
        }
        duration = sum(float(plan["audio"][index].get("duration", 0.0)) for index in used_indices)
    elif config.get("audio_manifest") and Path(config["audio_manifest"]).is_file():
        audio_data = json.loads(Path(config["audio_manifest"]).read_text(encoding="utf-8"))
        if audio_data.get("entries") and all("duration" in item for item in audio_data["entries"]):
            duration = sum(float(item["duration"]) for item in audio_data["entries"])
    if "totalDuration" not in entry and duration is not None:
        entry["totalDuration"] = _format_duration(duration)
    return entry


def _load_journal(path: Path, fingerprint: str, book_id: str) -> Dict:
    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "book_id": book_id,
            "release_fingerprint": fingerprint,
            "status": "running",
            "steps": {step: {"status": "pending"} for step in STEPS},
            "events": [],
        }
    journal = json.loads(path.read_text(encoding="utf-8"))
    if journal.get("schema_version") != SCHEMA_VERSION:
        raise RuntimeError("unsupported publisher journal schema")
    if journal.get("release_fingerprint") != fingerprint:
        raise RuntimeError("publisher inputs changed; use a new journal after reviewing the release")
    return journal


def _git(repo: Path, *args: str, timeout: int = 300) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True, text=True, timeout=timeout)


def _changed_paths(repo: Path) -> set[str]:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=str(repo), check=True, capture_output=True, timeout=300,
    )
    return {
        record[3:].decode("utf-8", errors="replace")
        for record in completed.stdout.split(b"\0") if record
    }


def _copy_atomic(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp")
    shutil.copy2(source, temporary)
    if _sha256(source) != _sha256(temporary):
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"copy verification failed: {source}")
    os.replace(temporary, destination)


def _prepare_cover(source: Path, destination: Path) -> None:
    """Center-crop a cover to 2:3 JPEG; permit JPEG copy when Pillow is absent."""
    try:
        from PIL import Image
    except ImportError:
        if source.suffix.casefold() not in {".jpg", ".jpeg"}:
            raise RuntimeError("Pillow is required to convert a non-JPEG cover")
        _copy_atomic(source, destination)
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{os.getpid()}.tmp.jpg")
    with Image.open(source) as image:
        image = image.convert("RGB")
        width, height = image.size
        target_ratio = 2 / 3
        if width / height > target_ratio:
            crop_width = int(height * target_ratio)
            left = (width - crop_width) // 2
            image = image.crop((left, 0, left + crop_width, height))
        elif width / height < target_ratio:
            crop_height = int(width / target_ratio)
            top = (height - crop_height) // 2
            image = image.crop((0, top, width, top + crop_height))
        image.resize((800, 1200), Image.Resampling.LANCZOS).save(temporary, "JPEG", quality=90, optimize=True)
    os.replace(temporary, destination)


def update_library_manifest(path: Path, entry: Dict) -> Dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    books = data.get("books")
    if not isinstance(books, list):
        raise ValueError("library manifest must contain a books list")
    if not entry.get("id"):
        raise ValueError("manifest entry requires id")
    updated = False
    for index, existing in enumerate(books):
        if existing.get("id") == entry["id"]:
            books[index] = entry
            updated = True
            break
    if not updated:
        books.append(entry)
    data["updatedAt"] = time.strftime("%Y-%m-%d", time.gmtime())
    atomic_write_json(path, data)
    return data


def validate_single_manifest_source(index_text: str) -> None:
    """Reject embedded shelf catalogs, including aliases used to evade the old check."""
    forbidden = ("INLINE_MANIFEST", "BUILTIN_MANIFEST_DATA", "EMBEDDED_MANIFEST")
    found = [name for name in forbidden if name in index_text]
    if found or re.search(r"\b(?:const|let|var)\s+ALL_BOOKS\s*=\s*\[\s*\{", index_text):
        detail = ", ".join(found) if found else "inline ALL_BOOKS array"
        raise RuntimeError(f"portal index embeds shelf data ({detail}); manifest.json must be the single data source")


def validate_reader_audio_contract(reader_text: str, entries: list[Dict]) -> None:
    urls = re.findall(r'\bdata-public-audio="([^"]*)"', reader_text)
    expected = [entry.get("public_url") for entry in entries]
    if len(urls) != len(entries):
        raise RuntimeError(f"reader/audio manifest chapter count mismatch: {len(urls)} != {len(entries)}")
    if any(not isinstance(url, str) or not re.match(r"^https://", url) for url in expected):
        raise ValueError("every audio manifest entry requires an HTTPS public_url")
    if urls != expected:
        raise RuntimeError("reader public audio URLs differ from audio_manifest.json")


def validate_release_report(reader_text: str, report_path: Path) -> None:
    report_path = Path(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("release_ready") is not True or report.get("errors") or report.get("warnings"):
        raise RuntimeError("release report does not authorize publication")
    match = re.search(r'<meta name="reader-release-report-sha256" content="([0-9a-f]{64})">', reader_text)
    if not match or match.group(1) != _sha256(report_path):
        raise RuntimeError("reader was not compiled from the supplied release report")


def _preflight(config: Dict, context: Dict) -> Dict:
    required = (
        "book_id", "reader_html", "audio_manifest", "intake_plan", "release_report",
        "portal_repo", "manifest_entry", "public_reader_url", "hosting_provider",
        "cloudflare_project", "deployment_mode",
    )
    missing = [key for key in required if not config.get(key)]
    if missing:
        raise ValueError("missing publisher configuration: " + ", ".join(missing))
    if config.get("deployment_mode") != "manifest_publisher":
        raise RuntimeError("legacy deployment paths are not supported by the production publisher")
    if config.get("hosting_provider") != "cloudflare_pages":
        raise RuntimeError("hosting_provider must be cloudflare_pages for production publication")
    reader = Path(config["reader_html"]).expanduser().resolve()
    audio_manifest = Path(config["audio_manifest"]).expanduser().resolve()
    repo = Path(config["portal_repo"]).expanduser().resolve()
    release_report = Path(config["release_report"]).expanduser().resolve()
    for path in (reader, audio_manifest, release_report, repo / "manifest.json", repo / "index.html"):
        if not path.exists():
            raise FileNotFoundError(path)
    if config.get("enforce_single_manifest", True):
        validate_single_manifest_source((repo / "index.html").read_text(encoding="utf-8"))
    intake_plan = json.loads(Path(config["intake_plan"]).expanduser().read_text(encoding="utf-8"))
    if float(intake_plan.get("threshold", 0.0)) < 0.90 and not config.get("allow_recovery_intake"):
        raise RuntimeError("intake plan uses recovery threshold; publication requires explicit allow_recovery_intake")
    entries = json.loads(audio_manifest.read_text(encoding="utf-8")).get("entries", [])
    if not entries:
        raise ValueError("audio manifest has no entries")
    for entry in entries:
        source = Path(entry.get("source_path", ""))
        if not source.is_file() or (entry.get("source_sha256") and _sha256(source) != entry["source_sha256"]):
            raise RuntimeError(f"audio source missing or changed: {source}")
        if not entry.get("public_url") or not entry.get("bytes"):
            raise ValueError(f"audio entry lacks public_url/bytes: {entry.get('object_key')}")
    reader_text = reader.read_text(encoding="utf-8")
    validate_reader_audio_contract(reader_text, entries)
    validate_release_report(reader_text, release_report)
    local_audio = repo / "books" / config["book_id"] / "audio"
    if local_audio.is_symlink():
        raise RuntimeError(f"portal book audio must not be a local symlink: {local_audio}")
    shelf_entry = resolve_manifest_entry(config)
    missing_shelf = [key for key in ("title", "author", "chaptersCount", "totalDuration") if not shelf_entry.get(key)]
    if missing_shelf:
        raise ValueError("incomplete derived shelf metadata: " + ", ".join(missing_shelf))
    if _changed_paths(repo):
        raise RuntimeError("portal repository must be clean before publication")
    return {
        "reader_sha256": _sha256(reader), "audio_entries": len(entries),
        "portal_repo": str(repo), "base_commit": _git(repo, "rev-parse", "HEAD").stdout.strip(),
        "shelf_entry": shelf_entry,
    }


def _archive(config: Dict, context: Dict) -> Dict:
    destination = config.get("archive_html")
    if not destination:
        return {"status": "not_configured"}
    source = Path(config["reader_html"]).expanduser().resolve()
    destination = Path(destination).expanduser().resolve()
    if destination.is_file() and _sha256(destination) == _sha256(source):
        return {"status": "skipped", "path": str(destination), "sha256": _sha256(source)}
    _copy_atomic(source, destination)
    return {"status": "archived", "path": str(destination), "sha256": _sha256(destination)}


def _r2(config: Dict, context: Dict) -> Dict:
    return sync_manifest(Path(config["audio_manifest"]))


def _remote_verify(config: Dict, context: Dict) -> Dict:
    manifest = json.loads(Path(config["audio_manifest"]).read_text(encoding="utf-8"))
    probes = 0
    for entry in manifest["entries"]:
        probes += len(probe_audio_ranges(entry["public_url"], int(entry["bytes"])))
    return {"audio_entries": len(manifest["entries"]), "range_probes": probes, "status": "passed"}


def _git_stage(config: Dict, context: Dict) -> Dict:
    repo = Path(config["portal_repo"]).expanduser().resolve()
    book_id = config["book_id"]
    reader_destination = repo / "books" / book_id / "index.html"
    whitelist = [reader_destination.relative_to(repo), Path("manifest.json")]
    if config.get("cover"):
        whitelist.append(Path("assets") / "covers" / f"{book_id}.jpg")
    allowed = {str(path) for path in whitelist}
    unexpected = _changed_paths(repo) - allowed
    if unexpected:
        raise RuntimeError("portal repository has unrelated changes: " + ", ".join(sorted(unexpected)))

    preflight = context["journal"]["steps"]["preflight"].get("result", {})
    base_commit = preflight.get("base_commit")
    current_commit = _git(repo, "rev-parse", "HEAD").stdout.strip()
    if base_commit and current_commit != base_commit and not _changed_paths(repo):
        changed_since_base = set(_git(repo, "diff", "--name-only", f"{base_commit}..{current_commit}").stdout.splitlines())
        if changed_since_base and changed_since_base <= allowed:
            return {
                "status": "recovered_commit", "committed": True,
                "commit": current_commit, "paths": sorted(changed_since_base),
            }
        raise RuntimeError("portal HEAD changed unexpectedly after preflight")

    _copy_atomic(Path(config["reader_html"]).expanduser().resolve(), reader_destination)
    if config.get("cover"):
        cover_source = Path(config["cover"]).expanduser().resolve()
        cover_destination = repo / "assets" / "covers" / f"{book_id}.jpg"
        _prepare_cover(cover_source, cover_destination)
    update_library_manifest(repo / "manifest.json", resolve_manifest_entry(config))
    _git(repo, "add", "--", *(str(path) for path in whitelist))
    staged_check = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=str(repo),
        check=False, capture_output=True, text=True, timeout=300,
    )
    if staged_check.returncode not in (0, 1):
        raise RuntimeError(staged_check.stderr or "git diff --cached failed")
    staged = staged_check.returncode == 1
    if not staged:
        return {"status": "skipped", "committed": False, "paths": [str(path) for path in whitelist]}
    message = config.get("commit_message") or f"publish: {book_id} interactive reader"
    _git(repo, "commit", "-m", message, "--", *(str(path) for path in whitelist))
    commit = _git(repo, "rev-parse", "HEAD").stdout.strip()
    return {"status": "committed", "committed": True, "commit": commit, "paths": [str(path) for path in whitelist]}


def _git_push(config: Dict, context: Dict) -> Dict:
    staged = context["journal"]["steps"]["git_stage"].get("result", {})
    if not staged.get("committed"):
        return {"status": "skipped", "reason": "no content changes"}
    repo = Path(config["portal_repo"]).expanduser().resolve()
    remote = config.get("git_remote", "origin")
    branch = config.get("git_branch", "main")
    _git(repo, "push", remote, branch)
    return {"status": "pushed", "remote": remote, "branch": branch, "commit": staged["commit"]}


def _smoke_test(config: Dict, context: Dict) -> Dict:
    request = Request(config["public_reader_url"], headers={"User-Agent": "immersive-reader-publisher/1.0"})
    with urlopen(request, timeout=30) as response:
        body = response.read(4096)
        status = response.status
    if status != 200 or b"<html" not in body.lower():
        raise RuntimeError(f"reader smoke test failed: HTTP {status}")
    return {"status": "passed", "http_status": status, "url": config["public_reader_url"]}


DEFAULT_ACTIONS = {
    "preflight": _preflight,
    "archive": _archive,
    "r2_upload": _r2,
    "remote_verify": _remote_verify,
    "git_stage": _git_stage,
    "git_push": _git_push,
    "smoke_test": _smoke_test,
}


def publish(config: Dict, journal_path: Optional[Path] = None,
            actions: Optional[Dict[str, Callable[[Dict, Dict], Dict]]] = None) -> Dict:
    """Execute or resume the publication protocol."""
    fingerprint = _release_fingerprint(config)
    journal_path = Path(journal_path or (Path(config["reader_html"]).resolve().parent / "publisher_journal.json"))
    journal = _load_journal(journal_path, fingerprint, config["book_id"])
    if journal.get("status") == "completed":
        return journal
    action_map = {**DEFAULT_ACTIONS, **(actions or {})}
    context = {"journal": journal, "journal_path": journal_path}
    for step in STEPS:
        record = journal["steps"][step]
        if record.get("status") == "completed":
            continue
        record.update({"status": "running", "started_at": _now()})
        atomic_write_json(journal_path, journal)
        try:
            result = action_map[step](config, context) or {}
        except Exception as exc:
            record.update({"status": "failed", "failed_at": _now(), "error": f"{type(exc).__name__}: {exc}"})
            journal["status"] = "failed"
            journal["events"].append({"at": _now(), "step": step, "status": "failed", "error": record["error"]})
            atomic_write_json(journal_path, journal)
            raise
        record.update({"status": "completed", "completed_at": _now(), "result": result})
        record.pop("error", None)
        journal["status"] = "running"
        journal["events"].append({"at": _now(), "step": step, "status": "completed"})
        atomic_write_json(journal_path, journal)
    journal["status"] = "completed"
    journal["completed_at"] = _now()
    atomic_write_json(journal_path, journal)
    return journal


def main() -> int:
    parser = argparse.ArgumentParser(description="Resume-safe all-channel audiobook publisher")
    parser.add_argument("config", type=Path, help="Publisher JSON configuration")
    parser.add_argument("--journal", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    journal = publish(config, args.journal)
    print(f"{journal['status']}: {config['public_reader_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
