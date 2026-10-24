import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from agy_linguistic_worker import (
    CHUNK_SIZE,
    _json_from_output,
    build_batch_prompt,
    can_reconcile_text,
    chunk_sentences,
    main,
    process_canonical_sentences,
    verify_analysis,
)
from artifact_io import atomic_write_json


class AgyLinguisticWorkerTests(unittest.TestCase):
    def test_chunk_sentences_splits_correctly(self):
        records_120 = [{"id": f"s-{i}", "text": f"Sentence {i}."} for i in range(1, 121)]
        chunks = chunk_sentences(records_120, chunk_size=50)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(len(chunks[0]), 50)
        self.assertEqual(len(chunks[1]), 50)
        self.assertEqual(len(chunks[2]), 20)
        self.assertEqual(chunks[0][0]["id"], "s-1")
        self.assertEqual(chunks[0][-1]["id"], "s-50")
        self.assertEqual(chunks[1][0]["id"], "s-51")
        self.assertEqual(chunks[1][-1]["id"], "s-100")
        self.assertEqual(chunks[2][0]["id"], "s-101")
        self.assertEqual(chunks[2][-1]["id"], "s-120")

        # 50 records -> 1 chunk of 50
        records_50 = [{"id": f"s-{i}", "text": f"Sentence {i}."} for i in range(1, 51)]
        chunks_50 = chunk_sentences(records_50, chunk_size=50)
        self.assertEqual(len(chunks_50), 1)
        self.assertEqual(len(chunks_50[0]), 50)

        # 20 records -> 1 chunk of 20
        records_20 = [{"id": f"s-{i}", "text": f"Sentence {i}."} for i in range(1, 21)]
        chunks_20 = chunk_sentences(records_20, chunk_size=50)
        self.assertEqual(len(chunks_20), 1)
        self.assertEqual(len(chunks_20[0]), 20)

        # 0 records -> 0 chunks
        self.assertEqual(chunk_sentences([], chunk_size=50), [])

        # Invalid chunk size
        with self.assertRaises(ValueError):
            chunk_sentences(records_20, chunk_size=0)

    def test_json_from_output_parses_various_formats(self):
        # Plain JSON
        plain = json.dumps([{"id": "s-1", "text": "Hello", "trans": "你好", "vocab": []}])
        self.assertEqual(_json_from_output(plain), [{"id": "s-1", "text": "Hello", "trans": "你好", "vocab": []}])

        # Markdown fenced json
        fenced = "```json\n" + plain + "\n```"
        self.assertEqual(_json_from_output(fenced), [{"id": "s-1", "text": "Hello", "trans": "你好", "vocab": []}])

        # Markdown fenced with commentary
        with_commentary = "Here is the result:\n```json\n" + plain + "\n```\nDone."
        self.assertEqual(_json_from_output(with_commentary), [{"id": "s-1", "text": "Hello", "trans": "你好", "vocab": []}])

    def test_can_reconcile_text(self):
        canonical = 'Morton Meyers writes: “Over 144,000 plant extracts, not a single drug reached status.'
        # Typographic quote normalization
        straight_quotes = 'Morton Meyers writes: "Over 144,000 plant extracts, not a single drug reached status.'
        self.assertTrue(can_reconcile_text(straight_quotes, canonical))

        # Minor spacing or footnote normalization
        minor_divergence = 'Morton Meyers writes: "Over 144,000 plant extracts, not a single drug reached status."'
        self.assertTrue(can_reconcile_text(minor_divergence, canonical))

        # Completely changed text should reject
        completely_different = 'This is an entirely different sentence.'
        self.assertFalse(can_reconcile_text(completely_different, canonical))

    def test_verify_analysis_contract(self):
        canonical = [
            {"id": "s-1", "text": "Sentence 1."},
            {"id": "s-2", "text": "Sentence 2."},
        ]
        valid_analysis = [
            {"id": "s-1", "text": "Sentence 1.", "trans": "句子一。", "vocab": [{"word": "sentence", "pos": "n.", "def": "句子"}]},
            {"id": "s-2", "text": "Sentence 2.", "trans": "句子二。", "vocab": []},
        ]
        # Should not raise
        verify_analysis(valid_analysis, canonical)

        # Count mismatch
        with self.assertRaises(RuntimeError):
            verify_analysis(valid_analysis[:1], canonical)

        # ID mismatch
        bad_id = [
            {"id": "s-2", "text": "Sentence 1.", "trans": "句子一。", "vocab": []},
            {"id": "s-1", "text": "Sentence 2.", "trans": "句子二。", "vocab": []},
        ]
        with self.assertRaises(RuntimeError):
            verify_analysis(bad_id, canonical)

        # Text mismatch
        bad_text = [
            {"id": "s-1", "text": "Changed text.", "trans": "句子一。", "vocab": []},
            {"id": "s-2", "text": "Sentence 2.", "trans": "句子二。", "vocab": []},
        ]
        with self.assertRaises(RuntimeError):
            verify_analysis(bad_text, canonical)

        # Empty translation
        empty_trans = [
            {"id": "s-1", "text": "Sentence 1.", "trans": "", "vocab": []},
            {"id": "s-2", "text": "Sentence 2.", "trans": "句子二。", "vocab": []},
        ]
        with self.assertRaises(RuntimeError):
            verify_analysis(empty_trans, canonical)

        # Malformed vocab entry
        bad_vocab = [
            {"id": "s-1", "text": "Sentence 1.", "trans": "句子一。", "vocab": [{"word": "test"}]},
            {"id": "s-2", "text": "Sentence 2.", "trans": "句子二。", "vocab": []},
        ]
        with self.assertRaises(RuntimeError):
            verify_analysis(bad_vocab, canonical)

    @patch("subprocess.run")
    def test_missing_translation_is_rejected_instead_of_fabricated(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"id": "s-1", "text": "Source sentence.", "trans": "", "vocab": []}]),
            stderr="",
        )
        with self.assertRaises(RuntimeError) as ctx:
            process_canonical_sentences(
                [{"id": "s-1", "text": "Source sentence."}],
                "Analyze", Path("."), max_batch_attempts=1,
            )
        self.assertIn("missing or empty translation", str(ctx.exception))

    @patch("subprocess.run")
    def test_parallel_batches_preserve_canonical_order(self, mock_run):
        def fake_run(cmd, **kwargs):
            prompt = cmd[-1]
            payload = prompt.split("```json\n", 1)[1].split("\n```", 1)[0]
            batch = json.loads(payload)
            analyzed = [
                {"id": item["id"], "text": item["text"], "trans": f"译文 {item['id']}", "vocab": []}
                for item in batch
            ]
            return MagicMock(returncode=0, stdout=json.dumps(analyzed), stderr="")

        mock_run.side_effect = fake_run
        canonical = [{"id": f"s-{i}", "text": f"Sentence {i}."} for i in range(8)]
        result = process_canonical_sentences(
            canonical, "Analyze", Path("."), chunk_size=2, max_workers=4,
        )
        self.assertEqual([item["id"] for item in result], [item["id"] for item in canonical])

    @patch("subprocess.run")
    def test_120_sentence_chunking_and_merging_mock_subprocess(self, mock_run):
        # 120 canonical sentences
        canonical = [{"id": f"s-{i:03d}", "text": f"This is sentence {i}."} for i in range(1, 121)]

        def fake_subprocess_run(cmd, cwd=None, text=None, capture_output=None, timeout=None, **kwargs):
            prompt = cmd[-1]
            header = "Input canonical records"
            header_idx = prompt.find(header)
            start_marker = "```json\n"
            end_marker = "\n```"
            start_idx = prompt.find(start_marker, header_idx) + len(start_marker)
            end_idx = prompt.find(end_marker, start_idx)
            batch_data = json.loads(prompt[start_idx:end_idx])

            analyzed = [
                {
                    "id": item["id"],
                    "text": item["text"],
                    "trans": f"这是句子 {item['id']}。",
                    "vocab": [{"word": "sentence", "pos": "n.", "def": "句子"}],
                }
                for item in batch_data
            ]
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = f"```json\n{json.dumps(analyzed, ensure_ascii=False, indent=2)}\n```"
            mock_res.stderr = ""
            return mock_res

        mock_run.side_effect = fake_subprocess_run

        with tempfile.TemporaryDirectory() as tmp:
            canonical_path = Path(tmp) / "demo_ch01_canonical_sentences.json"
            output_path = Path(tmp) / "demo_ch01_full_analysis.json"
            atomic_write_json(canonical_path, canonical)

            env = {
                "READER_CANONICAL_PATH": str(canonical_path),
                "READER_OUTPUT_PATH": str(output_path),
            }

            ret = main(environ=env)
            self.assertEqual(ret, 0)
            self.assertTrue(output_path.is_file())

            # Verify subprocess was called 3 times (50, 50, 20)
            self.assertEqual(mock_run.call_count, 3)

            # Inspect calls
            call_0_prompt = mock_run.call_args_list[0][0][0][-1]
            call_1_prompt = mock_run.call_args_list[1][0][0][-1]
            call_2_prompt = mock_run.call_args_list[2][0][0][-1]

            self.assertIn("batch 1 of 3, 50 items", call_0_prompt)
            self.assertIn("batch 2 of 3, 50 items", call_1_prompt)
            self.assertIn("batch 3 of 3, 20 items", call_2_prompt)

            # Check output data
            output_data = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(len(output_data), 120)
            for i, record in enumerate(output_data, start=1):
                expected_id = f"s-{i:03d}"
                self.assertEqual(record["id"], expected_id)
                self.assertEqual(record["text"], f"This is sentence {i}.")
                self.assertEqual(record["trans"], f"这是句子 {expected_id}。")
                self.assertEqual(record["vocab"], [{"word": "sentence", "pos": "n.", "def": "句子"}])

    @patch("subprocess.run")
    def test_subprocess_failure_raises(self, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 1
        mock_res.stdout = ""
        mock_res.stderr = "Model rate limited"
        mock_run.return_value = mock_res

        canonical = [{"id": "s-1", "text": "Sentence 1."}]
        with tempfile.TemporaryDirectory() as tmp:
            canonical_path = Path(tmp) / "demo_ch01_canonical_sentences.json"
            output_path = Path(tmp) / "demo_ch01_full_analysis.json"
            atomic_write_json(canonical_path, canonical)

            env = {
                "READER_CANONICAL_PATH": str(canonical_path),
                "READER_OUTPUT_PATH": str(output_path),
            }
            with self.assertRaises(RuntimeError) as ctx:
                main(environ=env)
            self.assertIn("Model rate limited", str(ctx.exception))

    @patch("subprocess.run")
    def test_subprocess_timeout_raises(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["agy"], timeout=3700)
        canonical = [{"id": "s-1", "text": "Sentence 1."}]
        with tempfile.TemporaryDirectory() as tmp:
            canonical_path = Path(tmp) / "demo_ch01_canonical_sentences.json"
            output_path = Path(tmp) / "demo_ch01_full_analysis.json"
            atomic_write_json(canonical_path, canonical)

            env = {
                "READER_CANONICAL_PATH": str(canonical_path),
                "READER_OUTPUT_PATH": str(output_path),
            }
            with self.assertRaises(RuntimeError) as ctx:
                main(environ=env)
            self.assertIn("timed out", str(ctx.exception))

    @patch("subprocess.run")
    def test_batch_record_count_mismatch_raises(self, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 0
        # Returns 1 item when 2 were expected in the batch
        mock_res.stdout = json.dumps([{"id": "s-1", "text": "Sentence 1.", "trans": "句子一", "vocab": []}])
        mock_res.stderr = ""
        mock_run.return_value = mock_res

        canonical = [
            {"id": "s-1", "text": "Sentence 1."},
            {"id": "s-2", "text": "Sentence 2."},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            canonical_path = Path(tmp) / "demo_ch01_canonical_sentences.json"
            output_path = Path(tmp) / "demo_ch01_full_analysis.json"
            atomic_write_json(canonical_path, canonical)

            env = {
                "READER_CANONICAL_PATH": str(canonical_path),
                "READER_OUTPUT_PATH": str(output_path),
            }
            with self.assertRaises(RuntimeError) as ctx:
                main(environ=env)
            self.assertIn("returned 1 items, expected 2", str(ctx.exception))

    @patch("subprocess.run")
    def test_batch_output_not_list_raises(self, mock_run):
        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = json.dumps({"error": "invalid format"})
        mock_res.stderr = ""
        mock_run.return_value = mock_res

        canonical = [{"id": "s-1", "text": "Sentence 1."}]
        with tempfile.TemporaryDirectory() as tmp:
            canonical_path = Path(tmp) / "demo_ch01_canonical_sentences.json"
            output_path = Path(tmp) / "demo_ch01_full_analysis.json"
            atomic_write_json(canonical_path, canonical)

            env = {
                "READER_CANONICAL_PATH": str(canonical_path),
                "READER_OUTPUT_PATH": str(output_path),
            }
            with self.assertRaises(RuntimeError) as ctx:
                main(environ=env)
            self.assertIn("must be a JSON list", str(ctx.exception))

    def test_empty_canonical_input_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            canonical_path = Path(tmp) / "demo_ch01_canonical_sentences.json"
            output_path = Path(tmp) / "demo_ch01_full_analysis.json"
            atomic_write_json(canonical_path, [])

            env = {
                "READER_CANONICAL_PATH": str(canonical_path),
                "READER_OUTPUT_PATH": str(output_path),
            }
            ret = main(environ=env)
            self.assertEqual(ret, 0)
            self.assertEqual(json.loads(output_path.read_text()), [])


if __name__ == "__main__":
    unittest.main()
