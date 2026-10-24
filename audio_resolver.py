"""Single source of truth for chapter-audio discovery."""

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class AudioResolution:
    candidates: tuple[Path, ...]

    @property
    def status(self):
        if not self.candidates:
            return "missing"
        if len(self.candidates) > 1:
            return "ambiguous"
        return "ok"

    @property
    def path(self):
        return self.candidates[0] if self.status == "ok" else None


AUDIO_EXTENSIONS = (".mp3", ".m4a", ".m4b", ".aac", ".flac", ".opus")


def _natural_keys(text):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(text))]


def resolve_chapter_audio(audio_dir, chapter_number):
    """Resolve zero, one, or multiple explicit chapter-number filenames across commercial conventions."""
    audio_dir = Path(audio_dir)
    if not audio_dir.is_dir():
        return AudioResolution(())

    # Tier 1: Explicit chapter/ch prefix (e.g. chapter_01.mp3, ch01.m4a)
    pattern1 = re.compile(
        rf"(?<!\d)(?:chapter|ch)[ _-]*0*{chapter_number}(?!\d)",
        re.IGNORECASE,
    )
    tier1 = {
        path.resolve()
        for ext in AUDIO_EXTENSIONS
        for path in audio_dir.glob(f"*{ext}")
        if pattern1.search(path.name)
    }
    if tier1:
        return AudioResolution(tuple(sorted(tier1)))

    # Tier 2: Standard commercial tracks with token delimiters (e.g. ' - 001.mp3', '_01.m4b', '001.mp3')
    pattern2 = re.compile(
        rf"(?:[-_ ]|^)0*{chapter_number}(?!\d)",
        re.IGNORECASE,
    )
    tier2 = {
        path.resolve()
        for ext in AUDIO_EXTENSIONS
        for path in audio_dir.glob(f"*{ext}")
        if pattern2.search(path.name)
    }
    if tier2:
        return AudioResolution(tuple(sorted(tier2)))

    # Tier 3: Deterministic 1-indexed natural sort cohort
    all_audio = sorted(
        [
            path.resolve()
            for ext in AUDIO_EXTENSIONS
            for path in audio_dir.glob(f"*{ext}")
        ],
        key=lambda p: _natural_keys(p.name),
    )
    if 1 <= chapter_number <= len(all_audio):
        return AudioResolution((all_audio[chapter_number - 1],))

    return AudioResolution(())
