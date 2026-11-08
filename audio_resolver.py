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

    # Tier 1.5: Explicit leading track index (e.g. '001 - Title.mp3', '01_Track.m4a', '01.mp3')
    pattern_leading = re.compile(
        rf"^0*{chapter_number}(?:[-_ .]|$)",
        re.IGNORECASE,
    )
    tier_leading = {
        path.resolve()
        for ext in AUDIO_EXTENSIONS
        for path in audio_dir.glob(f"*{ext}")
        if pattern_leading.search(path.name)
    }
    if tier_leading:
        return AudioResolution(tuple(sorted(tier_leading)))

    # Tier 2: Standard commercial tracks with token delimiters (e.g. ' - 001.mp3', '_01.m4b')
    # Guard against false positives like 'Book 1.mp3', 'Part 1.mp3' when checking for chapter 1
    pattern2 = re.compile(
        rf"(?:[-_ ]|^)0*{chapter_number}(?!\d)",
        re.IGNORECASE,
    )
    ignored_prefix_tokens = ("book", "part", "vol", "volume", "cd", "disc", "edition", "act", "scene", "unit")
    tier2 = set()
    for ext in AUDIO_EXTENSIONS:
        for path in audio_dir.glob(f"*{ext}"):
            for m in pattern2.finditer(path.name):
                prefix = path.name[:m.start()].lower().rstrip()
                if any(prefix.endswith(w) for w in ignored_prefix_tokens):
                    continue
                tier2.add(path.resolve())
                break
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
        candidate = all_audio[chapter_number - 1]
        # Guard: if the candidate explicitly declares a different chapter number, do not false-match
        explicit_nums = re.findall(r"(?:chapter|ch)[ _-]*(\d+)", candidate.name, re.IGNORECASE)
        if explicit_nums and any(int(n) != chapter_number for n in explicit_nums):
            return AudioResolution(())
        return AudioResolution((candidate,))

    return AudioResolution(())
