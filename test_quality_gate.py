import tempfile
import unittest
from pathlib import Path

from quality_gate import smoke_check_html, check_audio_physical_integrity


class QualityGateSmokeTests(unittest.TestCase):
    def _create_minimal_html(self, body_content: str, css_content: str = "body { margin: 0; }") -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>{css_content}</style>
</head>
<body>
<div id="chapterSelectBtn"></div>
<div id="chapterDropdown"></div>
<div id="drawerToggleBtn"></div>
<div id="controlDrawer"></div>
<audio id="audioTrack" src="audio.mp3"></audio>
{body_content}
<script>
function switchChapter() {{}}
function handleSentenceClick() {{}}
function toggleGlobalPlay() {{}}
function syncPlayback() {{}}
</script>
</body>
</html>
"""

    def test_valid_html_passes_smoke_check(self):
        body = """
<section class="chapter-section active" data-ch="1">
  <div class="sentence-unit" id="c1-s-1" data-start="0.0" data-end="2.0" data-matched="1">
    <div class="sentence-text">
      <span class="w" data-s="0.0" data-e="1.0" data-timing-source="observed">Hello</span>
      <span class="w" data-s="1.0" data-e="2.0" data-timing-source="observed">world</span>
    </div>
  </div>
</section>
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "reader.html"
            path.write_text(self._create_minimal_html(body), encoding="utf-8")
            result = smoke_check_html(path, expected_chapters=1)
            self.assertEqual(result["status"], "passed", result["errors"])

    def test_overlapping_sentences_fail_smoke_check(self):
        # Sentence 1 ends at 5.0, Sentence 2 starts at 4.0
        body = """
<section class="chapter-section active" data-ch="1">
  <div class="sentence-unit" id="c1-s-1" data-start="0.0" data-end="5.0" data-matched="1">
    <div class="sentence-text">
      <span class="w" data-s="0.0" data-e="5.0" data-timing-source="observed">First</span>
    </div>
  </div>
  <div class="sentence-unit" id="c1-s-2" data-start="4.0" data-end="8.0" data-matched="1">
    <div class="sentence-text">
      <span class="w" data-s="4.0" data-e="8.0" data-timing-source="observed">Second</span>
    </div>
  </div>
</section>
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "reader.html"
            path.write_text(self._create_minimal_html(body), encoding="utf-8")
            result = smoke_check_html(path, expected_chapters=1)
            self.assertEqual(result["status"], "failed")
            self.assertTrue(any("sentence overlap" in err for err in result["errors"]))

    def test_duplicate_word_timestamps_fail_smoke_check(self):
        # Two adjacent observed words with identical start timestamps
        body = """
<section class="chapter-section active" data-ch="1">
  <div class="sentence-unit" id="c1-s-1" data-start="0.0" data-end="2.0" data-matched="1">
    <div class="sentence-text">
      <span class="w" data-s="1.0" data-e="1.5" data-timing-source="observed">but</span>
      <span class="w" data-s="1.0" data-e="1.8" data-timing-source="observed">you’ll</span>
    </div>
  </div>
</section>
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "reader.html"
            path.write_text(self._create_minimal_html(body), encoding="utf-8")
            result = smoke_check_html(path, expected_chapters=1)
            self.assertEqual(result["status"], "failed")
            self.assertTrue(any("duplicate word start timestamp" in err for err in result["errors"]))

    def test_check_audio_physical_integrity(self):
        import subprocess
        import numpy as np
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            audio_path = tmp_path / "test.mp3"
            # Generate a 2.0s sine wave audio (440Hz)
            sr = 16000
            t = np.linspace(0, 2.0, int(sr * 2.0), endpoint=False)
            sine = (np.sin(2 * np.pi * 440 * t) * 10000).astype(np.int16)
            cmd = [
                "/opt/homebrew/bin/ffmpeg", "-y", "-f", "s16le", "-ar", "16000", "-ac", "1",
                "-i", "pipe:0", "-b:a", "128k", str(audio_path)
            ]
            subprocess.run(cmd, input=sine.tobytes(), check=True, capture_output=True)

            # Test 1: Duration matches -> passed
            res = check_audio_physical_integrity(audio_path, expected_duration=2.0, max_duration_delta=0.15)
            self.assertEqual(res["status"], "passed", res)

            # Test 2: Duration mismatch -> failed
            res_bad_dur = check_audio_physical_integrity(audio_path, expected_duration=5.0, max_duration_delta=0.15)
            self.assertEqual(res_bad_dur["status"], "failed")
            self.assertIn("deviates from timeline end", res_bad_dur["error"])

            # Test 3: Excessive silence -> failed
            silence_path = tmp_path / "silence.mp3"
            silence = np.zeros(int(sr * 2.0), dtype=np.int16)
            cmd_silence = [
                "/opt/homebrew/bin/ffmpeg", "-y", "-f", "s16le", "-ar", "16000", "-ac", "1",
                "-i", "pipe:0", "-b:a", "128k", str(silence_path)
            ]
            subprocess.run(cmd_silence, input=silence.tobytes(), check=True, capture_output=True)
            res_silent = check_audio_physical_integrity(silence_path, expected_duration=2.0, max_silence_ratio=0.30)
            self.assertEqual(res_silent["status"], "failed")
            self.assertIn("silence ratio", res_silent["error"])


if __name__ == "__main__":
    unittest.main()
