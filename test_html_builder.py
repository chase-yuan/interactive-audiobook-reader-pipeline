import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from html_builder import build_master_reader
from validate_outputs import validate_for_release


def _make_release_token(tmp_path: Path):
    (tmp_path / "audio").mkdir(exist_ok=True)
    (tmp_path / "audio" / "chapter_01.mp3").write_bytes(b"fixture")
    canonical = [{"id": "s-1", "text": "A complete sentence."}]
    analysis = [{"id": "s-1", "text": "A complete sentence.", "trans": "一个完整的句子。", "vocab": []}]
    aligned = [{
        **analysis[0], "word_spans": [{"word": "A", "start": 0.0, "end": 0.2}],
        "raw_start": 0.0, "raw_end": 1.0, "has_audio_match": True,
        "fallback_used": False, "alignment_status": "validated",
        "matched_token_count": 3, "source_token_count": 3, "match_ratio": 1.0,
    }]
    for suffix, data in (("canonical_sentences", canonical), ("full_analysis", analysis), ("aligned_sentences", aligned)):
        (tmp_path / f"book_ch01_{suffix}.json").write_text(json.dumps(data), encoding="utf-8")
    report_path = tmp_path / "reader_validation_report.json"
    _, token = validate_for_release(tmp_path, report_path)
    return token, report_path


class HTMLBuilderTests(unittest.TestCase):
    def test_generated_reader_has_valid_javascript_and_bookmark_contract(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            token, report_path = _make_release_token(tmp_path)
            output = tmp_path / "reader.html"
            build_master_reader(
                "Test Book", "A Test", "Test Author", [{
                    "num": 1,
                    "title": "Chapter One",
                    "audio": "./audio/chapter_01.mp3",
                    "aligned_json": str(tmp_path / "book_ch01_aligned_sentences.json"),
                }], str(output), release_token=token, release_report_path=report_path,
            )
            rendered = output.read_text(encoding="utf-8")
            self.assertNotIn('bookmarksToggleBtn', rendered)
            self.assertNotIn('selectionBookmark', rendered)
            self.assertNotIn('bookmarkList', rendered)
            for function_name in (
                "switchChapter", "handleSentenceClick",
                "toggleGlobalPlay", "syncPlayback",
            ):
                self.assertRegex(rendered, rf"function {function_name}\s*\(")
            self.assertIn("window.addEventListener('storage'", rendered)
            self.assertIn("--bg-page: #12151c", rendered)

            scripts = re.findall(r"<script(?:[^>]*)>(.*?)</script>", rendered, re.DOTALL)
            self.assertGreaterEqual(len(scripts), 2)
            js_path = tmp_path / "reader.js"
            js_path.write_text(scripts[-1], encoding="utf-8")
            result = subprocess.run(
                ["node", "--check", str(js_path)],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_front_matter_labels_do_not_shift_printed_chapter_numbers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            token, report_path = _make_release_token(tmp_path)
            aligned = str(tmp_path / "book_ch01_aligned_sentences.json")
            output = tmp_path / "reader.html"
            build_master_reader(
                "Test", "Study", "Author", [{
                    "num": 1,
                    "role": "introduction",
                    "title": "How This Book Began",
                    "audio": "./audio/chapter_01.mp3",
                    "aligned_json": aligned,
                }], str(output), release_token=token, release_report_path=report_path,
            )
            rendered = output.read_text(encoding="utf-8")
            self.assertIn('<span class="chapter-item-tag">Introduction</span>', rendered)
            self.assertIn('INTRODUCTION<br>How This Book Began', rendered)
            self.assertNotIn('Chapter 1</span>', rendered)

    def test_estimated_word_timing_is_rendered_non_playable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            token, report_path = _make_release_token(tmp_path)
            aligned_path = tmp_path / "book_ch01_aligned_sentences.json"
            aligned = json.loads(aligned_path.read_text(encoding="utf-8"))
            aligned[0]["word_spans"] = [{"word": "A", "start": 0, "end": .2, "timing_source": "estimated"}]
            aligned_path.write_text(json.dumps(aligned), encoding="utf-8")
            output = tmp_path / "reader.html"
            build_master_reader("Test", "Study", "Author", [{
                "num": 1, "title": "Chapter One", "audio": "./audio/chapter_01.mp3", "aligned_json": str(aligned_path),
            }], str(output), release_token=token, release_report_path=report_path)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn('data-matched="0"', rendered)
            self.assertIn('data-timing-source="estimated"', rendered)

    def test_internal_track_number_can_differ_from_display_chapter_number(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            token, report_path = _make_release_token(tmp_path)
            output = tmp_path / "reader.html"
            build_master_reader(
                "Test", "Study", "Author", [{
                    "num": 1,
                    "role": "chapter",
                    "display_number": 7,
                    "title": "Unity",
                    "audio": "./audio/chapter_01.mp3",
                    "aligned_json": str(tmp_path / "book_ch01_aligned_sentences.json"),
                }], str(output), release_token=token, release_report_path=report_path,
            )
            rendered = output.read_text(encoding="utf-8")
            self.assertIn('<span class="chapter-item-tag">Chapter 7</span>', rendered)
            self.assertIn('CHAPTER 7<br>Unity', rendered)
            self.assertIn('id="chapter-1"', rendered)

    def test_chapter_selector_is_text_only(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            token, report_path = _make_release_token(tmp_path)
            output = tmp_path / "reader.html"
            build_master_reader(
                "Test Book", "Study", "Author", [{
                    "num": 1,
                    "role": "chapter",
                    "display_number": 1,
                    "title": "Opening",
                    "audio": "./audio/chapter_01.mp3",
                    "aligned_json": str(tmp_path / "book_ch01_aligned_sentences.json"),
                }], str(output), release_token=token, release_report_path=report_path,
            )
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("Test Book · <span id=\"currentChapterLabel\">Ch. 1</span>", rendered)
            self.assertNotIn("📖", rendered)

    def test_zero_jitter_css_invariants(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            output = tmp_path / "reader.html"
            token, report_path = _make_release_token(tmp_path)

            build_master_reader(
                book_title="Test Book",
                book_subtitle="A Test",
                book_author="Test Author",
                chapters_config=[{
                    "num": 1,
                    "title": "Chapter One",
                    "audio": "./audio/chapter_01.mp3",
                    "aligned_json": str(tmp_path / "book_ch01_aligned_sentences.json"),
                }],
                output_html_path=str(output),
                release_token=token,
                release_report_path=report_path,
            )

            rendered = output.read_text(encoding="utf-8")
            rules = re.findall(r"\.w\.active-word\s*\{(?P<body>.*?)\}", rendered, re.DOTALL)
            self.assertEqual(len(rules), 1)

            forbidden_properties = ("font-weight", "font-size", "letter-spacing", "line-height")
            self.assertFalse(any(
                re.search(rf"(?:^|;)\s*{re.escape(prop)}\s*:", rules[0])
                for prop in forbidden_properties
            ))

    def test_namespaced_storage_keys_and_default_book_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            output = tmp_path / "reader.html"
            token, report_path = _make_release_token(tmp_path)

            build_master_reader(
                book_title="The 48 Laws of Power: Special Edition!",
                book_subtitle="A Comprehensive Guide",
                book_author="Robert Greene",
                chapters_config=[{
                    "num": 1,
                    "title": "Chapter One",
                    "audio": "./audio/chapter_01.mp3",
                    "aligned_json": str(tmp_path / "book_ch01_aligned_sentences.json"),
                }],
                output_html_path=str(output),
                release_token=token,
                release_report_path=report_path,
            )

            rendered = output.read_text(encoding="utf-8")
            self.assertIn('window.__BOOK_ID__ = "the_48_laws_of_power_special_edition";', rendered)
            self.assertIn("const STORAGE_PREFIX = 'reader_' + (window.__BOOK_ID__ || 'default') + '_';", rendered)

            expected_namespaced_keys = (
                "STORAGE_PREFIX + 'active_ch'",
                "STORAGE_PREFIX + 'autoscroll'",
                "STORAGE_PREFIX + 'drawer_open'",
                "STORAGE_PREFIX + 'theme'",
                "STORAGE_PREFIX + 'font_size'",
                "STORAGE_PREFIX + 'last_sentence_c'",
            )
            for key in expected_namespaced_keys:
                self.assertIn(key, rendered)

            unnamespaced_keys = (
                "'book_active_ch'",
                "'book_autoscroll'",
                "'book_drawer_open'",
                "'book_theme'",
                "'book_font_size'",
                "'book_last_sentence_c'",
            )
            for key in unnamespaced_keys:
                self.assertNotIn(key, rendered)

    def test_namespaced_storage_keys_with_custom_book_id(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            output = tmp_path / "reader.html"
            token, report_path = _make_release_token(tmp_path)

            build_master_reader(
                book_title="Any Book Title",
                book_subtitle="Subtitle",
                book_author="Author",
                chapters_config=[{
                    "num": 1,
                    "title": "Chapter One",
                    "audio": "./audio/chapter_01.mp3",
                    "aligned_json": str(tmp_path / "book_ch01_aligned_sentences.json"),
                }],
                output_html_path=str(output),
                release_token=token,
                release_report_path=report_path,
                book_id="the-housemaid-p0",
            )

            rendered = output.read_text(encoding="utf-8")
            self.assertIn('window.__BOOK_ID__ = "the-housemaid-p0";', rendered)
            self.assertIn("const STORAGE_PREFIX = 'reader_' + (window.__BOOK_ID__ || 'default') + '_';", rendered)
            self.assertIn("STORAGE_PREFIX + 'active_ch'", rendered)
            self.assertIn("STORAGE_PREFIX + 'autoscroll'", rendered)
            self.assertIn("STORAGE_PREFIX + 'drawer_open'", rendered)
            self.assertIn("STORAGE_PREFIX + 'theme'", rendered)
            self.assertIn("STORAGE_PREFIX + 'font_size'", rendered)
            self.assertIn("STORAGE_PREFIX + 'last_sentence_c'", rendered)

    def test_html_builder_rejects_missing_release_authorization(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            aligned = tmp_path / "aligned.json"
            aligned.write_text("[]", encoding="utf-8")
            with self.assertRaises(Exception) as ctx:
                build_master_reader(
                    "Test", "Test", "Author", [], str(tmp_path / "reader.html"),
                    release_token=None, release_report_path=tmp_path / "missing.json",
                )
            self.assertIn("ReleaseToken", str(ctx.exception))

    def test_p2_reader_uses_binary_sync_and_sleeps_when_paused(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            output = tmp_path / "reader.html"
            token, report_path = _make_release_token(tmp_path)
            build_master_reader(
                "Test", "Study", "Author", [{
                    "num": 1, "title": "One", "audio": "./audio/chapter_01.mp3",
                    "public_audio": "https://cdn.example/book/chapter_01.mp3",
                    "aligned_json": str(tmp_path / "book_ch01_aligned_sentences.json"),
                }], str(output), release_token=token, release_report_path=report_path,
            )
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("function findSentenceAt(time)", rendered)
            self.assertIn("while (low <= high)", rendered)
            self.assertNotIn("for (let u of sentenceUnits)", rendered)
            self.assertIn("cancelAnimationFrame(syncFrameId)", rendered)
            self.assertIn("document.addEventListener('visibilitychange'", rendered)
            self.assertIn("data-public-audio=\"https://cdn.example/book/chapter_01.mp3\"", rendered)

    def test_p2_reader_has_native_preserves_pitch_and_double_tap_shadowing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            output = tmp_path / "reader.html"
            token, report_path = _make_release_token(tmp_path)
            build_master_reader(
                "Test", "Study", "Author", [{
                    "num": 1, "title": "One", "audio": "./audio/chapter_01.mp3",
                    "aligned_json": str(tmp_path / "book_ch01_aligned_sentences.json"),
                }], str(output), release_token=token, release_report_path=report_path,
            )
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("audio.preservesPitch = true", rendered)
            self.assertIn("startSentenceShadowing", rendered)
            self.assertIn("isDoubleTap", rendered)
            for state in ("'idle'", "'playing'", "'pause_buffer'", "'replaying'"):
                self.assertIn(state, rendered)

    def test_chapter_title_deduplication_and_intext_styling(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            output = tmp_path / "reader.html"
            (tmp_path / "audio").mkdir(exist_ok=True)
            (tmp_path / "audio" / "chapter_01.mp3").write_bytes(b"fixture")
            canonical = [
                {"id": "s-1", "text": "—The Dragon Codex Citation"},
                {"id": "s-2", "text": "CHAPTER ONE"},
                {"id": "s-3", "text": "First story sentence."},
            ]
            analysis = [{**item, "trans": "译文", "vocab": []} for item in canonical]
            aligned = [
                {**analysis[0], "word_spans": [], "raw_start": None, "raw_end": None, "has_audio_match": False, "alignment_status": "not-applicable", "alignment_reason": "non_narrated_content", "fallback_used": False, "matched_token_count": 0, "source_token_count": 4, "match_ratio": 0},
                {**analysis[1], "word_spans": [], "raw_start": None, "raw_end": None, "has_audio_match": False, "alignment_status": "not-applicable", "alignment_reason": "non_narrated_content", "fallback_used": False, "matched_token_count": 0, "source_token_count": 2, "match_ratio": 0},
                {**analysis[2], "word_spans": [{"word": "First", "start": 0, "end": 1}], "raw_start": 0, "raw_end": 1, "has_audio_match": True, "alignment_status": "validated", "fallback_used": False, "matched_token_count": 3, "source_token_count": 3, "match_ratio": 1},
            ]
            for suffix, data in (("canonical_sentences", canonical), ("full_analysis", analysis), ("aligned_sentences", aligned)):
                (tmp_path / f"book_ch01_{suffix}.json").write_text(json.dumps(data), encoding="utf-8")
            report_path = tmp_path / "reader_validation_report.json"
            _, token = validate_for_release(tmp_path, report_path)

            build_master_reader(
                book_title="Fourth Wing",
                book_subtitle="Bilingual Reader",
                book_author="Rebecca Yarros",
                chapters_config=[{
                    "num": 1,
                    "title": "Chapter 1",
                    "audio": "./audio/chapter_01.mp3",
                    "aligned_json": str(tmp_path / "book_ch01_aligned_sentences.json"),
                }],
                output_html_path=str(output),
                release_token=token,
                release_report_path=report_path,
                book_id="fourth-wing",
            )
            rendered = output.read_text(encoding="utf-8")
            self.assertIn('<h1 class="book-title">CHAPTER 1</h1>', rendered)
            self.assertNotIn('CHAPTER 1<br>Chapter 1', rendered)
            self.assertIn('class="sentence-text epigraph-citation"', rendered)
            self.assertIn('class="sentence-text chapter-intext-heading"', rendered)

    def test_chinese_lock_mode_and_arrow_keys_navigation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            token, report_path = _make_release_token(tmp_path)
            output = tmp_path / "reader.html"
            build_master_reader(
                "Focus Reading", "Pure Audio", "Language Coach", [{
                    "num": 1, "title": "Focus Track", "audio": "./audio/chapter_01.mp3",
                    "aligned_json": str(tmp_path / "book_ch01_aligned_sentences.json"),
                }], str(output), release_token=token, release_report_path=report_path,
            )
            rendered = output.read_text(encoding="utf-8")
            self.assertIn('id="chineseLockBtn"', rendered)
            self.assertIn("function toggleChineseLock()", rendered)
            self.assertIn("[data-hide-chinese=\"true\"] .inspect-panel", rendered)
            self.assertIn(".sentence-unit.active:not(.card-collapsed) .inspect-panel", rendered)
            self.assertIn("targetUnit.classList.add('active', 'card-collapsed')", rendered)
            self.assertIn("STORAGE_PREFIX + 'hide_chinese'", rendered)

    def test_shortcuts_t_and_r_registered_and_documented(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            tmp_path = Path(temp_dir)
            token, report_path = _make_release_token(tmp_path)
            output = tmp_path / "reader.html"
            build_master_reader(
                "Shortcut Test", "Audiobook", "Author", [{
                    "num": 1, "title": "Chapter 1", "audio": "./audio/chapter_01.mp3",
                    "aligned_json": str(tmp_path / "book_ch01_aligned_sentences.json"),
                }], str(output), release_token=token, release_report_path=report_path,
            )
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("e.key === 't'", rendered)
            self.assertIn("e.key === 'r'", rendered)
            self.assertIn("toggleChineseLock()", rendered)
            self.assertIn("toggleShadowing()", rendered)
            self.assertIn("e.metaKey || e.ctrlKey || e.altKey", rendered)
            self.assertIn('<span class="kbd-key">T</span><span>Toggle Bilingual / English-only mode</span>', rendered)
            self.assertIn('<span class="kbd-key">R</span><span>Repeat sentence loop</span>', rendered)
            self.assertIn('快捷键 T', rendered)
            self.assertIn('快捷键 R', rendered)


