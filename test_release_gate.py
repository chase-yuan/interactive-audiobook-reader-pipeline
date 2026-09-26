import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from validate_outputs import _chapter_audio_exists, _suspicious_sentence_boundaries, validate
from dynamic_aligner import align_sentences_with_audio
from pipeline import _find_chapter_audio


class ReleaseGateTests(unittest.TestCase):
    def _write_fixture(self, root: Path, *, status="validated"):
        (root / "audio").mkdir()
        (root / "audio" / "chapter_01.mp3").write_bytes(b"fixture")
        canonical = [{"id": "s-1", "text": "A sentence."}]
        analysis = [{"id": "s-1", "text": "A sentence.", "trans": "一个句子。", "vocab": []}]
        aligned = [{
            "id": "s-1", "text": "A sentence.", "word_spans": [{"word": "A", "start": 0.0, "end": 0.2}],
            "raw_start": 0.0, "raw_end": 0.4, "has_audio_match": True,
            "fallback_used": False, "alignment_status": status,
            "matched_token_count": 2, "source_token_count": 2, "match_ratio": 1.0,
        }]
        for suffix, data in (("canonical_sentences", canonical), ("full_analysis", analysis), ("aligned_sentences", aligned)):
            (root / f"book_ch01_{suffix}.json").write_text(json.dumps(data), encoding="utf-8")

    def test_valid_fixture_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            self.assertEqual(validate(root), 0)

    def test_provenance_mode_requires_manifests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            self.assertNotEqual(validate(root, require_provenance=True), 0)

    def test_review_required_fixture_blocks_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root, status="review-required")
            self.assertNotEqual(validate(root), 0)

    def test_low_chapter_acoustic_coverage_blocks_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            aligned = root / "book_ch01_aligned_sentences.json"
            data = json.loads(aligned.read_text(encoding="utf-8"))
            data[0]["matched_token_count"] = 1
            data[0]["source_token_count"] = 10
            data[0]["match_ratio"] = 0.1
            aligned.write_text(json.dumps(data), encoding="utf-8")
            self.assertNotEqual(validate(root), 0)
            report = json.loads((root / "reader_validation_report.json").read_text(encoding="utf-8")) if (root / "reader_validation_report.json").exists() else None
            self.assertIsNone(report)

    def test_low_lexical_ratio_with_complete_physical_spans_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            aligned = root / "book_ch01_aligned_sentences.json"
            data = json.loads(aligned.read_text(encoding="utf-8"))
            data[0]["word_spans"] = [
                {"word": word, "start": float(index), "end": float(index) + 0.2}
                for index, word in enumerate(("A", "sentence."))
            ]
            data[0]["matched_token_count"] = 2
            data[0]["match_ratio"] = 0.4
            aligned.write_text(json.dumps(data), encoding="utf-8")
            self.assertEqual(validate(root), 0)

    def test_estimated_word_span_cannot_pass_as_karaoke(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            aligned = root / "book_ch01_aligned_sentences.json"
            data = json.loads(aligned.read_text(encoding="utf-8"))
            data[0]["word_spans"] = [
                {"word": "A", "start": 0.0, "end": 0.2, "timing_source": "observed"},
                {"word": "sentence.", "start": 0.2, "end": 0.4, "timing_source": "estimated"},
            ]
            aligned.write_text(json.dumps(data), encoding="utf-8")
            self.assertNotEqual(validate(root), 0)

    def test_course_profile_requires_explicit_scope_and_hash_bound_transcript(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "audio").mkdir()
            (root / "audio" / "lesson.mp3").write_bytes(b"fixture")
            spoken = root / "spoken.txt"
            spoken.write_text("Narrated sentence.", encoding="utf-8")
            digest = hashlib.sha256(spoken.read_bytes()).hexdigest()
            canonical = [
                {"id": "s-1", "text": "Narrated sentence."},
                {"id": "s-2", "text": "EPUB-only reference."},
            ]
            analysis = [{**item, "trans": "译文", "vocab": []} for item in canonical]
            aligned = [
                {**analysis[0], "word_spans": [{"word": "Narrated", "start": 0, "end": .2}, {"word": "sentence.", "start": .2, "end": .4}], "raw_start": 0, "raw_end": .4, "has_audio_match": True, "fallback_used": False, "alignment_status": "validated", "matched_token_count": 2, "source_token_count": 2, "match_ratio": 1},
                {**analysis[1], "word_spans": [], "raw_start": None, "raw_end": None, "has_audio_match": False, "fallback_used": False, "alignment_status": "not-applicable", "alignment_reason": "out_of_scope_reference", "matched_token_count": 0, "source_token_count": 3, "match_ratio": 0},
            ]
            for suffix, data in (("canonical_sentences", canonical), ("full_analysis", analysis), ("aligned_sentences", aligned)):
                (root / f"book_ch01_{suffix}.json").write_text(json.dumps(data), encoding="utf-8")
            (root / "audio_content_profile.json").write_text(json.dumps({
                "schema_version": 1, "audio_content_mode": "course",
                "spoken_source": {"path": "spoken.txt", "sha256": digest},
                "units": [{"chapter": 1, "audio_path": "audio/lesson.mp3", "audio_start": 0, "audio_end": 10, "sentence_ids": ["s-1"]}],
            }), encoding="utf-8")
            self.assertEqual(validate(root), 0)
            aligned[1]["alignment_reason"] = "non_narrated_text"
            (root / "book_ch01_aligned_sentences.json").write_text(json.dumps(aligned), encoding="utf-8")
            self.assertNotEqual(validate(root), 0)
            aligned[1]["alignment_reason"] = "out_of_scope_reference"
            aligned[0]["raw_end"] = 11
            (root / "book_ch01_aligned_sentences.json").write_text(json.dumps(aligned), encoding="utf-8")
            self.assertNotEqual(validate(root), 0)

    def test_audio_omission_is_not_a_non_narrated_exception(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            aligned = root / "book_ch01_aligned_sentences.json"
            data = json.loads(aligned.read_text(encoding="utf-8"))
            data[0].update({"has_audio_match": False, "word_spans": [], "alignment_status": "review-required", "alignment_reason": "audio_omitted"})
            aligned.write_text(json.dumps(data), encoding="utf-8")
            self.assertNotEqual(validate(root), 0)

    def test_owner_review_ledger_blocks_release_instead_of_waiving_alignment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            aligned = root / "book_ch01_aligned_sentences.json"
            data = json.loads(aligned.read_text(encoding="utf-8"))
            data[0]["has_audio_match"] = False
            data[0]["fallback_used"] = True
            aligned.write_text(json.dumps(data), encoding="utf-8")
            (root / "reader_review_ledger.json").write_text(json.dumps({
                "schema_version": 1,
                "reviews": [{
                    "chapter": 1,
                    "sentence_id": "s-1",
                    "decision": "accepted",
                    "reviewer": "project_owner",
                    "evidence": "Reviewed audiobook wording discrepancy.",
                }],
            }), encoding="utf-8")
            self.assertNotEqual(validate(root), 0)

    def test_unmatched_record_blocks_release_without_manual_waiver(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "audio").mkdir()
            (root / "audio" / "chapter_01.mp3").write_bytes(b"fixture")
            canonical = [
                {"id": "s-1", "text": "First sentence."},
                {"id": "s-2", "text": "Print only sidebar."},
                {"id": "s-3", "text": "Third sentence."},
            ]
            analysis = [{**item, "trans": "译文", "vocab": []} for item in canonical]
            aligned = [
                {**analysis[0], "word_spans": [{"word": "First", "start": 1, "end": 2}], "raw_start": 1, "raw_end": 2, "has_audio_match": True, "fallback_used": False, "alignment_status": "validated", "matched_token_count": 2, "source_token_count": 2, "match_ratio": 1},
                {**analysis[1], "word_spans": [], "raw_start": 99, "raw_end": 99, "has_audio_match": False, "fallback_used": False, "alignment_status": "review-required", "matched_token_count": 0, "source_token_count": 3, "match_ratio": 0},
                {**analysis[2], "word_spans": [{"word": "Third", "start": 3, "end": 4}], "raw_start": 3, "raw_end": 4, "has_audio_match": True, "fallback_used": False, "alignment_status": "validated", "matched_token_count": 2, "source_token_count": 2, "match_ratio": 1},
            ]
            for suffix, data in (("canonical_sentences", canonical), ("full_analysis", analysis), ("aligned_sentences", aligned)):
                (root / f"book_ch01_{suffix}.json").write_text(json.dumps(data), encoding="utf-8")
            (root / "reader_review_ledger.json").write_text(json.dumps({
                "schema_version": 1,
                "reviews": [{"chapter": 1, "sentence_id": "s-2", "decision": "accepted", "reviewer": "project_owner", "evidence": "Verified as print-only content between narrated anchors."}],
            }), encoding="utf-8")
            self.assertNotEqual(validate(root), 0)

    def test_reviewed_out_of_order_alignment_can_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "audio").mkdir()
            (root / "audio" / "chapter_01.mp3").write_bytes(b"fixture")
            sentences = [
                {"id": "s-1", "text": "first exact phrase", "trans": "第一个准确短语", "vocab": []},
                {"id": "s-2", "text": "second exact phrase", "trans": "第二个准确短语", "vocab": []},
            ]
            analysis_path = root / "book_ch01_full_analysis.json"
            analysis_path.write_text(json.dumps(sentences), encoding="utf-8")
            (root / "book_ch01_canonical_sentences.json").write_text(json.dumps(sentences), encoding="utf-8")
            acoustic_path = root / "audio" / "book_ch01_acoustic_words.json"
            acoustic_path.write_text(json.dumps({"words": [
                {"word": word, "start": index, "end": index + 0.5}
                for index, word in enumerate("second exact phrase filler first exact phrase".split())
            ]}), encoding="utf-8")
            aligned_path = root / "book_ch01_aligned_sentences.json"
            align_sentences_with_audio(acoustic_path, analysis_path, aligned_path)
            self.assertNotEqual(validate(root), 0)

            aligned = json.loads(aligned_path.read_text(encoding="utf-8"))
            aligned[1]["alignment_status"] = "reviewed"
            aligned[1]["review_evidence"] = "Verified against the acoustic word sequence."
            aligned_path.write_text(json.dumps(aligned), encoding="utf-8")
            self.assertEqual(validate(root), 0)

    def test_structural_heading_and_attribution_audio_order_can_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "audio").mkdir()
            (root / "audio" / "chapter_01.mp3").write_bytes(b"fixture")
            sentences = [
                {"id": "s-0", "text": "A dragon without its rider is a tragedy.", "trans": "失去骑手的龙是一场悲剧。", "vocab": []},
                {"id": "s-1", "text": "—Article One The Dragon Rider’s Codex", "trans": "《龙骑士法典》第一条", "vocab": []},
                {"id": "s-2", "text": "CHAPTER ONE", "trans": "第一章", "vocab": []},
            ]
            for suffix in ("canonical_sentences", "full_analysis"):
                (root / f"book_ch01_{suffix}.json").write_text(json.dumps(sentences), encoding="utf-8")
            acoustic_path = root / "audio" / "book_ch01_acoustic_words.json"
            spoken = "Chapter one A quote from Article One The Dragon Rider's Codex A dragon without its rider is a tragedy".split()
            acoustic_path.write_text(json.dumps({"words": [
                {"word": word, "start": index, "end": index + 0.5}
                for index, word in enumerate(spoken)
            ]}), encoding="utf-8")
            aligned_path = root / "book_ch01_aligned_sentences.json"
            align_sentences_with_audio(acoustic_path, root / "book_ch01_full_analysis.json", aligned_path)

            self.assertEqual(validate(root), 0)

    def test_empty_translation_blocks_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            analysis = root / "book_ch01_full_analysis.json"
            data = json.loads(analysis.read_text(encoding="utf-8"))
            data[0]["trans"] = ""
            analysis.write_text(json.dumps(data), encoding="utf-8")
            self.assertNotEqual(validate(root), 0)

    def test_malformed_vocabulary_blocks_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            analysis = root / "book_ch01_full_analysis.json"
            data = json.loads(analysis.read_text(encoding="utf-8"))
            data[0]["vocab"] = [{"word": "only-word"}]
            analysis.write_text(json.dumps(data), encoding="utf-8")
            self.assertNotEqual(validate(root), 0)

    def test_manifest_detects_post_alignment_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            aligned = root / "book_ch01_aligned_sentences.json"
            digest = hashlib.sha256(aligned.read_bytes()).hexdigest()
            (root / "reader_run_manifest.json").write_text(json.dumps({
                "schema_version": 2,
                "chapters": [{"chapter": 1, "aligned_sha256": digest}],
            }), encoding="utf-8")
            aligned.write_text(aligned.read_text() + "\n", encoding="utf-8")
            self.assertNotEqual(validate(root), 0)

    def test_audio_fallback_matches_explicit_chapter_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            audio_dir = Path(tmp)
            (audio_dir / "narration_ch10.mp3").write_bytes(b"10")
            (audio_dir / "narration_ch11.mp3").write_bytes(b"11")
            self.assertIsNone(_find_chapter_audio(str(audio_dir), 1))
            self.assertEqual(Path(_find_chapter_audio(str(audio_dir), 11)).name, "narration_ch11.mp3")
            self.assertFalse(_chapter_audio_exists(audio_dir, 1))
            self.assertTrue(_chapter_audio_exists(audio_dir, 11))

    def test_ambiguous_audio_candidates_block_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            (root / "audio" / "bonus_ch01.mp3").write_bytes(b"bonus")
            self.assertIsNone(_find_chapter_audio(str(root / "audio"), 1))
            self.assertFalse(_chapter_audio_exists(root / "audio", 1))
            self.assertNotEqual(validate(root), 0)

    def test_common_abbreviations_do_not_trigger_boundary_warning(self):
        self.assertEqual(_suspicious_sentence_boundaries("Mrs. Winchester asked Dr. Hewitt.") , [])
        self.assertEqual(_suspicious_sentence_boundaries("A Guide to U.S. Prisons."), [])
    def test_text_only_profile_passes_without_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "audio_content_profile.json").write_text(json.dumps({
                "schema_version": 1,
                "audio_content_mode": "text_only"
            }), encoding="utf-8")
            canonical = [{"id": "s-1", "text": "A sentence."}]
            analysis = [{"id": "s-1", "text": "A sentence.", "trans": "一个句子。", "vocab": []}]
            aligned = [{"id": "s-1", "text": "A sentence.", "trans": "一个句子。", "vocab": [], "has_audio_match": False, "start": None, "end": None, "word_spans": []}]
            for suffix, data in (("canonical_sentences", canonical), ("full_analysis", analysis), ("aligned_sentences", aligned)):
                (root / f"book_ch01_{suffix}.json").write_text(json.dumps(data), encoding="utf-8")
            rep_path = root / "reader_validation_report.json"
            self.assertEqual(validate(root, rep_path), 0)
            report = json.loads(rep_path.read_text(encoding="utf-8"))
            self.assertTrue(report["release_ready"])
            self.assertEqual(report["audio_content_mode"], "text_only")

    def test_large_non_narrated_omission_blocks_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_fixture(root)
            aligned_file = root / "book_ch01_aligned_sentences.json"
            canonical_file = root / "book_ch01_canonical_sentences.json"
            analysis_file = root / "book_ch01_full_analysis.json"
            
            # Create 20 sentences where 16 are non_narrated_text (> 10% and > 15 count)
            can_list = []
            ana_list = []
            ali_list = []
            for i in range(20):
                sid = f"s-{i+1}"
                is_omitted = i >= 4
                text = f"Sentence {i+1}."
                can_list.append({"id": sid, "text": text})
                ana_list.append({"id": sid, "text": text, "trans": f"句子 {i+1}。", "vocab": []})
                if is_omitted:
                    ali_list.append({
                        "id": sid, "text": text, "trans": f"句子 {i+1}。", "vocab": [],
                        "has_audio_match": False, "start": None, "end": None, "word_spans": [],
                        "alignment_status": "not-applicable", "alignment_reason": "non_narrated_text",
                        "source_token_count": 2, "matched_token_count": 0,
                    })
                else:
                    ali_list.append({
                        "id": sid, "text": text, "trans": f"句子 {i+1}。", "vocab": [],
                        "has_audio_match": True, "start": float(i * 2), "end": float(i * 2 + 1.5),
                        "word_spans": [
                            {"word": "Sentence", "start": float(i * 2), "end": float(i * 2 + 0.8), "timing_source": "observed"},
                            {"word": f"{i+1}.", "start": float(i * 2 + 0.8), "end": float(i * 2 + 1.5), "timing_source": "observed"}
                        ],
                        "alignment_status": "validated", "alignment_reason": None,
                        "source_token_count": 2, "matched_token_count": 2, "match_ratio": 1.0,
                    })
            canonical_file.write_text(json.dumps(can_list), encoding="utf-8")
            analysis_file.write_text(json.dumps(ana_list), encoding="utf-8")
            aligned_file.write_text(json.dumps(ali_list), encoding="utf-8")
            
            rep_path = root / "reader_validation_report.json"
            code = validate(root, rep_path)
            self.assertNotEqual(code, 0)
            report = json.loads(rep_path.read_text(encoding="utf-8"))
            self.assertFalse(report["release_ready"])
            self.assertTrue(any("exceeds the 10%" in err for err in report["errors"]))


if __name__ == "__main__":
    unittest.main()
