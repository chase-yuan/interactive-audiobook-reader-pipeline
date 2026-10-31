#!/usr/bin/env python3
"""Sentence Metrics & Extreme Payload Scanner.

Automated static analysis engine that identifies extreme sentence scenarios:
1. Lexical volume: Words per sentence (p50, p90, p99, max).
2. Translation payload: Chinese characters per sentence.
3. Acoustic duration: Audio seconds per sentence.
4. UI Stress: High translation combined with high vocabulary density.

Prevents UI layout blowouts, screen takeovers, and acoustic drift across
existing refurbished books and future pipeline ingestion.
"""

import argparse
import glob
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Severity Threshold Contracts
EXTREME_WORD_THRESHOLD = 70       # Author stream-of-consciousness / complex periodic sentences
HIGH_WORD_THRESHOLD = 45          # Heavy sentence requiring cognitive focus
EXTREME_CHAR_THRESHOLD = 180      # Multi-line Chinese translation payload
HIGH_CHAR_THRESHOLD = 120         # Heavy Chinese translation payload
EXTREME_DURATION_THRESHOLD = 35.0 # Seconds of continuous speech
HIGH_DURATION_THRESHOLD = 22.0    # Seconds of speech
HIGH_VOCAB_THRESHOLD = 4          # Compound inspection items


def compute_sentence_metric(s: Dict[str, Any], chapter: str = "") -> Dict[str, Any]:
    """Calculate single sentence dimensional metrics and severity."""
    text = s.get("text", "") or ""
    trans = s.get("trans", "") or ""
    words = len(text.split())
    chars = len(trans)
    
    raw_s = s.get("raw_start")
    start = raw_s if raw_s is not None else s.get("start")
    raw_e = s.get("raw_end")
    end = raw_e if raw_e is not None else s.get("end")
    dur = round(max(0.0, float(end) - float(start)), 2) if (start is not None and end is not None) else 0.0
    
    vocab = s.get("vocab", [])
    vocab_cnt = len(vocab) if isinstance(vocab, list) else 0

    is_extreme = (words >= EXTREME_WORD_THRESHOLD or 
                  chars >= EXTREME_CHAR_THRESHOLD or 
                  dur >= EXTREME_DURATION_THRESHOLD)
    
    is_high = ((words >= HIGH_WORD_THRESHOLD or 
                chars >= HIGH_CHAR_THRESHOLD or 
                dur >= HIGH_DURATION_THRESHOLD) and not is_extreme)

    # UI Stress indicator: long translation + high vocabulary entries
    ui_stress = (chars >= HIGH_CHAR_THRESHOLD and vocab_cnt >= HIGH_VOCAB_THRESHOLD)

    level = "EXTREME" if is_extreme else ("HIGH" if is_high else "NORMAL")

    return {
        "chapter": chapter,
        "id": s.get("id", ""),
        "words": words,
        "chars": chars,
        "duration": dur,
        "vocab_count": vocab_cnt,
        "level": level,
        "ui_stress": ui_stress,
        "text": text,
        "trans": trans,
    }


def _percentile(arr: List[float], q: float) -> float:
    if not arr:
        return 0.0
    idx = int(math.ceil(q * len(arr))) - 1
    idx = max(0, min(idx, len(arr) - 1))
    return arr[idx]


def profile_sentences(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute aggregate statistical distribution and identify outliers."""
    if not records:
        return {
            "total": 0,
            "extreme_count": 0,
            "high_count": 0,
            "ui_stress_count": 0,
            "word_stats": {"p50": 0, "p90": 0, "p99": 0, "max": 0},
            "char_stats": {"p50": 0, "p90": 0, "p99": 0, "max": 0},
            "duration_stats": {"p50": 0.0, "p90": 0.0, "p99": 0.0, "max": 0.0},
            "outliers": [],
        }

    valid_records = [r for r in records if r["words"] > 0]
    words_sorted = sorted([r["words"] for r in valid_records])
    chars_sorted = sorted([r["chars"] for r in valid_records])
    durs_sorted = sorted([r["duration"] for r in valid_records if r["duration"] > 0])

    extreme_records = [r for r in valid_records if r["level"] == "EXTREME"]
    high_records = [r for r in valid_records if r["level"] == "HIGH"]
    stress_records = [r for r in valid_records if r["ui_stress"]]

    # Outliers: all extremes, plus top high records, sorted by words descending
    outliers = sorted(extreme_records, key=lambda x: (x["words"], x["chars"]), reverse=True)

    return {
        "total": len(valid_records),
        "extreme_count": len(extreme_records),
        "high_count": len(high_records),
        "ui_stress_count": len(stress_records),
        "word_stats": {
            "p50": int(_percentile(words_sorted, 0.5)),
            "p90": int(_percentile(words_sorted, 0.9)),
            "p99": int(_percentile(words_sorted, 0.99)),
            "max": words_sorted[-1] if words_sorted else 0,
        },
        "char_stats": {
            "p50": int(_percentile(chars_sorted, 0.5)),
            "p90": int(_percentile(chars_sorted, 0.9)),
            "p99": int(_percentile(chars_sorted, 0.99)),
            "max": chars_sorted[-1] if chars_sorted else 0,
        },
        "duration_stats": {
            "p50": round(_percentile(durs_sorted, 0.5), 1) if durs_sorted else 0.0,
            "p90": round(_percentile(durs_sorted, 0.9), 1) if durs_sorted else 0.0,
            "p99": round(_percentile(durs_sorted, 0.99), 1) if durs_sorted else 0.0,
            "max": round(durs_sorted[-1], 1) if durs_sorted else 0.0,
        },
        "outliers": outliers,
    }


def scan_book_dir(book_dir: Path) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Scan all aligned or canonical sentence JSONs in a book directory."""
    # Filter out intermediate, test, scratch, or backup JSONs
    is_not_scratch = lambda f: not re.search(r"(?:_test_|_test\.|\btest_|\bscratch_|\bbackup_|\bold_)", f.name, re.IGNORECASE)
    aligned_files = [f for f in sorted(book_dir.glob("*aligned*.json")) if is_not_scratch(f)]
    if not aligned_files:
        # Fallback to chapters/ch*.json or canonical
        aligned_files = [f for f in sorted(book_dir.glob("chapters/ch*.json")) if is_not_scratch(f)]
    if not aligned_files:
        aligned_files = [f for f in sorted(book_dir.glob("*canonical*.json")) if is_not_scratch(f)]

    all_records = []
    for f in aligned_files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                continue
            ch_label = f.stem
            for s in data:
                if isinstance(s, dict):
                    all_records.append(compute_sentence_metric(s, chapter=ch_label))
        except Exception:
            continue

    profile = profile_sentences(all_records)
    return profile, all_records


def print_cli_report(book_name: str, profile: Dict[str, Any], top_n: int = 5):
    """Render a clean terminal report for a book."""
    total = profile["total"]
    if total == 0:
        print(f"⚠️  {book_name}: No sentences found.")
        return

    ext = profile["extreme_count"]
    high = profile["high_count"]
    stress = profile["ui_stress_count"]
    ws = profile["word_stats"]
    cs = profile["char_stats"]
    ds = profile["duration_stats"]

    print("═" * 78)
    print(f" 📖  {book_name.upper()}")
    print("═" * 78)
    print(f" • Total Sentences:    {total:,}")
    print(f" • 🔴 Extreme Payload: {ext} ({ext / total * 100:.1f}%) [Words >= {EXTREME_WORD_THRESHOLD} | Chars >= {EXTREME_CHAR_THRESHOLD} | Dur >= {EXTREME_DURATION_THRESHOLD}s]")
    print(f" • 🟡 High Payload:    {high} ({high / total * 100:.1f}%) [Words >= {HIGH_WORD_THRESHOLD} | Chars >= {HIGH_CHAR_THRESHOLD} | Dur >= {HIGH_DURATION_THRESHOLD}s]")
    print(f" • ⚠️  UI Stress Risks: {stress} (Long Translation + >= {HIGH_VOCAB_THRESHOLD} Vocab entries)")
    print("-" * 78)
    print(" 📊 Statistical Distribution (Percentiles):")
    print(f"   - English Words:   p50={ws['p50']:2d}  |  p90={ws['p90']:2d}  |  p99={ws['p99']:2d}  |  Max={ws['max']:2d} words")
    print(f"   - Chinese Chars:   p50={cs['p50']:2d}  |  p90={cs['p90']:2d}  |  p99={cs['p99']:2d}  |  Max={cs['max']:2d} chars")
    print(f"   - Audio Duration:  p50={ds['p50']:4.1f}s|  p90={ds['p90']:4.1f}s|  p99={ds['p99']:4.1f}s|  Max={ds['max']:4.1f}s")
    
    outliers = profile.get("outliers", [])
    if outliers and top_n > 0:
        print("-" * 78)
        print(f" 🔍 Top {min(top_n, len(outliers))} Extreme Outliers:")
        for idx, item in enumerate(outliers[:top_n], start=1):
            ch = item["chapter"]
            sid = item["id"]
            w = item["words"]
            c = item["chars"]
            d = item["duration"]
            v = item["vocab_count"]
            print(f"   {idx}. [{ch} :: {sid}] — {w} words | {c} chars | {d}s | {v} vocab")
            en_preview = item["text"][:85].replace("\n", " ") + ("..." if len(item["text"]) > 85 else "")
            zh_preview = item["trans"][:85].replace("\n", " ") + ("..." if len(item["trans"]) > 85 else "")
            print(f"      EN: \"{en_preview}\"")
            print(f"      ZH: \"{zh_preview}\"")
    print("═" * 78 + "\n")


def scan_all_audible_library(audible_root: Path, top_n: int = 3):
    """Scan all books in the Audible production library and rank by extreme density."""
    books_dir = audible_root / "books"
    if not books_dir.exists():
        print(f"❌ Audible books directory not found: {books_dir}")
        return

    book_dirs = sorted([d for d in books_dir.iterdir() if d.is_dir()])
    summary = []

    print("\n" + "█" * 78)
    print("   🌐 AUDIBLE CENTRAL LIBRARY SENTENCE EXTREMES & UI PAYLOAD AUDIT")
    print("█" * 78 + "\n")

    for bd in book_dirs:
        # Check source book directories or chapter HTMLs
        profile, _ = scan_book_dir(bd)
        # If no json directly in bd, try matching in Sentence Analysis
        if profile["total"] == 0:
            obsidian_dir = Path("/Users/lindy/Vault/MyObsidian/English/Sentence Analysis")
            # fuzzy match
            matched = [od for od in obsidian_dir.iterdir() if od.is_dir() and bd.name.lower() in od.name.lower().replace(" ", "-")]
            if matched:
                profile, _ = scan_book_dir(matched[0])
            else:
                audiobook_dir = Path("/Users/lindy/Vault/audiobook")
                matched_ab = [ad for ad in audiobook_dir.iterdir() if ad.is_dir() and bd.name.lower() in ad.name.lower().replace(" ", "-")]
                if matched_ab:
                    profile, _ = scan_book_dir(matched_ab[0])

        if profile["total"] > 0:
            summary.append((bd.name, profile))
            print_cli_report(bd.name, profile, top_n=top_n)

    # Output Leaderboard
    if summary:
        print("\n" + "═" * 78)
        print(" 🏆 LIBRARY EXTREME SENTENCE LEADERBOARD (Sorted by Max Words)")
        print("═" * 78)
        print(f" {'Book ID':<35} | {'Total':>6} | {'Extreme':>7} | {'Max Words':>9} | {'Max Chars':>9} | {'Max Dur':>7}")
        print("-" * 78)
        for b_id, prof in sorted(summary, key=lambda x: x[1]["word_stats"]["max"], reverse=True):
            tot = prof["total"]
            ext = prof["extreme_count"]
            mw = prof["word_stats"]["max"]
            mc = prof["char_stats"]["max"]
            md = prof["duration_stats"]["max"]
            print(f" {b_id:<35} | {tot:>6,d} | {ext:>7d} | {mw:>9d} | {mc:>9d} | {md:>6.1f}s")
        print("═" * 78 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Audit books for extreme sentence lengths and UI risks.")
    parser.add_argument("book_dir", nargs="?", help="Path to a book directory")
    parser.add_argument("--all-audible", action="store_true", help="Scan all books in Audible central repository")
    parser.add_argument("--top", type=int, default=5, help="Number of outliers to print (default: 5)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    if args.all_audible:
        scan_all_audible_library(Path("/Users/lindy/Vault/Audible"), top_n=args.top)
        return

    target_dir = Path(args.book_dir or ".")
    if not target_dir.exists():
        print(f"❌ Error: Directory not found: {target_dir}")
        sys.exit(1)

    profile, _ = scan_book_dir(target_dir)
    if args.json:
        print(json.dumps(profile, indent=2, ensure_ascii=False))
    else:
        print_cli_report(target_dir.name, profile, top_n=args.top)


if __name__ == "__main__":
    main()
