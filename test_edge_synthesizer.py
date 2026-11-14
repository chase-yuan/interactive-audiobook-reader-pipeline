"""
Unit test for Edge-TTS synthesizer adapter.
"""

import json
import tempfile
from pathlib import Path

from edge_synthesizer import synthesize_chapter, speed_to_edge_rate

def test_speed_to_edge_rate():
    assert speed_to_edge_rate(1.0) == "+0%"
    assert speed_to_edge_rate(1.15) == "+15%"
    assert speed_to_edge_rate(0.9) == "-10%"

def test_synthesize_chapter_edge():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        canonical = [
            {"id": "s-0", "elem_idx": 0, "tag": "h1", "text": "Critical Thinking", "is_heading": True},
            {"id": "s-1", "elem_idx": 1, "tag": "p", "text": "This is a test of the Edge neural synthesis adapter.", "is_heading": False},
        ]
        can_path = tmp_path / "canonical.json"
        can_path.write_text(json.dumps(canonical), encoding="utf-8")

        ana_path = tmp_path / "analysis.json"
        ana_path.write_text(json.dumps([
            {"id": "s-0", "trans": "批判性思维", "vocab": []},
            {"id": "s-1", "trans": "这是Edge神经语音合成适配器的测试。", "vocab": []},
        ]), encoding="utf-8")

        aligned_path = tmp_path / "aligned.json"
        audio_path = tmp_path / "audio.mp3"

        out_aligned, out_audio = synthesize_chapter(
            canonical_path=can_path,
            analysis_path=ana_path,
            aligned_output_path=aligned_path,
            audio_output_path=audio_path,
            voice="en-US-GuyNeural",
            speed=1.0,
        )

        assert out_audio.is_file()
        assert out_audio.stat().st_size > 5000
        assert out_aligned.is_file()

        aligned_data = json.loads(out_aligned.read_text(encoding="utf-8"))
        assert len(aligned_data) == 2
        assert aligned_data[0]["has_audio_match"] is True
        assert aligned_data[1]["has_audio_match"] is True
        assert len(aligned_data[1]["word_spans"]) > 5

        # Grill finding 6: Strict silence trimming and monotonic word span assertions
        assert aligned_data[0]["end"] < 1.2, f"Heading silence was not trimmed: end={aligned_data[0]['end']}"
        for s in aligned_data:
            spans = s.get("word_spans", [])
            for i in range(len(spans) - 1):
                assert spans[i]["end"] <= spans[i+1]["start"] + 0.001, (
                    f"Overlapping word spans detected: {spans[i]} vs {spans[i+1]}"
                )
            if spans:
                assert abs(spans[-1]["end"] - s["end"]) < 0.05, (
                    f"Sentence end mismatch with final word: span_end={spans[-1]['end']} vs sent_end={s['end']}"
                )
        print("\n[OK] Edge-TTS Synthesizer Adapter physically verified!")

if __name__ == "__main__":
    test_speed_to_edge_rate()
    test_synthesize_chapter_edge()
    print("ALL TESTS PASSED WITH EXIT CODE 0!")

