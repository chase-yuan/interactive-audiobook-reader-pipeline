"""Design Tokens and Aesthetic Architecture Test Suite.

Enforces Li Xiaolai's '100% Tokenized & Well-Organized' CSS and aesthetic principles:
1. Complete design token declaration in :root and theme blocks.
2. Parity across all 4 visual themes: Sepia (parchment), Light (studio clean), Dark (slate), Night (OLED pure black).
3. Zero hardcoded magic numbers (raw hex/rgb colors, raw px spacing) in component CSS rules.
4. Zero layout jitter invariants on synchronized audio active-word highlights.
"""

import json
import re
import tempfile
import unittest
from pathlib import Path

from html_builder import build_master_reader
from validate_outputs import validate_for_release


def _generate_test_reader_html() -> str:
    with tempfile.TemporaryDirectory() as temp_dir:
        tmp_path = Path(temp_dir)
        (tmp_path / "audio").mkdir(exist_ok=True)
        (tmp_path / "audio" / "chapter_01.mp3").write_bytes(b"fixture")
        canonical = [{"id": "s-1", "text": "This is a design token test sentence."}]
        analysis = [{"id": "s-1", "text": "This is a design token test sentence.", "trans": "这是设计令牌测试句。", "vocab": []}]
        aligned = [{
            **analysis[0],
            "word_spans": [{"word": "This", "start": 0.0, "end": 0.3}],
            "raw_start": 0.0,
            "raw_end": 1.0,
            "has_audio_match": True,
            "fallback_used": False,
            "alignment_status": "validated",
            "matched_token_count": 7,
            "source_token_count": 7,
            "match_ratio": 1.0,
        }]
        for suffix, data in (("canonical_sentences", canonical), ("full_analysis", analysis), ("aligned_sentences", aligned)):
            (tmp_path / f"book_ch01_{suffix}.json").write_text(json.dumps(data), encoding="utf-8")
        report_path = tmp_path / "reader_validation_report.json"
        _, token = validate_for_release(tmp_path, report_path)
        output = tmp_path / "reader.html"
        build_master_reader(
            "Aesthetic Token Specimen",
            "100% Tokenized Design System",
            "Lindy & DeepMind Pair",
            [{
                "num": 1,
                "title": "Design System Chapter",
                "audio": "./audio/chapter_01.mp3",
                "aligned_json": str(tmp_path / "book_ch01_aligned_sentences.json"),
            }],
            str(output),
            release_token=token,
            release_report_path=report_path,
        )
        return output.read_text(encoding="utf-8")


class DesignTokensAestheticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = _generate_test_reader_html()
        match = re.search(r"<style>(.*?)</style>", cls.html, re.DOTALL)
        cls.assertIsNotNone(match, "Reader HTML must contain a <style> block")
        cls.css = match.group(1)

    def test_root_defines_complete_scale_of_design_tokens(self):
        root_match = re.search(r":root\s*\{(?P<body>.*?)\}", self.css, re.DOTALL)
        self.assertIsNotNone(root_match, ":root block must exist")
        root_body = root_match.group("body")

        expected_tokens = [
            "--font-serif",
            "--font-sans",
            "--font-size-base",
            "--font-size-ui",
            "--font-size-sm",
            "--font-size-xs",
            "--font-size-h1",
            "--font-size-h2",
            "--line-height-base",
            "--space-xs",
            "--space-sm",
            "--space-md",
            "--space-lg",
            "--space-xl",
            "--space-2xl",
            "--max-content-width",
            "--dropdown-width",
            "--radius-base",
            "--radius-pill",
            "--shadow-subtle",
            "--shadow-nav",
            "--transition-base",
            "--transition-drawer",
        ]
        for token in expected_tokens:
            self.assertIn(token, root_body, f"Missing design token in :root: {token}")

    def test_all_four_themes_maintain_strict_token_parity(self):
        required_theme_tokens = [
            "--bg-page",
            "--bg-page-glass",
            "--bg-panel",
            "--bg-panel-glass",
            "--bg-hover",
            "--text-main",
            "--text-sub",
            "--accent",
            "--accent-light",
            "--word-highlight-bg",
            "--word-highlight-text",
            "--border",
            "--border-subtle",
            "--card-shadow",
            "--audio-filter",
        ]
        for theme_name in ("sepia", "light", "dark", "night"):
            theme_match = re.search(rf'\[data-theme="{theme_name}"\]\s*\{{(?P<body>.*?)\}}', self.css, re.DOTALL)
            self.assertIsNotNone(theme_match, f'Theme block [data-theme="{theme_name}"] missing in CSS')
            theme_body = theme_match.group("body")
            for token in required_theme_tokens:
                self.assertIn(token, theme_body, f'Theme "{theme_name}" is missing token {token}')

    def test_night_theme_uses_true_oled_black(self):
        night_match = re.search(r'\[data-theme="night"\]\s*\{(?P<body>.*?)\}', self.css, re.DOTALL)
        self.assertIsNotNone(night_match)
        night_body = night_match.group("body")
        self.assertIn("--bg-page: #000000", night_body, "Night theme must utilize true OLED #000000 for maximum black contrast")

    def test_component_rules_do_not_contain_hardcoded_hex_colors(self):
        """No raw hexadecimal color literals in component rules (outside token definition blocks)."""
        # Strip comments
        cleaned = re.sub(r"/\*.*?\*/", "", self.css, flags=re.DOTALL)
        # Strip :root and [data-theme=...] blocks where tokens are defined
        non_token_css = re.sub(r":root\s*\{.*?\}", "", cleaned, flags=re.DOTALL)
        non_token_css = re.sub(r'\[data-theme=".*?"\]\s*\{.*?\}', "", non_token_css, flags=re.DOTALL)

        # Search for raw hex color declarations like '#abc' or '#abcdef'
        raw_hex_matches = re.findall(r"(:\s*#[0-9a-fA-F]{3,8}\b)", non_token_css)
        self.assertEqual(
            raw_hex_matches, [],
            f"Component rules must be 100% tokenized; found hardcoded hex color literals: {raw_hex_matches}"
        )

    def test_component_rules_do_not_contain_hardcoded_rgba_colors(self):
        """No raw rgb/rgba literals in component rules (outside token definition blocks)."""
        cleaned = re.sub(r"/\*.*?\*/", "", self.css, flags=re.DOTALL)
        non_token_css = re.sub(r":root\s*\{.*?\}", "", cleaned, flags=re.DOTALL)
        non_token_css = re.sub(r'\[data-theme=".*?"\]\s*\{.*?\}', "", non_token_css, flags=re.DOTALL)

        raw_rgba_matches = re.findall(r"(:\s*rgba?\([^)]+\))", non_token_css)
        self.assertEqual(
            raw_rgba_matches, [],
            f"Component rules must be 100% tokenized; found hardcoded rgb/rgba literals: {raw_rgba_matches}"
        )

    def test_zero_layout_jitter_on_active_words(self):
        active_match = re.search(r"\.w\.active-word\s*\{(?P<body>.*?)\}", self.css, re.DOTALL)
        self.assertIsNotNone(active_match, ".w.active-word rule missing")
        active_body = active_match.group("body")
        for forbidden in ("font-size", "font-weight", "letter-spacing", "line-height", "padding", "margin"):
            self.assertNotIn(
                f"{forbidden}:", active_body,
                f".w.active-word violates zero-jitter invariant with property: {forbidden}"
            )

    def test_theme_switch_script_supports_all_four_themes(self):
        self.assertIn("const themes = ['sepia', 'light', 'dark', 'night'];", self.html)
        self.assertIn("t === 'night'", self.html)


if __name__ == "__main__":
    unittest.main()
