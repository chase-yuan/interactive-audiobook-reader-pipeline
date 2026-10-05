import tempfile
import unittest
from pathlib import Path

from quality_gate import smoke_check_html


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


if __name__ == "__main__":
    unittest.main()
