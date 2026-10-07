"""Validated display metadata for logical audiobook tracks.

Artifact chapter numbers identify files and audio tracks. They are deliberately
kept separate from printed chapter numbers so front matter cannot shift the UI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable


SCHEMA_VERSION = 1
ROLES = {"preface", "introduction", "chapter", "afterword", "appendix", "conclusion", "epilogue", "prologue", "other"}


def load_chapter_metadata(path: Path, expected_chapters: Iterable[int] | None = None) -> Dict[int, dict]:
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("chapter metadata must use schema_version 1")
    rows = data.get("chapters")
    if not isinstance(rows, list) or not rows:
        raise ValueError("chapter metadata must contain a non-empty chapters list")

    result: Dict[int, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("chapter metadata contains a malformed entry")
        chapter = row.get("chapter")
        role = row.get("role")
        title = row.get("title")
        display_number = row.get("display_number")
        if not isinstance(chapter, int) or chapter < 0 or chapter in result:
            raise ValueError(f"invalid or duplicate artifact chapter: {chapter}")
        if role not in ROLES:
            raise ValueError(f"unsupported chapter role for track {chapter}: {role}")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"missing title for track {chapter}")
        if role == "chapter" and (not isinstance(display_number, int) or display_number < 1):
            raise ValueError(f"printed chapter track {chapter} requires a positive display_number")
        if role != "chapter" and display_number is not None:
            raise ValueError(f"front/back matter track {chapter} cannot have display_number")
        result[chapter] = {
            "role": role,
            "title": title.strip(),
            "display_number": display_number,
            **({"label": row["label"].strip()} if isinstance(row.get("label"), str) and row["label"].strip() else {}),
        }

    if expected_chapters is not None:
        expected = set(expected_chapters)
        actual = set(result)
        if actual != expected:
            raise ValueError(
                f"chapter metadata tracks differ from artifacts; missing={sorted(expected - actual)}, "
                f"unexpected={sorted(actual - expected)}"
            )
    return result
