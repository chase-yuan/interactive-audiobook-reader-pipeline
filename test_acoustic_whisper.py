import json
import tempfile
import unittest
from pathlib import Path

from acoustic_whisper import (
    ACOUSTIC_PROFILE_VERSION,
    ACOUSTIC_TRANSCRIPTION_OPTIONS,
    run_mlx_acoustic_extraction,
    is_acoustic_ready,
)


class AcousticWhisperTests(unittest.TestCase):
    def test_extraction_disables_cross_window_prompt_and_records_profile(self):
        observed = {}

        def fake_transcribe(audio_path, **kwargs):
            observed.update(kwargs)
            return {
                "segments": [{
                    "id": 1,
                    "start": 1.0,
                    "end": 2.0,
                    "text": " Complete sentence.",
                    "words": [{"word": " Complete", "start": 1.0, "end": 1.5, "probability": 0.9}],
                }]
            }

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "acoustic.json"
            result = run_mlx_acoustic_extraction("chapter.mp3", output, transcribe_fn=fake_transcribe)
            written = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(observed["condition_on_previous_text"], False)
        self.assertEqual(observed["hallucination_silence_threshold"], 2.0)
        self.assertEqual(observed["language"], "en")
        self.assertEqual(result["acoustic_profile_version"], ACOUSTIC_PROFILE_VERSION)
        self.assertEqual(written["transcription_options"], ACOUSTIC_TRANSCRIPTION_OPTIONS)

    def test_runner_rejects_legacy_acoustic_artifact_for_regeneration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            legacy = root / "legacy.json"
            current = root / "current.json"
            padding = "x" * 1200
            legacy.write_text(json.dumps({"padding": padding, "words": [{"word": "old"}]}), encoding="utf-8")
            current.write_text(json.dumps({
                "acoustic_profile_version": ACOUSTIC_PROFILE_VERSION,
                "padding": padding,
                "words": [{"word": "current"}],
            }), encoding="utf-8")

            self.assertTrue(is_acoustic_ready(legacy))
            self.assertFalse(is_acoustic_ready(legacy, require_current_profile=True))
            self.assertTrue(is_acoustic_ready(current, require_current_profile=True))

    def test_acoustic_preflight_blocks_implicit_rebuild_of_existing_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio_dir = root / "audio"
            audio_dir.mkdir()
            for chapter in range(1, 3):
                (audio_dir / f"book_ch{chapter:02d}_acoustic_words.json").write_text(
                    json.dumps({"words": [{"word": "legacy"}]}), encoding="utf-8"
                )

            def check_preflight(paths, allow_rebuild=False):
                blocked = [p.name for p in paths if not is_acoustic_ready(p, require_current_profile=True) and not allow_rebuild]
                return len(blocked) == 0

            cand_paths = [audio_dir / f"book_ch{ch:02d}_acoustic_words.json" for ch in range(1, 3)]
            self.assertFalse(check_preflight(cand_paths, allow_rebuild=False))
            self.assertTrue(check_preflight(cand_paths, allow_rebuild=True))

    def test_extraction_rejects_reverse_word_timestamps(self):
        def fake_transcribe(audio_path, **kwargs):
            return {"segments": [{"words": [{"word": "broken", "start": 2.0, "end": 1.0}]}]}

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "acoustic.json"
            with self.assertRaises(ValueError):
                run_mlx_acoustic_extraction("chapter.mp3", output, transcribe_fn=fake_transcribe)

    def test_extraction_records_and_discards_zero_duration_words(self):
        def fake_transcribe(audio_path, **kwargs):
            return {"segments": [{"words": [
                {"word": "boundary", "start": 2.0, "end": 2.0},
                {"word": "valid", "start": 2.0, "end": 2.5},
            ]}]}

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "acoustic.json"
            result = run_mlx_acoustic_extraction("chapter.mp3", output, transcribe_fn=fake_transcribe)

        self.assertEqual(result["dropped_zero_duration_words"], 1)
        self.assertEqual([word["word"] for word in result["words"]], ["valid"])


if __name__ == "__main__":
    unittest.main()
