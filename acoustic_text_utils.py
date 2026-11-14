"""
Acoustic Text Cleansing & Word Span Calculation Utilities.

Extracted as a standalone module to decouple text/acoustic preprocessing
from specific TTS neural backends (Kokoro ONNX, Edge Neural TTS, etc.).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

__all__ = [
    "is_standalone_divider",
    "clean_acoustic_text",
    "compute_word_spans",
    "_expand_number_token",
    "_ONES",
    "_TEENS",
    "_TENS",
    "_FUNCTION_WORDS",
]


def is_standalone_divider(text: str) -> bool:
    """Return True if text consists only of decorative divider glyphs (*, -, —, •, etc.)."""
    s = text.strip()
    return bool(re.fullmatch(r"[\*\-–—•·#\s]{2,}", s) and not re.search(r"[a-zA-Z0-9]", s))


def clean_acoustic_text(text: str) -> str:
    """
    Purify text before sending to neural TTS phonemizer:
    - Strips markdown formatting: **bold**, *italic*, __italic__, ~~strike~~
    - Strips bracketed numeric citations: [1], [2, 3], [12-15]
    - Strips footnote asterisks and glyphs: *, **, †, ‡, §, ¶, •, ◦, ▪, ▫, ‣
    - Strips markdown headers: # Chapter -> Chapter
    - Preserves semantic punctuation: currency ($100), percent (50%), em-dash, ellipses, quotes
    """
    t = text
    # 1. Strip markdown bold / italic formatting: **word** -> word, *word* -> word
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"__([^_]+)__", r"\1", t)
    t = re.sub(r"~~([^~]+)~~", r"\1", t)
    # 2. Strip bracketed numeric citations: [1], [2, 3], [1-4]
    t = re.sub(r"\[\s*\d+(?:\s*[,–-]\s*\d+)*\s*\]", "", t)
    # 2b. Unwrap editorial brackets around words: [Today's] -> Today's
    t = re.sub(r"\[([^\]]+)\]", r"\1", t)
    t = re.sub(r"[\[\]]", " ", t)
    # 3. Strip standalone asterisks and footnote markers: *, **, †, ‡, §, ¶, •, ◦, ▪, ▫, ‣, ~, #, _
    t = re.sub(r"[\*†‡§¶•◦▪▫‣#~_]", " ", t)
    # 4. Strip markdown heading hashes: e.g. # Chapter 1 -> Chapter 1
    t = re.sub(r"^\s*#+\s*", "", t)
    # 4b. Strip digit-grouping commas in numbers (e.g. 150,000 -> 150000, 7,500 -> 7500, $1,000,000 -> $1000000)
    # Kokoro's G2P tokenizer splits on commas, which improperly reads "150,000" as "one hundred fifty zero zero zero".
    while re.search(r"(\d),(\d{3}(?:\b|\D))", t):
        t = re.sub(r"(\d),(\d{3}(?:\b|\D))", r"\1\2", t)
    # 5. Fix spaces before punctuation created by stripping citations
    t = re.sub(r"\s+([,.:;?!])", r"\1", t)
    # 6. Normalize whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


# Number expander for English reading
_ONES = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
_TEENS = {10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen"}
_TENS = {2: "twenty", 3: "thirty", 4: "forty", 5: "fifty", 6: "sixty", 7: "seventy", 8: "eighty", 9: "ninety"}


def _expand_number_token(s: str) -> str:
    """Expand numeric strings into spoken English words for accurate acoustic duration estimation."""
    s = s.replace(",", "")
    if "." in s:
        parts = s.split(".", 1)
        int_exp = _expand_number_token(parts[0])
        dec = parts[1]
        if len(dec) == 2 and dec[0] != "0":
            dec_exp = _expand_number_token(dec)
        else:
            dec_exp = " ".join(_ONES.get(int(d), d) for d in dec)
        return f"{int_exp} point {dec_exp}"
    try:
        val = int(s)
    except ValueError:
        return s
    if val < 10:
        return _ONES.get(val, str(val))
    if val < 20:
        return _TEENS.get(val, str(val))
    if val < 100:
        rem = val % 10
        return _TENS.get(val // 10, "") + (" " + _ONES.get(rem, "") if rem else "")
    if 1100 <= val <= 2099 and val % 100 != 0:
        c, r = val // 100, val % 100
        c_str = _expand_number_token(str(c))
        r_str = ("oh " + _ONES.get(r, "")) if r < 10 else _expand_number_token(str(r))
        return f"{c_str} {r_str}"
    if val < 1000:
        rem = val % 100
        return _ONES.get(val // 100, "") + " hundred" + (" and " + _expand_number_token(str(rem)) if rem else "")
    if val < 1000000:
        rem = val % 1000
        return _expand_number_token(str(val // 1000)) + " thousand" + (" " + _expand_number_token(str(rem)) if rem else "")
    return s


_FUNCTION_WORDS = {
    "a", "an", "the", "of", "in", "on", "at", "to", "for", "with",
    "and", "or", "but", "is", "was", "are", "were", "it", "its", "as", "by", "that", "this"
}


def compute_word_spans(
    text: str,
    start_time: float,
    end_time: float,
) -> List[Dict[str, Any]]:
    """Derive strictly monotonic continuous word spans proportional to word acoustic weight."""
    words = text.split()
    if not words:
        return []

    duration = max(0.01, end_time - start_time)

    def _word_weight(w: str) -> float:
        # 1. Expand numbers/currencies/percentages to spoken words
        w_expanded = re.sub(r"\b\d+(?:\.\d+)?\b", lambda m: _expand_number_token(m.group(0)), w)

        # 2. Count syllables & letters in expanded form
        tokens = w_expanded.lower().split()
        total_base = 0.0
        for tok in tokens:
            clean = re.sub(r"[^a-z]", "", tok)
            if not clean:
                continue
            if clean in _FUNCTION_WORDS and len(tokens) == 1:
                base = max(1.2, float(len(clean)) * 0.8)
            else:
                vowels = len(re.findall(r"[aeiouy]+", clean))
                if clean.endswith("e") and not clean.endswith("le") and len(clean) > 2:
                    vowels = max(1, vowels - 1)
                syllables = max(1, vowels)
                base = max(1.5, float(len(clean)) * 0.7 + syllables * 1.8)
            total_base += base

        # 3. Punctuation pause modeling
        if re.search(r"[;:；：]$", w):
            total_base += 4.5
        elif re.search(r"[,，—–\-]$", w):
            total_base += 2.8
        elif re.search(r"[.?!。？！]$", w):
            total_base += 5.0
        elif re.search(r"[\"”’]$", w):
            total_base += 1.0

        return max(1.0, total_base)

    char_weights = [_word_weight(w) for w in words]
    total_weight = sum(char_weights)

    spans = []
    accum_t = start_time
    for i, (word, weight) in enumerate(zip(words, char_weights)):
        word_dur = (weight / total_weight) * duration
        w_start = round(accum_t, 3)
        w_end = round(accum_t + word_dur, 3)
        if i == len(words) - 1:
            w_end = round(end_time, 3)
        if w_end <= w_start:
            w_end = round(w_start + 0.01, 3)

        spans.append({
            "word": word,
            "start": w_start,
            "end": w_end,
            "timing_source": "observed",
        })
        accum_t += word_dur

    return spans
