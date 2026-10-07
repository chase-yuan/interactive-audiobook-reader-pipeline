import json
import os
import tempfile
import unittest
import numpy as np
from pathlib import Path

from dynamic_aligner import (
    align_sentences_with_audio,
    AcousticDegradationError,
    are_tokens_plausible,
    detect_voice_onset,
    calibrate_aligned_sentences_pcm,
)
from quality_gate import check_acoustic_lead_silence


class GrillRemediationTests(unittest.TestCase):
    def test_empty_acoustic_words_raises_degradation_error(self):
        """Defect 2: Dynamic aligner must fail fast with AcousticDegradationError when words is empty."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ac_path = root / "empty_acoustic.json"
            an_path = root / "analysis.json"
            out_path = root / "aligned.json"

            ac_path.write_text(json.dumps({"words": []}), encoding="utf-8")
            an_path.write_text(json.dumps([{"id": "s-1", "text": "Hello world."}]), encoding="utf-8")

            with self.assertRaises(AcousticDegradationError):
                align_sentences_with_audio(str(ac_path), str(an_path), str(out_path))

    def test_are_tokens_plausible_phonetic_and_numeric(self):
        """Test phonetic similarity and number word substitutions."""
        self.assertTrue(are_tokens_plausible(["Bill", "Stiritz"], ["Bill", "Sturrits"]))
        self.assertTrue(are_tokens_plausible(["Nineteen"], ["19"]))
        self.assertTrue(are_tokens_plausible(["twenty", "four"], ["24"]))
        self.assertFalse(are_tokens_plausible(["completely", "unrelated"], ["apples", "bananas"]))

    def test_backward_token_inspection_recovers_prefix_word_spans(self):
        """Defect 1: Backward token inspection recovers proper noun prefix timestamps instead of 10ms squishing."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ac_path = root / "acoustic.json"
            an_path = root / "analysis.json"
            out_path = root / "aligned.json"

            # Speaker said "Bill Sturrits had arrived"
            ac_words = [
                {"word": "Bill", "start": 1.0, "end": 1.3},
                {"word": "Sturrits", "start": 1.35, "end": 1.8},
                {"word": "had", "start": 1.9, "end": 2.1},
                {"word": "arrived", "start": 2.15, "end": 2.6},
            ]
            ac_path.write_text(json.dumps({"words": ac_words}), encoding="utf-8")
            an_path.write_text(json.dumps([{"id": "s-1", "text": "Bill Stiritz had arrived."}]), encoding="utf-8")

            results = align_sentences_with_audio(str(ac_path), str(an_path), str(out_path))
            self.assertEqual(len(results), 1)
            item = results[0]

            self.assertTrue(item.get("has_audio_match"))
            spans = item.get("word_spans", [])
            self.assertEqual(len(spans), 4)

            # Bill and Stiritz must have real acoustic durations (> 0.2s), not squished into 0.02s
            bill_span = spans[0]
            stiritz_span = spans[1]
            self.assertAlmostEqual(bill_span["start"], 1.0, delta=0.05)
            self.assertAlmostEqual(bill_span["end"], 1.3, delta=0.05)
            self.assertAlmostEqual(stiritz_span["start"], 1.35, delta=0.05)
            self.assertAlmostEqual(stiritz_span["end"], 1.8, delta=0.05)

            # Sentence start must encompass prefix words
            self.assertAlmostEqual(item["start"], 1.0, delta=0.05)

    def test_backward_token_inspection_with_numeric_variant(self):
        """Defect 1: Number word variation ('Nineteen' vs '19') properly recovered."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ac_path = root / "acoustic.json"
            an_path = root / "analysis.json"
            out_path = root / "aligned.json"

            ac_words = [
                {"word": "19", "start": 3.0, "end": 3.5},
                {"word": "people", "start": 3.6, "end": 3.9},
                {"word": "attended", "start": 4.0, "end": 4.5},
            ]
            ac_path.write_text(json.dumps({"words": ac_words}), encoding="utf-8")
            an_path.write_text(json.dumps([{"id": "s-1", "text": "Nineteen people attended."}]), encoding="utf-8")

            results = align_sentences_with_audio(str(ac_path), str(an_path), str(out_path))
            item = results[0]
            spans = item.get("word_spans", [])

            self.assertEqual(spans[0]["word"], "Nineteen")
            self.assertAlmostEqual(spans[0]["start"], 3.0, delta=0.05)
            self.assertAlmostEqual(spans[0]["end"], 3.5, delta=0.05)
            self.assertAlmostEqual(item["start"], 3.0, delta=0.05)

    def test_pcm_voice_onset_detection_and_calibration(self):
        """Defect 1 & 3: 16kHz PCM RMS voice onset detection accurately finds onset and calibrates sentence start."""
        sr = 16000
        # 0.5s silence + 0.5s 440Hz sine wave tone
        silence = np.zeros(int(sr * 0.5), dtype=np.int16)
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
        tone = (np.sin(2 * np.pi * 440 * t) * 15000).astype(np.int16)
        pcm = np.concatenate([silence, tone])

        onset = detect_voice_onset(pcm, 0.0, 1.0, sr=sr)
        self.assertAlmostEqual(onset, 0.50, delta=0.03)

        # Calibrate aligned sentence starting at 0.0 with onset at 0.50 -> new_st should be 0.50 - 0.06 = 0.44
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            raw_pcm_path = root / "test_audio.pcm"
            wav_path = root / "test_audio.wav"
            # Write WAV file using standard wave module
            import wave
            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(pcm.tobytes())

            sentences = [{
                "id": "s-1",
                "text": "Test tone.",
                "has_audio_match": True,
                "start": 0.0,
                "end": 1.0,
                "raw_start": 0.0,
                "raw_end": 1.0,
                "word_spans": [{"word": "Test", "start": 0.0, "end": 0.5}, {"word": "tone.", "start": 0.5, "end": 1.0}]
            }]

            calibrated = calibrate_aligned_sentences_pcm(sentences, str(wav_path), headroom=0.06)
            self.assertAlmostEqual(calibrated[0]["start"], 0.44, delta=0.04)
            self.assertAlmostEqual(calibrated[0]["word_spans"][0]["start"], 0.44, delta=0.04)

    def test_quality_gate_acoustic_lead_silence_validation(self):
        """Defect 3: Quality gate rejects un-calibrated lead silence exceeding 0.10s tolerance."""
        sr = 16000
        silence = np.zeros(int(sr * 0.5), dtype=np.int16)
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
        tone = (np.sin(2 * np.pi * 440 * t) * 15000).astype(np.int16)
        pcm = np.concatenate([silence, tone])

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            wav_path = root / "test_audio.wav"
            import wave
            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(pcm.tobytes())

            # Un-calibrated sentence: starts at 0.0s, voice starts at 0.50s (lead = 0.50s > 0.10s) -> FAIL
            uncalibrated = [{"has_audio_match": True, "start": 0.0, "end": 1.0}]
            fail_res = check_acoustic_lead_silence(uncalibrated, str(wav_path), max_lead=0.10)
            self.assertEqual(fail_res["status"], "failed")
            self.assertGreater(fail_res["mean_lead"], 0.40)

            # Calibrated sentence: starts at 0.44s, voice starts at 0.50s (lead = 0.06s <= 0.10s) -> PASS
            calibrated = [{"has_audio_match": True, "start": 0.44, "end": 1.0}]
            pass_res = check_acoustic_lead_silence(calibrated, str(wav_path), max_lead=0.10)
            self.assertEqual(pass_res["status"], "passed")
            self.assertLessEqual(pass_res["mean_lead"], 0.10)


if __name__ == "__main__":
    unittest.main()
