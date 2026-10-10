import json
import tempfile
import unittest
from pathlib import Path

from kokoro_synthesizer import compute_word_spans, synthesize_chapter
from quality_gate import check_audio_physical_integrity
from validate_outputs import validate


class KokoroSynthesizerTests(unittest.TestCase):
    def test_compute_word_spans_monotonic_and_complete(self):
        text = "Critical thinking is an essential skill."
        spans = compute_word_spans(text, start_time=1.5, end_time=4.5)
        words = text.split()
        self.assertEqual(len(spans), len(words))

        prev_end = 1.5
        for i, (span, word) in enumerate(zip(spans, words)):
            self.assertEqual(span["word"], word)
            self.assertEqual(span["timing_source"], "observed")
            self.assertGreaterEqual(span["start"], prev_end - 0.001)
            self.assertGreater(span["end"], span["start"])
            prev_end = span["end"]

        self.assertAlmostEqual(spans[-1]["end"], 4.5, delta=0.01)

    def test_compute_word_spans_empty_text(self):
        self.assertEqual(compute_word_spans("", 0.0, 1.0), [])
        self.assertEqual(compute_word_spans("   ", 0.0, 1.0), [])

    def test_clean_acoustic_text_digit_grouping_commas(self):
        from kokoro_synthesizer import clean_acoustic_text
        raw = 'In addition, by 1950 over 150,000 supposedly "defective" children, and 7,500 women, raised $1,000,000.'
        cleaned = clean_acoustic_text(raw)
        self.assertIn("150000", cleaned)
        self.assertIn("7500", cleaned)
        self.assertIn("$1000000", cleaned)
        self.assertNotIn("150,000", cleaned)
        self.assertNotIn("7,500", cleaned)
        # Verify ordinary clause commas are preserved
        self.assertIn("In addition,", cleaned)

    def test_synthesize_chapter_end_to_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            can_path = tmp_path / "test_ch01_canonical_sentences.json"
            ana_path = tmp_path / "test_ch01_full_analysis.json"
            alg_path = tmp_path / "test_ch01_aligned_sentences.json"
            mp3_path = tmp_path / "audio" / "chapter_01.mp3"

            canonical = [
                {"id": "c1-s1", "text": "Critical thinking requires evaluating evidence.", "is_heading": False, "elem_idx": 1, "tag": "p"},
                {"id": "c1-s2", "text": "* * *", "is_heading": False, "elem_idx": 2, "tag": "p"},  # Non-alphanumeric test
                {"id": "c1-s3", "text": "It helps us make better decisions.", "is_heading": False, "elem_idx": 3, "tag": "p"},
            ]
            analysis = [
                {"id": "c1-s1", "text": "Critical thinking requires evaluating evidence.", "trans": "批判性思维需要评估证据。", "vocab": []},
                {"id": "c1-s2", "text": "* * *", "trans": "分割线", "vocab": []},
                {"id": "c1-s3", "text": "It helps us make better decisions.", "trans": "它帮助我们做出更好的决策。", "vocab": []},
            ]

            can_path.write_text(json.dumps(canonical), encoding="utf-8")
            ana_path.write_text(json.dumps(analysis), encoding="utf-8")

            # 1. Synthesize
            out_alg, out_mp3 = synthesize_chapter(
                canonical_path=can_path,
                analysis_path=ana_path,
                aligned_output_path=alg_path,
                audio_output_path=mp3_path,
                voice="am_adam",
                speed=1.0,
            )

            self.assertTrue(out_mp3.is_file())
            self.assertTrue(out_alg.is_file())
            self.assertGreater(out_mp3.stat().st_size, 5000)

            alg_data = json.loads(out_alg.read_text(encoding="utf-8"))
            self.assertEqual(len(alg_data), 3)

            # Check sentence 1 (alphanumeric)
            self.assertTrue(alg_data[0]["has_audio_match"])
            self.assertEqual(alg_data[0]["alignment_status"], "validated")
            self.assertGreater(len(alg_data[0]["word_spans"]), 0)

            # Check sentence 2 (pure symbol * * *)
            self.assertTrue(alg_data[1]["has_audio_match"])
            self.assertEqual(len(alg_data[1]["word_spans"]), 3)
            self.assertGreater(alg_data[1]["end"], alg_data[1]["start"])

            # Check sentence 3
            self.assertGreater(alg_data[2]["start"], alg_data[1]["end"] - 0.001)

            # 2. Physical Audio Integrity Check
            last_end = alg_data[-1]["end"]
            res = check_audio_physical_integrity(out_mp3, expected_duration=last_end, max_duration_delta=0.45)
            self.assertEqual(res["status"], "passed", res)

            # 3. Checkpointing test: subsequent call returns cached paths immediately
            mtime_before = out_mp3.stat().st_mtime
            out_alg2, out_mp32 = synthesize_chapter(
                canonical_path=can_path,
                analysis_path=ana_path,
                aligned_output_path=alg_path,
                audio_output_path=mp3_path,
            )
            self.assertEqual(mtime_before, out_mp32.stat().st_mtime)

            # 4. Release gate validation test in SYNTHETIC mode
            profile_path = tmp_path / "audio_content_profile.json"
            profile_path.write_text(json.dumps({"schema_version": 1, "audio_content_mode": "synthetic"}), encoding="utf-8")
            gate_code = validate(tmp_path)
            self.assertEqual(gate_code, 0)


if __name__ == "__main__":
    unittest.main()
