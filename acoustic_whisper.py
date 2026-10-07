"""
Module: acoustic_whisper.py
Description: Apple Silicon GPU-Accelerated MLX Whisper Word Timestamp Extractor.
"""

import hashlib
import json
import math
import time
import sys
from pathlib import Path
from artifact_io import atomic_write_json

ACOUSTIC_PROFILE_VERSION = 2
ACOUSTIC_TRANSCRIPTION_OPTIONS = {
    "condition_on_previous_text": False,
    "hallucination_silence_threshold": 2.0,
    "language": "en",
}


def run_mlx_acoustic_extraction(
    audio_path,
    output_json_path,
    model_name="mlx-community/whisper-large-v3-turbo",
    *,
    transcribe_fn=None,
    transcription_options=None,
):
    if transcribe_fn is None:
        import mlx_whisper
        transcribe_fn = mlx_whisper.transcribe
    
    options = dict(ACOUSTIC_TRANSCRIPTION_OPTIONS)
    if transcription_options:
        options.update(transcription_options)

    print(f"Starting MLX Whisper acoustic extraction on {audio_path} using {model_name}...")
    start_t = time.time()
    
    call_options = {k: v for k, v in options.items() if v is not None}
    result = transcribe_fn(
        audio_path,
        path_or_hf_repo=model_name,
        word_timestamps=True,
        verbose=False,
        **call_options,
    )
    
    words_list = []
    segments_list = []
    dropped_zero_duration_words = 0
    
    for seg in result.get("segments", []):
        segments_list.append({
            "id": seg.get("id"),
            "start": seg.get("start"),
            "end": seg.get("end"),
            "text": seg.get("text")
        })
        for w in seg.get("words", []):
            if not isinstance(w.get("word"), str) or not w.get("word").strip():
                raise ValueError("acoustic backend returned a word without text")
            if not isinstance(w.get("start"), (int, float)) or not isinstance(w.get("end"), (int, float)):
                raise ValueError("acoustic backend returned a word without timestamps")
            if not math.isfinite(float(w["start"])) or not math.isfinite(float(w["end"])) or float(w["end"]) < float(w["start"]):
                raise ValueError("acoustic backend returned an invalid word timestamp")
            if float(w["end"]) == float(w["start"]):
                # MLX can emit zero-duration boundary tokens. They cannot be
                # used for alignment, so discard and expose the count rather
                # than corrupting the artifact or aborting the whole chapter.
                dropped_zero_duration_words += 1
                continue
            words_list.append({
                "word": w.get("word"),
                "start": round(w.get("start", 0.0), 2),
                "end": round(w.get("end", 0.0), 2),
                "probability": round(w.get("probability", 0.0), 4)
            })
            
    output_data = {
        "schema_version": 2,
        "acoustic_profile_version": ACOUSTIC_PROFILE_VERSION,
        "model": model_name,
        "source_audio_sha256": hashlib.sha256(Path(audio_path).read_bytes()).hexdigest() if Path(audio_path).is_file() else None,
        "transcription_options": ACOUSTIC_TRANSCRIPTION_OPTIONS,
        "word_timestamps": True,
        "dropped_zero_duration_words": dropped_zero_duration_words,
        "segments": segments_list,
        "words": words_list
    }
    
    atomic_write_json(output_json_path, output_data)
        
    elapsed = round(time.time() - start_t, 2)
    print(f"Acoustic extraction complete in {elapsed}s! Total words extracted: {len(words_list)} -> {output_json_path}")
    return output_data

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        model = sys.argv[3] if len(sys.argv) >= 4 else "mlx-community/whisper-large-v3-turbo"
        run_mlx_acoustic_extraction(sys.argv[1], sys.argv[2], model)
    else:
        print("Usage: python3 acoustic_whisper.py <audio_path> <output_json_path> [model_name]")
