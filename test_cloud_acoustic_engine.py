"""
Unit Tests for cloud_acoustic_engine.py
Verifies API key resolution, compression contracts, Groq payload normalization,
rate-limit retry resilience, schema parity, and fallback to MLX Whisper.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from acoustic_whisper import is_acoustic_ready
from cloud_acoustic_engine import (
    ACOUSTIC_PROFILE_VERSION,
    compress_audio_if_needed,
    resolve_groq_api_key,
    run_acoustic_extraction,
    run_groq_acoustic_extraction,
    transcribe_chapters_parallel_groq,
)


class TestCloudAcousticEngine(unittest.TestCase):
    def test_resolve_groq_api_key_priority(self):
        # 1. Explicit argument wins
        self.assertEqual(resolve_groq_api_key("gsk_arg_priority"), "gsk_arg_priority")

        # 2. Environment variable fallback
        with patch.dict(os.environ, {"GROQ_API_KEY": "gsk_env_test"}):
            self.assertEqual(resolve_groq_api_key(), "gsk_env_test")

        # 3. Config file fallback
        with tempfile.TemporaryDirectory() as tmp_dir:
            fake_config = Path(tmp_dir) / "key"
            fake_config.write_text("gsk_file_test\n", encoding="utf-8")
            with patch("cloud_acoustic_engine.Path.home", return_value=Path(tmp_dir)):
                with patch.dict(os.environ, {}, clear=True):
                    # Mock the candidate path
                    with patch("cloud_acoustic_engine.Path.is_file", return_value=True), \
                         patch("cloud_acoustic_engine.Path.read_text", return_value="gsk_file_test"):
                        key = resolve_groq_api_key()
                        self.assertEqual(key, "gsk_file_test")

    def test_compress_audio_if_needed_small_file_passthrough(self):
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
            tf.write(b"ID3" + b"\x00" * 1024)
            tf_path = Path(tf.name)

        try:
            path_to_send, is_temp = compress_audio_if_needed(tf_path, max_bytes=10 * 1024 * 1024)
            self.assertEqual(path_to_send, tf_path.resolve())
            self.assertFalse(is_temp)
        finally:
            if tf_path.exists():
                tf_path.unlink()

    @patch("cloud_acoustic_engine.requests.Session")
    def test_groq_acoustic_extraction_schema_parity(self, mock_session_cls):
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        words = [
            {"word": f"word_{i}", "start": float(i), "end": float(i) + 0.5, "probability": 0.98}
            for i in range(50)
        ]
        mock_resp.json.return_value = {
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 50.0,
                    "text": " The Drunkard's Walk test sentence with plenty of words.",
                    "words": words,
                }
            ]
        }
        mock_session.post.return_value = mock_resp

        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "test.mp3"
            audio_path.write_bytes(b"dummy audio data")
            out_json = Path(tmp_dir) / "test_acoustic_words.json"

            result = run_groq_acoustic_extraction(
                audio_path=audio_path,
                output_json_path=out_json,
                api_key="gsk_mock_test_key",
                session=mock_session,
            )

            # Check return value
            self.assertEqual(result["schema_version"], 2)
            self.assertEqual(result["acoustic_profile_version"], ACOUSTIC_PROFILE_VERSION)
            self.assertEqual(len(result["words"]), 50)
            self.assertEqual(result["words"][0]["word"], "word_0")
            self.assertEqual(result["words"][0]["start"], 0.0)
            self.assertEqual(result["words"][0]["end"], 0.5)

            # Check file written on disk
            self.assertTrue(out_json.is_file())
            written = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(written["model"], "groq/whisper-large-v3-turbo")
            self.assertTrue(is_acoustic_ready(out_json, require_current_profile=True))

    @patch("cloud_acoustic_engine.requests.post")
    def test_groq_retry_on_429_rate_limit(self, mock_post):
        # 1st call: 429, 2nd call: 200
        resp_429 = MagicMock()
        resp_429.status_code = 429

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "segments": [
                {
                    "id": 0, "start": 0.0, "end": 1.0, "text": "Ok",
                    "words": [{"word": "Ok", "start": 0.1, "end": 0.9, "probability": 0.99}],
                }
            ]
        }
        mock_post.side_effect = [resp_429, resp_200]

        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "test.mp3"
            audio_path.write_bytes(b"dummy audio data")
            out_json = Path(tmp_dir) / "test_acoustic_words.json"

            with patch("cloud_acoustic_engine.time.sleep") as mock_sleep:
                result = run_groq_acoustic_extraction(
                    audio_path=audio_path,
                    output_json_path=out_json,
                    api_key="gsk_mock_key",
                )
                self.assertEqual(mock_post.call_count, 2)
                mock_sleep.assert_called_once()
                self.assertEqual(len(result["words"]), 1)

    @patch("cloud_acoustic_engine.requests.post")
    def test_groq_multi_key_rotation_on_429(self, mock_post):
        # 1st call on key 1: 429, 2nd call on key 2: 200
        resp_429 = MagicMock()
        resp_429.status_code = 429

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {
            "segments": [
                {
                    "id": 0, "start": 0.0, "end": 1.0, "text": "Multi-key success",
                    "words": [{"word": "Multi-key", "start": 0.0, "end": 0.5, "probability": 0.99}],
                }
            ]
        }
        mock_post.side_effect = [resp_429, resp_200]

        with tempfile.TemporaryDirectory() as tmp_dir:
            audio_path = Path(tmp_dir) / "test.mp3"
            audio_path.write_bytes(b"dummy audio data")
            out_json = Path(tmp_dir) / "test_acoustic_words.json"

            with patch("cloud_acoustic_engine.time.sleep") as mock_sleep:
                result = run_groq_acoustic_extraction(
                    audio_path=audio_path,
                    output_json_path=out_json,
                    api_key=["gsk_key_1", "gsk_key_2"],
                )
                self.assertEqual(mock_post.call_count, 2)
                # Verify that key was rotated in Authorization header
                first_call_auth = mock_post.call_args_list[0][1]["headers"]["Authorization"]
                second_call_auth = mock_post.call_args_list[1][1]["headers"]["Authorization"]
                self.assertEqual(first_call_auth, "Bearer gsk_key_1")
                self.assertEqual(second_call_auth, "Bearer gsk_key_2")
                self.assertEqual(len(result["words"]), 1)

    @patch("cloud_acoustic_engine.run_groq_acoustic_extraction")
    def test_transcribe_chapters_parallel_groq(self, mock_single):
        mock_single.return_value = {"words": [{"word": "test"}], "acoustic_profile_version": 2}
        tasks = [
            {"audio_path": "/fake/ch0.mp3", "output_json_path": "/fake/ch0.json", "label": "Ch 0"},
            {"audio_path": "/fake/ch1.mp3", "output_json_path": "/fake/ch1.json", "label": "Ch 1"},
        ]
        results = transcribe_chapters_parallel_groq(tasks, api_key="gsk_test", max_workers=2)
        self.assertEqual(len(results), 2)
        self.assertEqual(mock_single.call_count, 2)

    @patch("cloud_acoustic_engine.resolve_groq_api_key", return_value=None)
    @patch("acoustic_whisper.run_mlx_acoustic_extraction")
    def test_universal_dispatcher_falls_back_to_mlx_when_no_key(self, mock_mlx, mock_key):
        mock_mlx.return_value = {"words": [], "provider": "mlx"}
        res = run_acoustic_extraction("/fake/audio.mp3", "/fake/out.json", provider="auto")
        mock_mlx.assert_called_once()
        self.assertEqual(res["provider"], "mlx")


if __name__ == "__main__":
    unittest.main()
