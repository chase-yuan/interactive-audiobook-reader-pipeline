"""Deterministic, human-approved EPUB/audio intake reconciliation.

The reconciler deliberately separates inexpensive evidence collection from costly
workers.  Acoustic backends write head/tail probe text; this module combines that
evidence with EPUB structure and duration proportions, then emits a hash-bound
``intake_plan.json``.  No worker should trust the plan until :func:`verify_gate`
succeeds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
import zipfile
from dataclasses import dataclass
from difflib import SequenceMatcher
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from xml.etree import ElementTree as ET

from artifact_io import atomic_write_json


SCHEMA_VERSION = 1
DEFAULT_THRESHOLD = 0.90


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _norm(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9']+", (text or "").casefold()))


def _anchor(text: str, *, tail: bool = False, words: int = 45) -> str:
    tokens = _norm(text).split()
    selected = tokens[-words:] if tail else tokens[:words]
    return " ".join(selected)


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []
        self._ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag.casefold() in {"script", "style", "svg"}:
            self._ignored += 1

    def handle_endtag(self, tag):
        if tag.casefold() in {"script", "style", "svg"} and self._ignored:
            self._ignored -= 1

    def handle_data(self, data):
        if not self._ignored and data.strip():
            self.parts.append(data.strip())

    @property
    def text(self) -> str:
        return " ".join(self.parts)


def _xml_text(element: ET.Element) -> str:
    return " ".join(part.strip() for part in element.itertext() if part.strip())


def _toc_titles(zf: zipfile.ZipFile, opf_dir: PurePosixPath, manifest: Dict[str, Dict]) -> Dict[str, str]:
    result: Dict[str, str] = {}
    nav_item = next((item for item in manifest.values() if "nav" in item.get("properties", "").split()), None)
    if nav_item:
        root = ET.fromstring(zf.read(str(opf_dir / nav_item["href"])))
        for element in root.iter():
            if _local(element.tag) != "a" or not element.get("href"):
                continue
            href = element.get("href", "").split("#", 1)[0]
            result[str(PurePosixPath(nav_item["href"]).parent / href)] = _xml_text(element)
    ncx_item = next((item for item in manifest.values() if item.get("media_type") == "application/x-dtbncx+xml"), None)
    if ncx_item:
        root = ET.fromstring(zf.read(str(opf_dir / ncx_item["href"])))
        for nav_point in (el for el in root.iter() if _local(el.tag) == "navPoint"):
            content = next((el for el in nav_point.iter() if _local(el.tag) == "content"), None)
            label = next((el for el in nav_point.iter() if _local(el.tag) == "text"), None)
            if content is not None and content.get("src") and label is not None:
                href = content.get("src", "").split("#", 1)[0]
                result.setdefault(str(PurePosixPath(ncx_item["href"]).parent / href), _xml_text(label))
    return {str(PurePosixPath(key)): value for key, value in result.items()}


def parse_epub(epub_path: Path, cover_output: Optional[Path] = None) -> Dict:
    """Return ordered, non-empty EPUB spine documents and optionally extract its cover."""
    epub_path = Path(epub_path).resolve()
    with zipfile.ZipFile(epub_path) as zf:
        container = ET.fromstring(zf.read("META-INF/container.xml"))
        rootfile = next((el for el in container.iter() if _local(el.tag) == "rootfile"), None)
        if rootfile is None or not rootfile.get("full-path"):
            raise ValueError("EPUB container has no package rootfile")
        opf_path = PurePosixPath(rootfile.get("full-path"))
        opf_dir = opf_path.parent
        package = ET.fromstring(zf.read(str(opf_path)))
        manifest: Dict[str, Dict] = {}
        spine_ids: List[str] = []
        cover_id = None
        metadata = {}
        for element in package.iter():
            name = _local(element.tag)
            if name == "item" and element.get("id") and element.get("href"):
                manifest[element.get("id")] = {
                    "href": element.get("href"),
                    "media_type": element.get("media-type", ""),
                    "properties": element.get("properties", ""),
                }
            elif name == "itemref" and element.get("idref"):
                spine_ids.append(element.get("idref"))
            elif name == "meta" and element.get("name") == "cover":
                cover_id = element.get("content")
            elif name in {"title", "creator", "language"} and name not in metadata:
                metadata[name] = _xml_text(element)
        titles = _toc_titles(zf, opf_dir, manifest)
        chapters = []
        for item_id in spine_ids:
            item = manifest.get(item_id)
            if not item or item["media_type"] not in {"application/xhtml+xml", "text/html"}:
                continue
            member = str(opf_dir / item["href"])
            extractor = _TextExtractor()
            extractor.feed(zf.read(member).decode("utf-8", errors="replace"))
            text = " ".join(extractor.text.split())
            if not _norm(text):
                continue
            relative_href = str(PurePosixPath(item["href"]))
            title = titles.get(relative_href) or titles.get(str(PurePosixPath(member).relative_to(opf_dir)))
            chapters.append({
                "index": len(chapters),
                "id": item_id,
                "title": title or f"Chapter {len(chapters) + 1}",
                "href": member,
                "text": text,
                "head_anchor": _anchor(text),
                "tail_anchor": _anchor(text, tail=True),
                "text_chars": len(_norm(text)),
            })
        cover_item = manifest.get(cover_id or "") or next(
            (item for item in manifest.values() if "cover-image" in item.get("properties", "").split()), None
        )
        cover = None
        if cover_item:
            cover = str(opf_dir / cover_item["href"])
            if cover_output:
                Path(cover_output).parent.mkdir(parents=True, exist_ok=True)
                Path(cover_output).write_bytes(zf.read(cover))
    if not chapters:
        raise ValueError("EPUB spine contains no textual chapters")
    return {"metadata": metadata, "chapters": chapters, "cover_member": cover}


def ffprobe_duration(path: Path) -> float:
    completed = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        check=True, capture_output=True, text=True, timeout=60,
    )
    return float(completed.stdout.strip())


def discover_audio(audio_dir: Path, duration_probe: Callable[[Path], float] = ffprobe_duration) -> List[Dict]:
    candidates = sorted(
        (path for path in Path(audio_dir).resolve().iterdir() if path.suffix.casefold() in {".mp3", ".m4b", ".m4a"}),
        key=lambda path: [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", path.name)],
    )
    return [{
        "index": index,
        "path": str(path),
        "name": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "duration": float(duration_probe(path)),
    } for index, path in enumerate(candidates)]


def _similarity(chapters: Sequence[Dict], audios: Sequence[Dict], probes: Dict[str, Dict],
                total_text_chars: int, total_audio_duration: float) -> Tuple[float, Dict]:
    # For grouped mappings the discriminating anchors are the outer boundaries:
    # first chapter/track head and last chapter/track tail.
    chapter_head = chapters[0]["head_anchor"]
    chapter_tail = chapters[-1]["tail_anchor"]
    audio_head = _norm(probes.get(audios[0]["name"], {}).get("head", ""))
    audio_tail = _norm(probes.get(audios[-1]["name"], {}).get("tail", ""))
    head_score = SequenceMatcher(None, chapter_head, audio_head).ratio() if audio_head else 0.0
    tail_score = SequenceMatcher(None, chapter_tail, audio_tail).ratio() if audio_tail else 0.0
    anchor_score = max(head_score, tail_score) if not (audio_head and audio_tail) else (head_score + tail_score) / 2
    chapter_weight = sum(max(1, ch["text_chars"]) for ch in chapters)
    audio_weight = sum(max(0.01, audio["duration"]) for audio in audios)
    count_ratio = min(len(chapters), len(audios)) / max(len(chapters), len(audios))
    text_share = chapter_weight / max(1, total_text_chars)
    duration_share = audio_weight / max(0.01, total_audio_duration)
    duration_score = min(text_share, duration_share) / max(text_share, duration_share)
    evidence_score = 0.75 * anchor_score + 0.15 * duration_score + 0.10 * count_ratio
    return round(evidence_score, 6), {
        "head_similarity": round(head_score, 6),
        "tail_similarity": round(tail_score, 6),
        "chapter_text_chars": chapter_weight,
        "audio_duration": round(audio_weight, 3),
        "duration_similarity": round(duration_score, 6),
    }


def reconcile(chapters: Sequence[Dict], audios: Sequence[Dict], probes: Dict[str, Dict], max_group: int = 3) -> List[Dict]:
    """Globally reconcile ordered sequences, allowing skips and M:1 / 1:N groups."""
    n, m = len(chapters), len(audios)
    total_text_chars = sum(max(1, chapter["text_chars"]) for chapter in chapters)
    total_audio_duration = sum(max(0.01, audio["duration"]) for audio in audios)
    dp: Dict[Tuple[int, int], Tuple[float, List[Dict]]] = {(0, 0): (0.0, [])}
    for i in range(n + 1):
        for j in range(m + 1):
            if (i, j) not in dp:
                continue
            score, rows = dp[(i, j)]
            if i < n:
                # EPUB spines routinely contain cover, contents, bibliography,
                # notes, index, and publisher pages that have no narration.
                # Keep the skip visible in the approval plan instead of forcing
                # a false match or hiding it in parser heuristics.
                candidate = (
                    score - 0.10,
                    rows + [{"kind": "skip_chapter", "chapter_indices": [i], "confidence": 1.0}],
                )
                if candidate[0] > dp.get((i + 1, j), (-10**9, []))[0]:
                    dp[(i + 1, j)] = candidate
            if j < m:
                # Commercial extras are common.  Skipping one track should beat
                # diluting a near-exact chapter match by grouping in unrelated
                # intro/outro material, while still carrying a small penalty.
                candidate = (score - 0.10, rows + [{"kind": "skip_audio", "audio_indices": [j], "confidence": 1.0}])
                if candidate[0] > dp.get((i, j + 1), (-10**9, []))[0]:
                    dp[(i, j + 1)] = candidate
            for chapter_count in range(1, min(max_group, n - i) + 1):
                for audio_count in range(1, min(max_group, m - j) + 1):
                    confidence, evidence = _similarity(
                        chapters[i:i + chapter_count], audios[j:j + audio_count], probes,
                        total_text_chars, total_audio_duration,
                    )
                    grouping_penalty = 0.04 * (chapter_count + audio_count - 2)
                    candidate_score = score + confidence - grouping_penalty
                    row = {
                        "kind": "match",
                        "chapter_indices": list(range(i, i + chapter_count)),
                        "audio_indices": list(range(j, j + audio_count)),
                        "confidence": confidence,
                        "evidence": evidence,
                    }
                    target = (i + chapter_count, j + audio_count)
                    if candidate_score > dp.get(target, (-10**9, []))[0]:
                        dp[target] = (candidate_score, rows + [row])
    if (n, m) not in dp:
        raise RuntimeError("Unable to reconcile every EPUB chapter")
    return dp[(n, m)][1]


def _plan_payload(plan: Dict) -> Dict:
    return {key: value for key, value in plan.items() if key not in {"plan_sha256", "approval"}}


def plan_digest(plan: Dict) -> str:
    encoded = json.dumps(_plan_payload(plan), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_plan(epub_path: Path, audio_dir: Path, probes: Dict[str, Dict], *,
               duration_probe: Callable[[Path], float] = ffprobe_duration,
               threshold: float = DEFAULT_THRESHOLD) -> Dict:
    epub = parse_epub(epub_path)
    audios = discover_audio(audio_dir, duration_probe)
    mappings = reconcile(epub["chapters"], audios, probes)
    for row in mappings:
        row["chapters"] = [epub["chapters"][index]["title"] for index in row.get("chapter_indices", [])]
        row["audio_files"] = [audios[index]["name"] for index in row.get("audio_indices", [])]
    matched = [row for row in mappings if row["kind"] == "match"]
    minimum = min((row["confidence"] for row in matched), default=0.0)
    plan = {
        "schema_version": SCHEMA_VERSION,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "threshold": threshold,
        "minimum_confidence": minimum,
        "gate_status": "awaiting_approval" if minimum >= threshold else "blocked_low_confidence",
        "epub": {"path": str(Path(epub_path).resolve()), "sha256": sha256(Path(epub_path))},
        "audio": audios,
        "chapters": [{key: value for key, value in chapter.items() if key != "text"} for chapter in epub["chapters"]],
        "mappings": mappings,
        "acoustic_probes_sha256": hashlib.sha256(
            json.dumps(probes, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
        "approval": None,
    }
    plan["plan_sha256"] = plan_digest(plan)
    return plan


def approve_plan(path: Path, approver: str = "human") -> Dict:
    path = Path(path)
    plan = json.loads(path.read_text(encoding="utf-8"))
    expected = plan_digest(plan)
    if plan.get("plan_sha256") != expected:
        raise RuntimeError("intake plan content changed since it was generated")
    if plan.get("minimum_confidence", 0.0) < plan.get("threshold", DEFAULT_THRESHOLD):
        raise RuntimeError("intake plan cannot be approved below its confidence threshold")
    plan["approval"] = {
        "approved": True,
        "approver": approver,
        "approved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "approved_plan_sha256": expected,
    }
    plan["gate_status"] = "approved"
    # gate_status is part of the approved contract, so recalculate after transition.
    plan["plan_sha256"] = plan_digest(plan)
    plan["approval"]["approved_plan_sha256"] = plan["plan_sha256"]
    atomic_write_json(path, plan)
    return plan


def verify_gate(path: Path) -> Dict:
    plan = json.loads(Path(path).read_text(encoding="utf-8"))
    digest = plan_digest(plan)
    approval = plan.get("approval") or {}
    if plan.get("plan_sha256") != digest or approval.get("approved_plan_sha256") != digest or not approval.get("approved"):
        raise RuntimeError("intake plan is not approved for its current content")
    if plan.get("minimum_confidence", 0.0) < plan.get("threshold", DEFAULT_THRESHOLD):
        raise RuntimeError("intake plan confidence is below the worker gate threshold")
    inputs = [plan.get("epub", {})] + list(plan.get("audio", []))
    for record in inputs:
        source = Path(record.get("path", ""))
        if not source.is_file() or sha256(source) != record.get("sha256"):
            raise RuntimeError(f"intake input missing or changed: {source}")
    return plan


def extract_book_metadata(target: Path | str) -> Dict[str, str]:
    """Extract authoritative title, subtitle, and author from an EPUB file or book directory."""
    target_path = Path(target).resolve()
    book_title = ""
    book_subtitle = ""
    book_author = ""

    # Case 1: Direct EPUB file
    if target_path.is_file() and target_path.suffix.lower() == ".epub":
        try:
            parsed = parse_epub(target_path)
            meta = parsed.get("metadata", {})
            raw_title = (meta.get("title") or "").strip()
            raw_creator = (meta.get("creator") or "").strip()
            if ":" in raw_title:
                parts = raw_title.split(":", 1)
                book_title = parts[0].strip()
                book_subtitle = parts[1].strip()
            else:
                book_title = raw_title
            book_author = raw_creator
        except Exception:
            pass

    # Case 2: Book directory
    elif target_path.is_dir():
        # Look in ebook/ directory first, then root of book dir
        ebook_dir = target_path / "ebook"
        candidates = []
        if ebook_dir.is_dir():
            candidates.extend(sorted(ebook_dir.glob("*.epub")))
        candidates.extend(sorted(target_path.glob("*.epub")))

        for epub_path in candidates:
            try:
                parsed = parse_epub(epub_path)
                meta = parsed.get("metadata", {})
                raw_title = (meta.get("title") or "").strip()
                raw_creator = (meta.get("creator") or "").strip()
                if raw_title and not book_title:
                    if ":" in raw_title:
                        parts = raw_title.split(":", 1)
                        book_title = parts[0].strip()
                        book_subtitle = parts[1].strip()
                    else:
                        book_title = raw_title
                if raw_creator and not book_author:
                    book_author = raw_creator
                if book_title and book_author:
                    break
            except Exception:
                continue

    # Fallback to filename or directory name pattern "Author - Title" or "Title - Author"
    folder_name = target_path.name if target_path.is_dir() else target_path.stem
    if " - " in folder_name and (not book_title or not book_author):
        parts = folder_name.split(" - ")
        if not book_title:
            book_title = parts[0].strip()
        if not book_author and len(parts) > 1:
            book_author = parts[1].strip()

    if not book_title:
        book_title = folder_name.replace("_", " ").strip()
    if not book_author:
        book_author = "Author"
    if not book_subtitle:
        book_subtitle = "Bilingual Synchronized Reader"

    return {
        "title": book_title,
        "subtitle": book_subtitle,
        "author": book_author,
    }


def _print_table(plan: Dict) -> None:
    print("KIND       CHAPTERS                         AUDIO                            CONFIDENCE")
    for row in plan["mappings"]:
        chapters = ", ".join(row.get("chapters", [])) or "-"
        audio = ", ".join(row.get("audio_files", [])) or "-"
        print(f"{row['kind']:<10} {chapters[:32]:<32} {audio[:32]:<32} {row['confidence']:.1%}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build and approve a hash-bound EPUB/audio intake plan")
    parser.add_argument("--epub", type=Path)
    parser.add_argument("--audio-dir", type=Path)
    parser.add_argument("--probes", type=Path, help="JSON mapping audio filename to head/tail transcript text")
    parser.add_argument("--output", type=Path, default=Path("intake_plan.json"))
    parser.add_argument("--approve", type=Path, help="Approve an existing plan after human review")
    parser.add_argument("--verify", type=Path, help="Verify approval and all bound inputs")
    args = parser.parse_args()
    if args.approve:
        approve_plan(args.approve)
        print(f"approved: {args.approve}")
        return 0
    if args.verify:
        verify_gate(args.verify)
        print(f"gate passed: {args.verify}")
        return 0
    if not args.epub or not args.audio_dir or not args.probes:
        parser.error("--epub, --audio-dir, and --probes are required to build a plan")
    probes = json.loads(args.probes.read_text(encoding="utf-8"))
    plan = build_plan(args.epub, args.audio_dir, probes)
    atomic_write_json(args.output, plan)
    _print_table(plan)
    print(f"plan: {args.output} ({plan['gate_status']})")
    return 0 if plan["minimum_confidence"] >= plan["threshold"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
