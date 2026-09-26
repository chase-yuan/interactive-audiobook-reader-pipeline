"""Agy adapter for one chapter of linguistic analysis.

Inputs are passed by the coordinator through READER_* environment variables.
The worker returns only the contract JSON and never edits the source book.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

from artifact_io import atomic_write_json


PROMPT_PATH = Path(__file__).with_name("LINGUISTIC_ANALYSIS_PROMPT.md")
CHUNK_SIZE = 50


def _json_from_output(text: str) -> Any:
    cleaned = text.strip()
    # 1. Extract from markdown code fences if present
    if "```" in cleaned:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            cleaned = match.group(1).strip()
        else:
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned).strip()

    # 2. Try direct parse
    try:
        data = json.loads(cleaned)
        # Preserve a successfully parsed non-list value so the caller can emit
        # the precise contract error instead of misreporting valid JSON as a
        # parse failure after its repair fallbacks are exhausted.
        if isinstance(data, list):
            return data
        return data
    except json.JSONDecodeError:
        pass

    # 3. Try regex array slice
    array_match = re.search(r"(\[\s*\{[\s\S]*\}\s*\])", cleaned)
    if array_match:
        try:
            return json.loads(array_match.group(1))
        except json.JSONDecodeError:
            cleaned = array_match.group(1)

    # 4. Repair common JSON errors (missing commas between objects, trailing commas)
    fixed = re.sub(r"\}\s*\{", "},{", cleaned)
    fixed = re.sub(r",\s*(\]|\})", r"\1", fixed)
    try:
        data = json.loads(fixed)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass

    # 5. Extract individual JSON objects by scanning curly brace depth
    results = []
    brace_depth = 0
    start_idx = None
    in_string = False
    escape = False
    for i, ch in enumerate(cleaned):
        if ch == '"' and not escape:
            in_string = not in_string
        elif ch == '\\' and in_string:
            escape = not escape
            continue
        elif not in_string:
            if ch == '{':
                if brace_depth == 0:
                    start_idx = i
                brace_depth += 1
            elif ch == '}':
                brace_depth -= 1
                if brace_depth == 0 and start_idx is not None:
                    obj_str = cleaned[start_idx:i + 1]
                    obj_fixed = re.sub(r",\s*\}", "}", obj_str)
                    try:
                        obj = json.loads(obj_fixed)
                        if isinstance(obj, dict) and "id" in obj:
                            results.append(obj)
                    except json.JSONDecodeError:
                        pass
                    start_idx = None
        escape = False
    if results:
        return results

    raise json.JSONDecodeError("Failed to parse valid JSON from output", text, 0)


def chunk_sentences(sentences: list[dict], chunk_size: int = CHUNK_SIZE) -> list[list[dict]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    return [sentences[i:i + chunk_size] for i in range(0, len(sentences), chunk_size)]


def build_batch_prompt(base_prompt: str, batch: list[dict], batch_idx: int, total_batches: int) -> str:
    batch_json = json.dumps(batch, ensure_ascii=False, indent=2)
    return (
        f"{base_prompt.strip()}\n\n"
        f"Input canonical records (batch {batch_idx + 1} of {total_batches}, {len(batch)} items):\n"
        f"```json\n{batch_json}\n```\n\n"
        "Return valid JSON only (a JSON array containing the analyzed objects for this specific batch), "
        "preserving every id, text, and order."
    )


def verify_analysis(data: Any, canonical_data: list[dict]) -> None:
    if not isinstance(data, list):
        raise RuntimeError("analysis output must be a list")
    if len(data) != len(canonical_data):
        raise RuntimeError(
            f"analysis record count mismatch: got {len(data)}, expected {len(canonical_data)}"
        )
    canonical_ids = [item.get("id") for item in canonical_data]
    output_ids = [item.get("id") for item in data]
    if output_ids != canonical_ids:
        raise RuntimeError("analysis output IDs/order differ from canonical input")
    for item, source in zip(data, canonical_data):
        item_id = item.get("id")
        if item.get("text") != source.get("text"):
            raise RuntimeError(f"text mismatch for record {item_id}")
        trans = item.get("trans")
        if not isinstance(trans, str) or not trans.strip():
            raise RuntimeError(f"missing or empty translation for record {item_id}")
        vocab = item.get("vocab")
        if not isinstance(vocab, list):
            raise RuntimeError(f"vocab must be a list for record {item_id}")
        for entry in vocab:
            if not isinstance(entry, dict) or not all(
                isinstance(entry.get(k), str) and entry.get(k).strip()
                for k in ("word", "pos", "def")
            ):
                raise RuntimeError(f"malformed vocabulary item in record {item_id}")


def _process_single_batch(batch_idx: int, batch: list[dict], base_prompt: str, total_batches: int,
                          cwd: Path, timeout: int, max_batch_attempts: int) -> list[dict]:
    prompt = build_batch_prompt(base_prompt, batch, batch_idx, total_batches)
    last_error = ""

    default_model = os.getenv("READER_AGY_MODEL", "gemini-3.8-flash-high")
    fallback_models = [default_model]
    for alt in ("gemini-3.7-flash-high", "gemini-3.8-flash-medium"):
        if alt not in fallback_models:
            fallback_models.append(alt)

    for attempt in range(1, max_batch_attempts + 1):
        model_name = fallback_models[(attempt - 1) % len(fallback_models)]
        base_cmd = ["agy"]
        if model_name:
            base_cmd.extend(["--model", model_name])

        try:
            completed = subprocess.run(
                base_cmd + ["--output-format", "text", "--print-timeout", "1h", "--print", prompt],
                cwd=str(cwd),
                text=True,
                capture_output=True,
                timeout=timeout,
            )
            if completed.returncode != 0:
                last_error = (completed.stderr or completed.stdout or "agy failed")[-4000:]
                is_quota = "RESOURCE_EXHAUSTED" in last_error or "429" in last_error
                wait_sec = 10 if is_quota else min(2 * attempt, 10)
                time.sleep(wait_sec)
                continue

            batch_result = _json_from_output(completed.stdout)
            if not isinstance(batch_result, list):
                last_error = "agy output must be a JSON list"
                time.sleep(1)
                continue

            returned_map = {
                item.get("id"): item
                for item in batch_result
                if isinstance(item, dict) and "id" in item
            }
            missing_items = [item for item in batch if item["id"] not in returned_map]

            # Auto-heal missing sentences via a targeted sub-query
            if missing_items and len(missing_items) <= 10:
                sub_prompt = build_batch_prompt(base_prompt, missing_items, 0, 1)
                try:
                    sub_completed = subprocess.run(
                        base_cmd + ["--output-format", "text", "--print-timeout", "1h", "--print", sub_prompt],
                        cwd=str(cwd),
                        text=True,
                        capture_output=True,
                        timeout=timeout,
                    )
                    if sub_completed.returncode == 0:
                        sub_result = _json_from_output(sub_completed.stdout)
                        if isinstance(sub_result, list):
                            for s_item in sub_result:
                                if isinstance(s_item, dict) and "id" in s_item:
                                    returned_map[s_item["id"]] = s_item
                except Exception:
                    pass
                missing_items = [item for item in batch if item["id"] not in returned_map]

            if missing_items:
                last_error = (
                    f"agy returned {len(returned_map)} items, expected {len(batch)}; "
                    f"missed {len(missing_items)} items: {[m['id'] for m in missing_items]}"
                )
                time.sleep(1)
                continue

            ordered_batch = [returned_map[item["id"]] for item in batch]
            verify_analysis(ordered_batch, batch)
            return ordered_batch
        except (subprocess.TimeoutExpired, json.JSONDecodeError, RuntimeError) as exc:
            last_error = str(exc)
            time.sleep(1)

    raise RuntimeError(
        f"agy failed on batch {batch_idx + 1}/{total_batches} after {max_batch_attempts} attempts: {last_error}"
    )


def process_canonical_sentences(
    canonical_data: list[dict],
    base_prompt: str,
    cwd: Path,
    chunk_size: int = CHUNK_SIZE,
    timeout: int = 3700,
    max_batch_attempts: int = 3,
    max_workers: int = 1,
) -> list[dict]:
    chunks = chunk_sentences(canonical_data, chunk_size=chunk_size)
    if not chunks:
        return []

    if max_workers <= 0:
        raise ValueError("max_workers must be positive")

    master_list: list[dict] = []
    with ThreadPoolExecutor(max_workers=min(max_workers, len(chunks))) as executor:
        futures = [
            executor.submit(
                _process_single_batch,
                batch_idx, batch, base_prompt, len(chunks), cwd, timeout, max_batch_attempts
            )
            for batch_idx, batch in enumerate(chunks)
        ]
        for f in futures:
            master_list.extend(f.result())

    verify_analysis(master_list, canonical_data)
    return master_list


def main(environ: dict[str, str] | None = None) -> int:
    env = os.environ if environ is None else environ
    canonical_path = Path(env["READER_CANONICAL_PATH"])
    output_path = Path(env["READER_OUTPUT_PATH"])

    canonical_data = json.loads(canonical_path.read_text(encoding="utf-8"))
    if not isinstance(canonical_data, list):
        raise RuntimeError(f"canonical data at {canonical_path} must be a JSON list")

    base_prompt = PROMPT_PATH.read_text(encoding="utf-8")

    analyzed_data = process_canonical_sentences(
        canonical_data=canonical_data,
        base_prompt=base_prompt,
        cwd=canonical_path.parent,
        max_workers=int(env.get("READER_LINGUISTIC_MAX_WORKERS", "1")),
    )

    atomic_write_json(output_path, analyzed_data)
    print(f"agy linguistic analysis written: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
