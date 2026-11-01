"""
Module: cloud_acoustic_engine.py
Description: High-Throughput Cloud & Hybrid Acoustic Extraction Engine.
Provides ultra-fast Whisper transcription via Groq Cloud API (~335x real-time),
with automatic adaptive FFmpeg downsampling (32k mono), multi-chapter parallel dispatch,
exponential-backoff retry on rate limits, and seamless fallback to Apple Silicon MLX Whisper.
"""

import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import requests

from artifact_io import atomic_write_json

GROQ_TRANSCRIPTION_ENDPOINT = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_GROQ_MODEL = "whisper-large-v3-turbo"
MAX_GROQ_PAYLOAD_BYTES = 24 * 1024 * 1024  # 24MB safe buffer for Groq 25MB multipart limit
ACOUSTIC_PROFILE_VERSION = 2


def resolve_groq_api_keys(api_key: Optional[str] = None) -> List[str]:
    """
    Resolve all available Groq API keys for pooling with standard precedence:
    1. Explicit api_key argument
    2. GROQ_API_KEY or GROQ_API_KEYS (comma-separated) environment variables
    3. User config file (~/.config/groq/keys.json or ~/.config/groq/key)
    4. Gemini config directory (~/.gemini/groq_key)
    Returns a deduplicated list of valid keys.
    """
    keys = []
    if api_key and str(api_key).strip():
        keys.append(str(api_key).strip())

    env_single = os.environ.get("GROQ_API_KEY")
    if env_single and env_single.strip() not in keys:
        keys.append(env_single.strip())

    env_multi = os.environ.get("GROQ_API_KEYS")
    if env_multi:
        for k in env_multi.split(","):
            k = k.strip()
            if k.startswith("gsk_") and k not in keys:
                keys.append(k)

    keys_json_file = Path.home() / ".config" / "groq" / "keys.json"
    if keys_json_file.is_file():
        try:
            data = json.loads(keys_json_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                for k in data:
                    if isinstance(k, str) and k.startswith("gsk_") and k not in keys:
                        keys.append(k.strip())
        except Exception:
            pass

    for cand in [Path.home() / ".config" / "groq" / "key", Path.home() / ".gemini" / "groq_key"]:
        if cand.is_file():
            try:
                c = cand.read_text(encoding="utf-8").strip()
                if c.startswith("gsk_") and c not in keys:
                    keys.append(c)
            except Exception:
                pass

    return keys


def resolve_groq_api_key(api_key: Optional[str] = None) -> Optional[str]:
    """
    Resolve primary Groq API key.
    """
    keys = resolve_groq_api_keys(api_key)
    return keys[0] if keys else None


def compress_audio_if_needed(
    audio_path: Union[str, Path],
    max_bytes: int = MAX_GROQ_PAYLOAD_BYTES,
    bitrate: str = "32k",
    sample_rate: int = 16000,
) -> Tuple[Path, bool]:
    """
    Check audio file size and compression requirements.
    If the file size exceeds max_bytes, or if it is uncompressed/high-bitrate,
    transcode it to mono 16kHz 32kbps MP3 via FFmpeg.
    Returns (path_to_use, is_temporary_file).
    """
    src = Path(audio_path).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Source audio file not found: {audio_path}")

    file_size = src.stat().st_size
    # If the file is already small (e.g. <= 20MB) and is an mp3, we can send directly
    if file_size <= max_bytes and src.suffix.lower() == ".mp3" and file_size <= 20 * 1024 * 1024:
        return src, False

    # Need compression/transcoding
    tmp_fd, tmp_path_str = tempfile.mkstemp(prefix="groq_whisper_", suffix=".mp3")
    os.close(tmp_fd)
    tmp_path = Path(tmp_path_str)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-vn",
        "-ac",
        "1",
        "-ar",
        str(sample_rate),
        "-b:a",
        bitrate,
        str(tmp_path),
    ]

    try:
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        if tmp_path.exists():
            tmp_path.unlink()
        # If ffmpeg is missing but file is under hard limit, fall back to original
        if file_size <= max_bytes:
            print(f"⚠️ [CLOUD ACOUSTIC] FFmpeg transcode failed or missing, uploading original ({file_size / 1024 / 1024:.1f} MB)...", flush=True)
            return src, False
        raise RuntimeError(
            f"Audio file '{src.name}' ({file_size / 1024 / 1024:.1f} MB) exceeds Groq limit ({max_bytes / 1024 / 1024} MB) "
            f"and FFmpeg compression failed: {exc}"
        ) from exc

    return tmp_path, True


def run_groq_acoustic_extraction(
    audio_path: Union[str, Path],
    output_json_path: Union[str, Path],
    *,
    api_key: Optional[Union[str, List[str]]] = None,
    model: str = DEFAULT_GROQ_MODEL,
    language: str = "en",
    prompt: Optional[str] = None,
    timeout: int = 240,
    max_retries: int = 4,
    session: Optional[requests.Session] = None,
) -> Dict[str, Any]:
    """
    Extract word-level acoustic timestamps using Groq Whisper Cloud API.
    Guarantees parity with the standard acoustic artifact schema.
    Supports multi-key pool rotation on rate limits (429).
    """
    if isinstance(api_key, list):
        keys_pool = [k for k in api_key if k and str(k).strip()]
    elif isinstance(api_key, str) and api_key.strip():
        keys_pool = [api_key.strip()]
    else:
        keys_pool = resolve_groq_api_keys()

    if not keys_pool:
        raise ValueError(
            "Groq API key not found. Please provide api_key argument, set GROQ_API_KEY environment variable, "
            "or save key to ~/.config/groq/key or ~/.config/groq/keys.json"
        )

    src_path = Path(audio_path).resolve()
    if not src_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    # Compute source audio SHA-256 ground truth
    source_sha256 = hashlib.sha256(src_path.read_bytes()).hexdigest()

    # Pre-compress if needed
    upload_path, is_temp = compress_audio_if_needed(src_path)
    start_time = time.time()

    data = [
        ("model", model),
        ("response_format", "verbose_json"),
        ("timestamp_granularities[]", "word"),
        ("timestamp_granularities[]", "segment"),
        ("language", language),
    ]
    if prompt:
        data.append(("prompt", prompt))

    http_client = session or requests

    last_error = None
    current_key_idx = 0
    consecutive_429 = 0
    total_attempts = max(max_retries, len(keys_pool) * 2)

    try:
        for attempt in range(1, total_attempts + 1):
            active_key = keys_pool[current_key_idx % len(keys_pool)]
            headers = {
                "Authorization": f"Bearer {active_key}",
                "User-Agent": "curl/7.68.0",
            }
            try:
                with open(upload_path, "rb") as audio_file:
                    files = {"file": (upload_path.name, audio_file, "audio/mpeg")}
                    resp = http_client.post(
                        GROQ_TRANSCRIPTION_ENDPOINT,
                        headers=headers,
                        data=data,
                        files=files,
                        timeout=timeout,
                    )

                if resp.status_code == 200:
                    raw_result = resp.json()
                    break
                elif resp.status_code == 429:
                    consecutive_429 += 1
                    if len(keys_pool) > 1 and consecutive_429 < len(keys_pool):
                        current_key_idx = (current_key_idx + 1) % len(keys_pool)
                        next_key_masked = keys_pool[current_key_idx % len(keys_pool)][:10] + "..."
                        print(f"⚠️ [GROQ 429] Rate limit hit on {src_path.name}. Rotating to next key {next_key_masked} in pool...", flush=True)
                        time.sleep(0.5)
                        continue
                    else:
                        consecutive_429 = 0
                        wait_sec = 2.0 * (2 ** min(attempt - 1, 4))
                        if len(keys_pool) > 1:
                            current_key_idx = (current_key_idx + 1) % len(keys_pool)
                        print(f"⚠️ [GROQ 429] Rate limit hit on {src_path.name}. Retrying in {wait_sec:.1f}s (Attempt {attempt}/{total_attempts})...", flush=True)
                        time.sleep(wait_sec)
                        continue
                elif resp.status_code >= 500:
                    wait_sec = 2.0 * attempt
                    print(f"⚠️ [GROQ {resp.status_code}] Server error on {src_path.name}. Retrying in {wait_sec:.1f}s...", flush=True)
                    time.sleep(wait_sec)
                    continue
                else:
                    error_text = resp.text[:500]
                    raise RuntimeError(f"Groq API returned HTTP {resp.status_code}: {error_text}")

            except (requests.exceptions.RequestException, TimeoutError) as exc:
                last_error = exc
                if attempt < total_attempts:
                    wait_sec = 2.0 * attempt
                    print(f"⚠️ [NETWORK ERROR] {exc} on {src_path.name}. Retrying in {wait_sec:.1f}s...", flush=True)
                    time.sleep(wait_sec)
                    continue
                raise
        else:
            raise RuntimeError(f"Failed to transcribe {src_path.name} after {total_attempts} attempts. Last error: {last_error}")

    finally:
        if is_temp and upload_path.exists():
            try:
                upload_path.unlink()
            except OSError:
                pass

    # Normalize response into standard pipeline acoustic schema
    segments_raw = raw_result.get("segments") or []
    segments_list = []
    for seg in segments_raw:
        if isinstance(seg, dict):
            segments_list.append({
                "id": seg.get("id"),
                "start": round(float(seg.get("start", 0.0)), 2),
                "end": round(float(seg.get("end", 0.0)), 2),
                "text": seg.get("text", "")
            })

    words_list = []
    dropped_zero_duration_words = 0

    # Words can be inside root "words" or inside each segment
    raw_words = raw_result.get("words") or []
    if not raw_words and segments_raw:
        for s in segments_raw:
            if isinstance(s, dict):
                raw_words.extend(s.get("words") or [])

    for w in raw_words:
        word_text = w.get("word")
        if not isinstance(word_text, str) or not word_text.strip():
            continue
        start_val = w.get("start")
        end_val = w.get("end")
        if start_val is None or end_val is None:
            continue
        try:
            start_f = float(start_val)
            end_f = float(end_val)
        except (ValueError, TypeError):
            continue

        if not math.isfinite(start_f) or not math.isfinite(end_f) or end_f < start_f:
            continue
        if end_f == start_f:
            dropped_zero_duration_words += 1
            continue

        prob = w.get("probability")
        prob_val = round(float(prob), 4) if prob is not None and math.isfinite(float(prob)) else 0.9500

        words_list.append({
            "word": word_text,
            "start": round(start_f, 2),
            "end": round(end_f, 2),
            "probability": prob_val,
        })

    output_data = {
        "schema_version": 2,
        "acoustic_profile_version": ACOUSTIC_PROFILE_VERSION,
        "model": f"groq/{model}",
        "source_audio_sha256": source_sha256,
        "transcription_options": {
            "provider": "groq",
            "model": model,
            "language": language,
            "condition_on_previous_text": False,
        },
        "word_timestamps": True,
        "dropped_zero_duration_words": dropped_zero_duration_words,
        "segments": segments_list,
        "words": words_list,
    }

    atomic_write_json(output_json_path, output_data)
    elapsed = round(time.time() - start_time, 2)
    print(f"⚡ [GROQ CLOUD] Acoustic extraction complete in {elapsed}s! Extracted {len(words_list)} words -> {output_json_path}", flush=True)
    return output_data


def transcribe_chapters_parallel_groq(
    chapter_tasks: List[Dict[str, Any]],
    *,
    api_key: Optional[Union[str, List[str]]] = None,
    max_workers: int = 5,
    model: str = DEFAULT_GROQ_MODEL,
    language: str = "en",
) -> List[Dict[str, Any]]:
    """
    Concurrently transcribe multiple chapters using Groq Whisper.
    Distributes chapters across the pool of available Groq API keys.
    Each task dict must have:
      - 'audio_path': Path to input audio
      - 'output_json_path': Path for output acoustic words JSON
      - 'label': Optional human readable label (e.g. 'Chapter 01')
    """
    if isinstance(api_key, list):
        keys_pool = [k for k in api_key if k and str(k).strip()]
    elif isinstance(api_key, str) and api_key.strip():
        keys_pool = [api_key.strip()]
    else:
        keys_pool = resolve_groq_api_keys()

    if not keys_pool:
        raise ValueError("Cannot run parallel Groq transcription: No API key available.")

    results = [None] * len(chapter_tasks)
    workers = max(1, min(max_workers, len(chapter_tasks)))
    print(f"\n🚀 [CLOUD ACOUSTIC] Launching {workers} concurrent Groq Whisper workers for {len(chapter_tasks)} chapters (Key pool size: {len(keys_pool)})...", flush=True)

    session = requests.Session()

    def _worker(idx: int, task: Dict[str, Any]):
        audio = task["audio_path"]
        out_json = task["output_json_path"]
        label = task.get("label", Path(audio).name)
        worker_keys = keys_pool[idx % len(keys_pool):] + keys_pool[:idx % len(keys_pool)]
        print(f"  ▶️ [DISPATCH] {label} -> Groq ({model}, key #{idx % len(keys_pool) + 1})...", flush=True)
        res = run_groq_acoustic_extraction(
            audio_path=audio,
            output_json_path=out_json,
            api_key=worker_keys,
            model=model,
            language=language,
            session=session,
        )
        return idx, res

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(_worker, i, t): t for i, t in enumerate(chapter_tasks)}
        for future in as_completed(futures):
            idx, res = future.result()
            results[idx] = res

    print(f"🏆 [CLOUD ACOUSTIC] All {len(chapter_tasks)} chapters successfully transcribed in cloud.\n", flush=True)
    return results


def run_acoustic_extraction(
    audio_path: Union[str, Path],
    output_json_path: Union[str, Path],
    *,
    provider: str = "auto",
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    language: str = "en",
) -> Dict[str, Any]:
    """
    Universal dispatcher for acoustic word timestamp extraction:
    - If provider == 'groq': force Groq cloud transcription.
    - If provider == 'mlx': force local MLX Whisper.
    - If provider == 'auto': prefer Groq if GROQ_API_KEY is available; fall back to MLX on failure or missing key.
    """
    resolved_key = resolve_groq_api_key(api_key)
    groq_available = bool(resolved_key)

    if provider == "groq" or (provider == "auto" and groq_available):
        groq_model = model or DEFAULT_GROQ_MODEL
        try:
            return run_groq_acoustic_extraction(
                audio_path=audio_path,
                output_json_path=output_json_path,
                api_key=resolved_key,
                model=groq_model,
                language=language,
            )
        except Exception as exc:
            if provider == "groq":
                raise
            print(f"⚠️ [CLOUD ACOUSTIC] Groq extraction encountered error ({exc}). Falling back to local MLX Whisper...", flush=True)

    # Fallback to local Apple Silicon MLX Whisper
    from acoustic_whisper import run_mlx_acoustic_extraction
    mlx_model = model or "mlx-community/whisper-large-v3-turbo"
    return run_mlx_acoustic_extraction(
        audio_path=audio_path,
        output_json_path=output_json_path,
        model_name=mlx_model,
    )
