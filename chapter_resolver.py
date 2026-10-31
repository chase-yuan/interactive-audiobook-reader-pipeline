"""Book-directory discovery and chapter input resolution."""

from dataclasses import dataclass
from pathlib import Path
import re
from typing import List, Optional


CANONICAL_SUFFIX = "_canonical_sentences.json"
CHAPTER_PATTERN = re.compile(r"(?:^|_)ch(\d+)(?:_|$)", re.IGNORECASE)


@dataclass(frozen=True)
class ChapterArtifact:
    chapter_number: int
    prefix: str
    canonical_path: Path
    analysis_path: Path
    acoustic_path: Path


def discover_chapters(book_dir) -> List[ChapterArtifact]:
    """Discover canonical chapter artifacts without making book-specific guesses."""
    book_dir = Path(book_dir).expanduser().resolve()
    artifacts = []
    for canonical_path in sorted(book_dir.glob(f"*{CANONICAL_SUFFIX}")):
        prefix = canonical_path.name[: -len(CANONICAL_SUFFIX)]
        match = CHAPTER_PATTERN.search(prefix)
        if not match:
            continue
        chapter_number = int(match.group(1))
        acoustic_candidate = book_dir / "audio" / f"{prefix}_acoustic_words.json"
        if not acoustic_candidate.exists():
            generic_candidate = book_dir / "audio" / f"chapter_{chapter_number:02d}_acoustic_words.json"
            if generic_candidate.exists():
                acoustic_candidate = generic_candidate
        artifacts.append(
            ChapterArtifact(
                chapter_number=chapter_number,
                prefix=prefix,
                canonical_path=canonical_path,
                analysis_path=book_dir / f"{prefix}_full_analysis.json",
                acoustic_path=acoustic_candidate,
            )
        )
    return artifacts
