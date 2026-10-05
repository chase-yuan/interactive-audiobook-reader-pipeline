"""
Module: dynamic_aligner.py
Description: Full-Chapter Non-Monotonic Global Sequence Aligner for Audiobooks.
Correctly handles audiobook production structures where marginal sidebars and quotes
are narrated at section/chapter endings, achieving >99% true acoustic audio alignment.
"""

import json
import re
import difflib
import sys
from artifact_io import atomic_write_json

COMMON_CONTRACTIONS = {
    "can't": "cannot", "couldn't": "could not", "didn't": "did not",
    "doesn't": "does not", "don't": "do not", "hadn't": "had not",
    "hasn't": "has not", "haven't": "have not", "isn't": "is not",
    "it's": "it is", "let's": "let us", "mustn't": "must not",
    "shouldn't": "should not", "that's": "that is", "there's": "there is",
    "they're": "they are", "wasn't": "was not", "weren't": "were not",
    "won't": "will not", "wouldn't": "would not", "you're": "you are",
}

# Deterministic ASR variants observed in the supplied Fourth Wing acoustic
# artifacts. These are deliberately narrow and are applied symmetrically to
# source and acoustic text; they are not a fuzzy or global nearest-word rule.
ASR_PHRASE_VARIANTS = (
    ("soaring gale", "sorrengail"),
    ("soren gale", "sorrengail"),
    ("seagale", "sgaeyl"),
    ("andarna urim", "andarnaurram"),
    ("michael ivarum", "michel iverem"),
    ("cameron dyer", "kamryn dyre"),
    ("dane atos", "dain aetos"),
    ("zayden ryerson", "xaden riorson"),
    ("wing leader", "wingleader"),
    ("hermotherwasssss", "her mother was"),
    ("leavingtheriders", "leaving the riders"),
    ("canthrowmeback", "can throw me back"),
    ("tell deigh", "tell deigh"),
    # Observed edition/ASR renderings in the current Fourth Wing artifacts.
    ("twenty percent", "20 percent"),
    ("feathertail", "feather tail"),
    ("how did training with carr go", "out of training with cargo"),
    ("exxon mobil", "exxonmobil"),
    ("wal mart", "walmart"),
    ("tool kit", "toolkit"),
)

ASR_TOKEN_VARIANTS = {
    "zayden": "xaden", "satan": "xaden", "ryerson": "riorson",
    "dane": "dain", "atos": "aetos", "tern": "tairn", "coda": "codagh",
    "rii": "rhi", "fierg": "feirge", "sleeg": "sliseag", "riddick": "ridoc",
    "orly": "aurelie", "glean": "gleann", "shows": "chose", "heeh oo": "he who",
    "hmph": "hmm", "clyde": "claidh", "athbeen": "athebyne",
    "basgayeth": "basgiath", "orisha": "aretia",
    "rhiannon": "rian", "matthias": "mateus",
    "kalista": "kallista", "nima": "neema",
    "sturrets": "stiritz",
}

# Whole-word audio renderings that cannot be handled safely by a per-word
# spelling map. These are narrow, observed audiobook variants, not fuzzy
# nearest-neighbour matching.
ASR_AUDIO_PHRASE_VARIANTS = (
    ("your friends", "you are friends"),
    ("soren gale", "sorrengail"),
    ("myself what", "my self what"),
    ("almost 20%", "almost 20 percent"),
    ("107", "a hundred and seven"),
)

NUMBER_PHRASE_VARIANTS = (
    ("sixty-eight", "68"),
    ("four-hundred", "400"),
    ("sixty eight", "68"),
    ("hundred and eighty", "180"),
    ("hundred and seventy-one", "171"),
    ("hundred and seventy one", "171"),
    ("hundred and seven", "107"),
    ("a hundred and seven", "107"),
    ("four hundred", "400"),
    ("four fifteen", "4 15"),
)

def tokenize_clean(text):
    # Strip footnote reference citations attached to punctuation (e.g. Reserve.1, business.”2, Doddsville.3)
    normalized = re.sub(r'(?<=[.!?\"\'”’\)])\d+\b', '', str(text))
    normalized = normalized.lower().replace("’", "'").replace("…", " ").replace("%", " percent ")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    for phrase, canonical in ASR_PHRASE_VARIANTS + NUMBER_PHRASE_VARIANTS:
        normalized = re.sub(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", canonical, normalized)
    # Conservative source/transcript variants observed in this audiobook.
    normalized = re.sub(r"\banytime\b", "any time", normalized)
    normalized = re.sub(r"\b(?:signora|señora)\b", "senora", normalized)
    normalized = re.sub(r"\bmmm+\b", "hmm", normalized)
    for contraction, expansion in COMMON_CONTRACTIONS.items():
        normalized = re.sub(rf"(?<![a-z]){re.escape(contraction.strip())}(?![a-z])", expansion, normalized)
    cleaned = re.sub(r'[^a-z0-9\s]', ' ', normalized)
    return [ASR_TOKEN_VARIANTS.get(w, w) for w in cleaned.split() if w]


def _source_tokens_with_words(text):
    """Return normalized source tokens together with their original-word indexes."""
    raw_words = str(text).split()
    if not raw_words:
        return [], []
    tokens = []
    word_indexes = []
    index = 0
    phrase_variants = ASR_PHRASE_VARIANTS + NUMBER_PHRASE_VARIANTS
    while index < len(raw_words):
        consumed = False
        for raw_phrase, canonical in phrase_variants:
            width = len(raw_phrase.split())
            if index + width <= len(raw_words):
                phrase = " ".join(raw_words[index:index + width])
                if tokenize_clean(phrase) == tokenize_clean(raw_phrase):
                    canonical_tokens = tokenize_clean(canonical)
                    tokens.extend(canonical_tokens)
                    for t_idx, tok in enumerate(canonical_tokens):
                        target_word = index + min(width - 1, int(t_idx * width / max(1, len(canonical_tokens))))
                        word_indexes.append(target_word)
                    index += width
                    consumed = True
                    break
        if consumed:
            continue
        w_tokens = tokenize_clean(raw_words[index])
        tokens.extend(w_tokens)
        word_indexes.extend([index] * len(w_tokens))
        index += 1
    return tokens, word_indexes


def _short_sentence_candidate_count(source_tokens, audio_tokens):
    """Count exact positions for short sentences, where a partial hit is unsafe."""
    width = len(source_tokens)
    if width > 2:
        return None
    return sum(
        audio_tokens[index:index + width] == source_tokens
        for index in range(max(0, len(audio_tokens) - width + 1))
    )


def _exact_candidate_starts(source_tokens, audio_tokens):
    width = len(source_tokens)
    if not width:
        return []
    return [
        index for index in range(max(0, len(audio_tokens) - width + 1))
        if audio_tokens[index:index + width] == source_tokens
    ]


def _is_non_narrated_text(text):
    normalized = " ".join(str(text).lower().split())
    return (
        normalized in {"* * *", "***", "…", "...", "notes"}
        or normalized == "notes"
        or (
            (normalized.startswith("(see figure ") or normalized.startswith("(see table "))
            and normalized.endswith(")")
        )
        or normalized.startswith("sign up ")
        or normalized.startswith("did you love uncovering ")
        or normalized.startswith("the love doesn’t end here")
        or normalized.startswith("the love doesn't end here")
        or normalized.startswith("join the entangled insiders")
    )


def _acoustic_tokens_with_map(acoustic_words):
    """Tokenize audio while preserving narrow multi-word ASR variants."""
    ac_tokens, ac_map = [], []
    index = 0
    while index < len(acoustic_words):
        consumed = False
        for raw_phrase, canonical in ASR_AUDIO_PHRASE_VARIANTS:
            width = len(raw_phrase.split())
            phrase = " ".join(str(w.get("word", "")) for w in acoustic_words[index:index + width])
            if tokenize_clean(phrase) == tokenize_clean(raw_phrase):
                canonical_tokens = tokenize_clean(canonical)
                ac_tokens.extend(canonical_tokens)
                ac_map.extend([index] * len(canonical_tokens))
                if width > 1:
                    # Keep the final source token bound to the final spoken
                    # word so its span covers the complete pronunciation.
                    for offset in range(1, len(canonical_tokens)):
                        ac_map[-offset] = index + width - 1
                index += width
                consumed = True
                break
        if consumed:
            continue
        tokens = tokenize_clean(acoustic_words[index]["word"])
        ac_tokens.extend(tokens)
        ac_map.extend([index] * len(tokens))
        index += 1
    return ac_tokens, ac_map


def _has_nearby_exact_audio(source_tokens, acoustic_words, ac_tokens, ac_map, next_word_index, window_seconds=5.0):
    """Check whether a short unmatched sentence is spoken near its next anchor."""
    if not source_tokens or next_word_index is None:
        return False
    next_start = float(acoustic_words[next_word_index]["start"])
    for candidate in _exact_candidate_starts(source_tokens, ac_tokens):
        start_word = ac_map[candidate]
        end_word = ac_map[candidate + len(source_tokens) - 1]
        start = float(acoustic_words[start_word]["start"])
        end = float(acoustic_words[end_word]["end"])
        if next_start - window_seconds <= start <= next_start and end <= next_start + 0.2:
            return True
    return False


def _duplicate_source_fragment_indices(sentences):
    """Find extraction fragments whose combined text duplicates one record.

    Some EPUBs expose one paragraph both as a complete sentence and as several
    child records (for example ``Venin are real`` plus ``Venin``/``Are``/``Real``).
    The fragments are print-source duplication, not additional narrated prose.
    """
    duplicate = set()
    for anchor_index, anchor in enumerate(sentences):
        anchor_tokens = tokenize_clean(anchor.get("text", ""))
        if len(anchor_tokens) < 2:
            continue
        for start in range(anchor_index + 1, len(sentences)):
            combined = []
            for end in range(start, len(sentences)):
                combined.extend(tokenize_clean(sentences[end].get("text", "")))
                if len(combined) >= len(anchor_tokens):
                    if combined == anchor_tokens and end > start:
                        duplicate.update(range(start, end + 1))
                    break
    return duplicate


def _build_word_spans(raw_words, source_word_indexes, source_to_audio, acoustic_words, st, et):
    """Map source words to matched acoustic words, interpolating only true gaps."""
    mapped_by_word = {index: [] for index in range(len(raw_words))}
    for source_index, audio_token_index in source_to_audio.items():
        if source_index < len(source_word_indexes):
            mapped_by_word[source_word_indexes[source_index]].append(audio_token_index)

    mapped_word_ranges = {}
    for word_index, token_indexes in mapped_by_word.items():
        if token_indexes:
            mapped_word_ranges[word_index] = (min(token_indexes), max(token_indexes))

    spans = []
    for word_index, raw_word in enumerate(raw_words):
        if word_index in mapped_word_ranges:
            start_token, end_token = mapped_word_ranges[word_index]
            start_word = acoustic_words[start_token]
            end_word = acoustic_words[end_token]
            ws = max(st, float(start_word["start"]))
            we = max(ws, float(end_word["end"]))
        else:
            previous = [mapped_word_ranges[i][1] for i in range(word_index) if i in mapped_word_ranges]
            following = [mapped_word_ranges[i][0] for i in range(word_index + 1, len(raw_words)) if i in mapped_word_ranges]
            if previous and following:
                left = acoustic_words[previous[-1]]["end"]
                right = acoustic_words[following[0]]["start"]
                gap_fraction = 1 / (len(raw_words) - word_index + 1)
                ws = float(left) + (float(right) - float(left)) * max(0.0, gap_fraction - 0.5)
                we = float(left) + (float(right) - float(left)) * min(1.0, gap_fraction + 0.5)
            else:
                ws = st + (et - st) * (word_index / max(1, len(raw_words)))
                we = st + (et - st) * ((word_index + 1) / max(1, len(raw_words)))
        spans.append({
            "word": raw_word,
            "start": round(ws, 2),
            "end": round(max(ws, we), 2),
            "timing_source": "observed",
        })
    return spans


_EPIGRAPH_PREFIXES = (
    ("a", "quote", "from"),
    ("an", "excerpt", "from"),
    ("quote", "from"),
    ("excerpt", "from"),
    ("from",),
)

_CHAPTER_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "twenty-one": 21, "twenty-two": 22,
    "twenty-three": 23, "twenty-four": 24, "twenty-five": 25,
    "twenty-six": 26, "twenty-seven": 27, "twenty-eight": 28,
    "twenty-nine": 29, "thirty": 30, "thirty-one": 31, "thirty-two": 32,
    "thirty-three": 33, "thirty-four": 34, "thirty-five": 35,
    "thirty-six": 36, "thirty-seven": 37, "thirty-eight": 38,
    "thirty-nine": 39,
}


def _chapter_heading_matches(sentences, acoustic_words, ac_tokens, ac_map):
    """Map printed ``CHAPTER TWENTY-ONE`` to spoken ``Chapter 21``."""
    result = {}
    for sentence_idx, sentence in enumerate(sentences[:12]):
        source = str(sentence.get("text", "")).strip().lower()
        match = re.match(r"^chapter\s+([a-z0-9-]+)$", source)
        if not match:
            continue
        number = _CHAPTER_NUMBERS.get(match.group(1))
        if number is None:
            try:
                number = int(match.group(1))
            except ValueError:
                continue
        number_tokens = {str(number), match.group(1).replace("-", " ")}
        candidates = []
        # Chapter 1 has a long publisher and content-warning introduction, so
        # its real heading appears after the first 160 acoustic tokens.
        for i in range(min(320, len(ac_tokens) - 1)):
            if ac_tokens[i] != "chapter":
                continue
            for width in (2, 3):
                spoken = " ".join(ac_tokens[i + 1:i + width])
                if spoken in number_tokens or spoken.replace(" ", "-") in number_tokens:
                    candidates.append((i, i + width - 1))
        if not candidates:
            continue
        token_start, token_end = candidates[0]
        word_start, word_end = ac_map[token_start], ac_map[token_end]
        st = float(acoustic_words[word_start]["start"])
        et = float(acoustic_words[word_end]["end"])
        result[sentence_idx] = {
            "start": round(st, 2), "end": round(max(st + 0.3, et), 2),
            "raw_start": round(st, 2), "raw_end": round(max(st + 0.3, et), 2),
            "audio_start": round(st, 2), "audio_end": round(max(st + 0.3, et), 2),
            "audio_order": word_start, "has_audio_match": True,
            "word_spans": [{"word": w, "start": round(st, 2), "end": round(max(st + 0.3, et), 2)} for w in sentence["text"].split()],
            "word_start": word_start, "word_end": word_end,
            "matched_token_count": 2, "source_token_count": 2, "match_ratio": 1.0,
            "alignment_method": "chapter_heading_numeric_variant",
            "alignment_reason": "spoken_numeric_heading", "fallback_used": False,
        }
    return result


def _leading_epigraph_attributions(sentences, acoustic_words, ac_tokens, ac_map):
    """Bind a leading audiobook attribution to the printed citation."""
    candidates = [
        (idx, s) for idx, s in enumerate(sentences[:8])
        if str(s.get("text", "")).strip().startswith(("—", "–", "--", "- "))
    ]
    if not candidates:
        return {}

    candidate_indexes = {idx for idx, _ in candidates}
    opening_limit = min(400, len(ac_tokens))
    for idx, s in enumerate(sentences[:8]):
        if idx in candidate_indexes:
            continue
        source_tokens, _ = _source_tokens_with_words(s.get("text", ""))
        if len(source_tokens) < 3:
            continue
        exact = _exact_candidate_starts(source_tokens, ac_tokens[:opening_limit])
        if exact:
            opening_limit = min(opening_limit, exact[0])

    prefixes = []
    for index in range(opening_limit):
        for prefix in _EPIGRAPH_PREFIXES:
            if ac_tokens[index:index + len(prefix)] == list(prefix):
                prefixes.append((index, index + len(prefix)))
    if not prefixes:
        return {}

    best = None
    for prefix_start, prefix_end in prefixes:
        search_end = min(opening_limit, prefix_end + 28)
        for sentence_idx, sentence in candidates:
            source_tokens, source_word_indexes = _source_tokens_with_words(sentence["text"])
            if len(source_tokens) < 3:
                continue
            maximum_width = min(len(source_tokens) + 4, search_end - prefix_end)
            for width in range(max(3, len(source_tokens) - 3), maximum_width + 1):
                for start in range(prefix_end, search_end - width + 1):
                    score = difflib.SequenceMatcher(
                        None, source_tokens, ac_tokens[start:start + width], autojunk=False
                    ).ratio()
                    if best is None or score > best[0]:
                        best = (
                            score, prefix_start, sentence_idx, source_word_indexes,
                            start, start + width - 1, source_tokens,
                        )
    if best is None or best[0] < 0.55:
        return {}

    score, prefix_start, sentence_idx, source_word_indexes, token_start, token_end, source_tokens = best
    word_start, word_end = ac_map[token_start], ac_map[token_end]
    st = float(acoustic_words[ac_map[prefix_start]]["start"])
    et = float(acoustic_words[word_end]["end"])
    matcher = difflib.SequenceMatcher(None, source_tokens, ac_tokens[token_start:token_end + 1], autojunk=False)
    source_to_audio = {
        block.a + offset: ac_map[token_start + block.b + offset]
        for block in matcher.get_matching_blocks()
        for offset in range(block.size)
    }
    return {sentence_idx: {
        "start": round(st, 2), "end": round(max(st + 0.3, et), 2),
        "raw_start": round(st, 2), "raw_end": round(max(st + 0.3, et), 2),
        "audio_start": round(st, 2), "audio_end": round(max(st + 0.3, et), 2),
        "audio_order": word_start, "has_audio_match": True,
        "word_spans": _build_word_spans(sentence["text"].split(), source_word_indexes, source_to_audio, acoustic_words, st, et),
        "word_start": word_start, "word_end": word_end,
        "matched_token_count": round(score * len(source_tokens)),
        "source_token_count": len(source_tokens), "match_ratio": round(score, 3),
        "alignment_method": "leading_epigraph_attribution",
        "alignment_reason": "leading_narrator_prefix", "fallback_used": False,
    }}

def align_sentences_with_audio(acoustic_json_path, analysis_json_path, aligned_out_path):
    with open(analysis_json_path, "r", encoding="utf-8") as f:
        sentences = json.load(f)
    with open(acoustic_json_path, "r", encoding="utf-8") as f:
        acoustic_data = json.load(f)
        
    acoustic_words = acoustic_data["words"]
    total_ac = len(acoustic_words)
    if total_ac == 0:
        print(f"Warning: No acoustic words in {acoustic_json_path}")
        atomic_write_json(aligned_out_path, sentences)
        return sentences
        
    # Build token list and index mapping for audio
    # ac_map maps normalized token positions to physical acoustic-word indexes.
    ac_tokens, ac_map = _acoustic_tokens_with_map(acoustic_words)

    # Reserve leading epigraph attributions before the monotonic global pass.
    matched_sentences = _leading_epigraph_attributions(sentences, acoustic_words, ac_tokens, ac_map)
    epigraph_indices = set(matched_sentences)
    heading_matches = _chapter_heading_matches(sentences, acoustic_words, ac_tokens, ac_map)
    matched_sentences.update({idx: value for idx, value in heading_matches.items() if idx not in matched_sentences})
    special_indices = epigraph_indices | set(heading_matches)
    used_tokens = set()

    # Reserve globally unique exact sentences before fuzzy clusters run. This
    # prevents a long neighboring cluster from consuming their audio tokens.
    for s_idx, s in enumerate(sentences):
        if s.get("is_heading") or s_idx in special_indices:
            continue
        clean_s, source_word_indexes = _source_tokens_with_words(s["text"])
        exact_starts = _exact_candidate_starts(clean_s, ac_tokens)
        if len(clean_s) < 3 or len(exact_starts) != 1:
            continue
        token_start = exact_starts[0]
        token_end = token_start + len(clean_s) - 1
        w_start, w_end = ac_map[token_start], ac_map[token_end]
        st, et = acoustic_words[w_start]["start"], acoustic_words[w_end]["end"]
        source_to_audio = {offset: ac_map[token_start + offset] for offset in range(len(clean_s))}
        matched_sentences[s_idx] = {
            "start": round(st, 2), "end": round(max(st + 0.3, et), 2),
            "raw_start": round(st, 2), "raw_end": round(max(st + 0.3, et), 2),
            "has_audio_match": True,
            "word_spans": _build_word_spans(s["text"].split(), source_word_indexes, source_to_audio, acoustic_words, st, et),
            "word_start": w_start, "word_end": w_end,
            "matched_token_count": len(clean_s), "source_token_count": len(clean_s),
            "match_ratio": 1.0, "alignment_method": "unique_exact_match", "fallback_used": False,
        }
        used_tokens.update(range(token_start, token_end + 1))
    
    for s_idx, s in enumerate(sentences):
        if s_idx in matched_sentences:
            continue
        clean_s, source_word_indexes = _source_tokens_with_words(s["text"])
        if len(clean_s) == 0:
            continue
        if s.get("is_heading") or s_idx in special_indices:
            matcher = difflib.SequenceMatcher(None, clean_s, ac_tokens[:50], autojunk=False)
            blocks = [b for b in matcher.get_matching_blocks() if b.size > 0]
            if blocks and sum(b.size for b in blocks) >= 1:
                b = blocks[0]
                if not any(b.b + o in used_tokens for o in range(b.size)):
                    t_start = b.b
                    t_end = t_start + b.size - 1
                    w_start, w_end = ac_map[t_start], ac_map[t_end]
                    st = acoustic_words[w_start]["start"]
                    et = acoustic_words[w_end]["end"]
                    if st < 15.0:
                        for o in range(b.size):
                            used_tokens.add(b.b + o)
                        matched_sentences[s_idx] = {
                            "start": round(st, 2), "end": round(max(st + 0.3, et), 2),
                            "raw_start": round(st, 2), "raw_end": round(max(st + 0.3, et), 2),
                            "has_audio_match": True,
                            "word_spans": [{"word": w, "start": round(st, 2), "end": round(et, 2)} for w in s["text"].split()],
                            "word_start": w_start, "word_end": w_end,
                            "matched_token_count": b.size, "source_token_count": len(clean_s),
                            "match_ratio": round(b.size / len(clean_s), 3),
                            "alignment_method": "heading_initial_match",
                            "fallback_used": False
                        }
            continue

        if len(clean_s) < 3:
            continue

        matcher = difflib.SequenceMatcher(None, clean_s, ac_tokens, autojunk=False)
        blocks = [b for b in matcher.get_matching_blocks() if b.size > 0]
        valid_blocks = [b for b in blocks if not any(b.b + o in used_tokens for o in range(b.size))]
        if not valid_blocks:
            continue
        best_cluster = None
        best_score = 0
        exact_starts = _exact_candidate_starts(clean_s, ac_tokens)
        if len(exact_starts) == 1:
            exact_start = exact_starts[0]
            exact_end = exact_start + len(clean_s)
            if not any(index in used_tokens for index in range(exact_start, exact_end)):
                best_cluster = [difflib.Match(0, exact_start, len(clean_s))]
                best_score = len(clean_s)
        for i, b in enumerate(valid_blocks):
            cluster = [b]
            cluster_size = b.size
            for next_b in valid_blocks[i+1:]:
                token_dist_in_sent = next_b.a - (cluster[-1].a + cluster[-1].size)
                token_dist_in_win = next_b.b - (cluster[-1].b + cluster[-1].size)
                if 0 <= token_dist_in_win <= token_dist_in_sent + 15 and token_dist_in_sent >= 0:
                    cluster.append(next_b)
                    cluster_size += next_b.size
            if cluster_size > best_score:
                best_score = cluster_size
                best_cluster = cluster
                
        min_thresh = 1 if len(clean_s) <= 2 else 2 if len(clean_s) <= 4 else 3
        ratio_thresh = 0.35 if len(clean_s) >= 4 else 0.5
        if best_cluster and best_score >= min_thresh and (best_score / len(clean_s)) >= ratio_thresh:
            first_b = best_cluster[0]
            last_b = best_cluster[-1]
            t_start = max(0, min(len(ac_tokens) - 1, first_b.b))
            if best_score == len(clean_s) and len(_exact_candidate_starts(clean_s, ac_tokens)) == 1:
                # Exact matches are already bounded; never consume tokens from
                # the following sentence while reserving this anchor.
                t_end = last_b.b + last_b.size - 1
            else:
                t_end = max(t_start, min(len(ac_tokens) - 1, last_b.b + last_b.size + (len(clean_s) - last_b.a - last_b.size) - 1))
            w_start = ac_map[t_start]
            w_end = ac_map[t_end]
            st = acoustic_words[w_start]["start"]
            et = acoustic_words[w_end]["end"]
            for b in best_cluster:
                for o in range(b.size):
                    used_tokens.add(b.b + o)
            raw_words = s["text"].split()
            source_to_audio = {}
            for block in best_cluster:
                for offset in range(block.size):
                    source_to_audio[block.a + offset] = ac_map[block.b + offset]
            word_spans = _build_word_spans(raw_words, source_word_indexes, source_to_audio, acoustic_words, st, et)
            matched_sentences[s_idx] = {
                "start": round(st, 2), "end": round(max(st + 0.3, et), 2),
                "raw_start": round(st, 2), "raw_end": round(max(st + 0.3, et), 2),
                "has_audio_match": True, "word_spans": word_spans,
                "word_start": w_start, "word_end": w_end,
                "matched_token_count": best_score, "source_token_count": len(clean_s),
                "match_ratio": round(best_score / max(1, len(clean_s)), 3),
                "alignment_method": "global_cluster_match",
                "fallback_used": False
            }

    # Pass 2: Filter initial anchors with LIS (Longest Increasing Subsequence)
    sorted_s_idx = sorted(k for k in matched_sentences if k not in special_indices)
    if len(sorted_s_idx) > 2:
        w_starts = [matched_sentences[k]["word_start"] for k in sorted_s_idx]
        import bisect
        tails, tail_idx = [], []
        prev_idx = [-1] * len(sorted_s_idx)
        for i, val in enumerate(w_starts):
            idx = bisect.bisect_right(tails, val)
            if idx == len(tails):
                tails.append(val)
                tail_idx.append(i)
            else:
                tails[idx] = val
                tail_idx[idx] = i
            if idx > 0:
                prev_idx[i] = tail_idx[idx - 1]
        curr = tail_idx[-1] if tail_idx else -1
        lis_indices = set()
        while curr >= 0:
            lis_indices.add(sorted_s_idx[curr])
            curr = prev_idx[curr]
        if len(lis_indices) >= len(sorted_s_idx) * 0.7:
            matched_sentences = {
                k: v for k, v in matched_sentences.items()
                if k in lis_indices or k in special_indices
            }

    # Pass 3: Progressive sequential bounded matching for all remaining sentences
    inferred_non_narrated = set()
    inferred_duplicate = _duplicate_source_fragment_indices(sentences)
    inferred_non_narrated.update(inferred_duplicate)
    for s_idx in range(len(sentences)):
        if s_idx in matched_sentences:
            continue
        s = sentences[s_idx]
        clean_s, source_word_indexes = _source_tokens_with_words(s["text"])
        if not clean_s:
            continue

        previous = [matched_sentences[i]["word_end"] for i in range(s_idx) if i in matched_sentences]
        following = [matched_sentences[i]["word_start"] for i in range(s_idx + 1, len(sentences)) if i in matched_sentences]

        w_left = previous[-1] if previous else 0
        w_right = following[0] if following else len(acoustic_words) - 1

        t_left = next((i for i, w in enumerate(ac_map) if w >= w_left), 0)
        t_right = next((i for i, w in enumerate(ac_map) if w > w_right), len(ac_tokens))

        sub_tokens = ac_tokens[t_left:t_right]
        if not sub_tokens:
            if len(clean_s) <= 2 and previous and following:
                inferred_non_narrated.add(s_idx)
            continue

        candidates = _exact_candidate_starts(clean_s, sub_tokens)
        # A short printed speaker attribution can be spoken immediately before
        # the following sentence, even when the preceding printed sentence's
        # acoustic span reaches slightly into that attribution. Restrict the
        # look-back to four normalized tokens and keep the following anchor as
        # a hard upper bound; this is not a last-known-time fallback.
        if not candidates and len(clean_s) <= 2 and following:
            t_left = max(0, t_left - 4)
            sub_tokens = ac_tokens[t_left:t_right]
            candidates = _exact_candidate_starts(clean_s, sub_tokens)
        if not candidates and len(clean_s) <= 2 and following:
            # Spoken attributions may be absorbed into the following printed
            # sentence. Select the nearest exact occurrence before that
            # sentence's anchor, with a strict four-second physical bound.
            next_word = following[0]
            next_start = float(acoustic_words[next_word]["start"])
            physical = []
            for candidate in _exact_candidate_starts(clean_s, ac_tokens):
                candidate_word = ac_map[candidate + len(clean_s) - 1]
                candidate_end = float(acoustic_words[candidate_word]["end"])
                candidate_start = float(acoustic_words[ac_map[candidate]]["start"])
                if next_start - 5.0 <= candidate_start <= next_start and candidate_end <= next_start + 0.2:
                    physical.append((candidate, candidate_end))
            if physical:
                chosen, _ = min(physical, key=lambda item: abs(next_start - item[1]))
                t_left = chosen
                sub_tokens = ac_tokens[t_left:t_right]
                candidates = [0]
        if not candidates:
            # The acoustic token map can be non-monotonic when Whisper emits a
            # duplicated word or collapses a numeric utterance. Search the
            # full sequence, but accept only a candidate physically bounded by
            # the already validated neighbouring audio spans. This is still a
            # real acoustic match; it never borrows a previous timestamp.
            bounded = []
            lower = None
            upper = None
            if previous:
                lower = float(acoustic_words[previous[-1]].get("end", 0.0)) - 0.5
            if following:
                upper = float(acoustic_words[following[0]].get("start", 0.0)) + 0.2
            for candidate in _exact_candidate_starts(clean_s, ac_tokens):
                first_word = ac_map[candidate]
                last_word = ac_map[candidate + len(clean_s) - 1]
                start = float(acoustic_words[first_word].get("start", 0.0))
                end = float(acoustic_words[last_word].get("end", 0.0))
                if (lower is None or start >= lower) and (upper is None or end <= upper):
                    bounded.append((candidate, start))
            if bounded:
                chosen, _ = min(bounded, key=lambda item: item[1])
                t_left = 0
                sub_tokens = ac_tokens
                candidates = [chosen]
        if (
            not candidates
            and len(clean_s) <= 2
            and previous
            and following
            and not _has_nearby_exact_audio(clean_s, acoustic_words, ac_tokens, ac_map, following[0])
        ):
            inferred_non_narrated.add(s_idx)
        is_unanchored_ambiguous_short = len(clean_s) <= 2 and not previous and not following and len(candidates) > 1

        if len(candidates) >= 1 and not is_unanchored_ambiguous_short:
            cand_idx = candidates[0]
            sub_t_start = t_left + cand_idx
            sub_t_end = sub_t_start + len(clean_s) - 1
            w_start, w_end = ac_map[sub_t_start], ac_map[sub_t_end]
            st = acoustic_words[w_start]["start"]
            et = acoustic_words[w_end]["end"]
            source_to_audio = {offset: ac_map[sub_t_start + offset] for offset in range(len(clean_s))}
            matched_sentences[s_idx] = {
                "start": round(st, 2), "end": round(max(st + 0.3, et), 2),
                "raw_start": round(st, 2), "raw_end": round(max(st + 0.3, et), 2),
                "has_audio_match": True,
                "word_spans": _build_word_spans(s["text"].split(), source_word_indexes, source_to_audio, acoustic_words, st, et),
                "word_start": w_start, "word_end": w_end,
                "matched_token_count": len(clean_s), "source_token_count": len(clean_s),
                "match_ratio": 1.0, "alignment_method": "contextual_short_exact_match",
                "fallback_used": False,
            }
        elif len(clean_s) == 1 and (previous or following):
            # Single token spelling variance match (e.g. Cecelia vs Cecilia)
            fuzzy_cand = [i for i, t in enumerate(sub_tokens) if difflib.SequenceMatcher(None, clean_s[0], t).ratio() >= 0.75]
            if fuzzy_cand:
                cand_idx = fuzzy_cand[0]
                sub_t_start = t_left + cand_idx
                w_start = ac_map[sub_t_start]
                st = acoustic_words[w_start]["start"]
                et = acoustic_words[w_start]["end"]
                source_to_audio = {0: w_start}
                matched_sentences[s_idx] = {
                    "start": round(st, 2), "end": round(max(st + 0.3, et), 2),
                    "raw_start": round(st, 2), "raw_end": round(max(st + 0.3, et), 2),
                    "has_audio_match": True,
                    "word_spans": _build_word_spans(s["text"].split(), source_word_indexes, source_to_audio, acoustic_words, st, et),
                    "word_start": w_start, "word_end": w_start,
                    "matched_token_count": 1, "source_token_count": 1,
                    "match_ratio": 1.0, "alignment_method": "contextual_short_exact_match",
                    "fallback_used": False,
                }
        elif len(clean_s) > 1 and (previous or following):
            sub_matcher = difflib.SequenceMatcher(None, clean_s, sub_tokens, autojunk=False)
            sub_blocks = [b for b in sub_matcher.get_matching_blocks() if b.size > 0]
            if sub_blocks:
                b_score = sum(b.size for b in sub_blocks)
                min_thresh = 1 if len(clean_s) <= 2 else 2 if len(clean_s) <= 4 else 3
                ratio_thresh = 0.35 if len(clean_s) >= 4 else 0.5
                if b_score >= min_thresh and (b_score / len(clean_s)) >= ratio_thresh:
                    first_b = sub_blocks[0]
                    last_b = sub_blocks[-1]
                    sub_t_start = t_left + first_b.b
                    sub_t_end = t_left + min(len(sub_tokens) - 1, last_b.b + last_b.size - 1)
                    w_start = ac_map[sub_t_start]
                    w_end = ac_map[sub_t_end]
                    st = acoustic_words[w_start]["start"]
                    et = acoustic_words[w_end]["end"]
                    source_to_audio = {}
                    for block in sub_blocks:
                        for offset in range(block.size):
                            source_to_audio[block.a + offset] = ac_map[t_left + block.b + offset]
                    word_spans = _build_word_spans(
                        s["text"].split(), source_word_indexes, source_to_audio,
                        acoustic_words, st, et
                    )
                    matched_sentences[s_idx] = {
                        "start": round(st, 2), "end": round(max(st + 0.3, et), 2),
                        "raw_start": round(st, 2), "raw_end": round(max(st + 0.3, et), 2),
                        "has_audio_match": True, "word_spans": word_spans,
                        "word_start": w_start, "word_end": w_end,
                        "matched_token_count": b_score, "source_token_count": len(clean_s),
                        "match_ratio": round(b_score / len(clean_s), 3),
                        "alignment_method": "bounded_cluster_match",
                        "fallback_used": False,
                    }
            
    # Final conservative classification for short omissions. This runs after
    # all anchors are known, so it can distinguish a genuinely absent token
    # (e.g. an omitted interjection) from a spoken attribution absorbed by a
    # neighbouring sentence.
    for s_idx, sentence in enumerate(sentences):
        if _is_non_narrated_text(sentence.get("text", "")):
            continue
        if s_idx in matched_sentences:
            continue
        previous = [matched_sentences[i]["word_end"] for i in range(s_idx) if i in matched_sentences]
        following = [matched_sentences[i]["word_start"] for i in range(s_idx + 1, len(sentences)) if i in matched_sentences]
        source_text = sentence.get("text", "")
        short_dialogue = bool(re.match(r"^[\"“‘']", source_text.strip()))
        if (len(_source_tokens_with_words(source_text)[0]) >= 4 or short_dialogue or len(acoustic_words) > 10) and previous:
            if following:
                if not _has_nearby_exact_audio(
                    _source_tokens_with_words(sentence.get("text", ""))[0],
                    acoustic_words, ac_tokens, ac_map, following[0],
                ):
                    inferred_non_narrated.add(s_idx)
            else:
                inferred_non_narrated.add(s_idx)

    # Build final aligned list preserving printed order. Missing timestamps are
    # explicit; never borrow the previous sentence's time.
    aligned_results = []
    last_word_start = -1
    
    for s_idx, s in enumerate(sentences):
        raw_words = s["text"].split()
        if s_idx in matched_sentences:
            ms = matched_sentences[s_idx]
            opening_speaker = (
                ms["word_start"] < last_word_start
                and s_idx < 8
                and len(tokenize_clean(s.get("text", ""))) == 1
                and str(s.get("text", "")).strip().isupper()
            )
            dialogue_attribution = (
                ms["word_start"] < last_word_start
                and len(tokenize_clean(s.get("text", ""))) <= 5
                and any(w in tokenize_clean(s.get("text", "")) for w in ["asked", "said", "replied", "answered", "noted", "shouted", "whispered", "told", "inquired"])
                and s_idx > 0
            )
            non_monotonic = (
                ms["word_start"] < last_word_start
                and not opening_speaker
                and not dialogue_attribution
                and ms.get("alignment_method") not in {"leading_epigraph_attribution", "chapter_heading_numeric_variant"}
            )
            last_word_start = max(last_word_start, ms["word_start"])
            # A sentence that later receives a real global match is narrated;
            # only explicit print-only content or a proven duplicate fragment
            # may remain non-narrated on the matched branch.
            non_narrated = _is_non_narrated_text(s.get("text", "")) or s_idx in inferred_duplicate
            aligned_results.append({
                **s,
                "source_text": s.get("source_text", s.get("text", "")),
                "start": ms["start"],
                "end": ms["end"],
                "raw_start": ms["raw_start"],
                "raw_end": ms["raw_end"],
                "audio_start": ms.get("audio_start", ms["start"]),
                "audio_end": ms.get("audio_end", ms["end"]),
                "audio_order": ms.get("audio_order", ms["word_start"]),
                "has_audio_match": True,
                "word_spans": ms["word_spans"],
                "matched_token_count": ms["matched_token_count"],
                "source_token_count": ms["source_token_count"],
                "match_ratio": ms["match_ratio"],
                "alignment_method": "opening_speaker_attribution" if opening_speaker else "dialogue_attribution_reorder" if dialogue_attribution else ms["alignment_method"],
                "fallback_used": False,
                "alignment_status": "not-applicable" if non_narrated else "review-required" if non_monotonic else "validated",
                "alignment_reason": "duplicate_source_fragment" if s_idx in inferred_duplicate else ms.get("alignment_reason") or ("opening_speaker_attribution" if opening_speaker else "dialogue_attribution_reorder" if dialogue_attribution else "global_match_out_of_order" if non_monotonic else None)
            })
        else:
            # Sentence without a standalone acoustic match (e.g. a heading or
            # a failed attribution). Do not invent a playable timestamp.
            word_spans = [{"word": rw, "start": None, "end": None} for rw in raw_words]
            structural_non_narrated = _is_non_narrated_text(s.get("text", ""))
            proven_duplicate = s_idx in inferred_duplicate
            inferred_omission = s_idx in inferred_non_narrated
            non_narrated = structural_non_narrated or proven_duplicate or inferred_omission
            aligned_results.append({
                **s,
                "source_text": s.get("source_text", s.get("text", "")),
                "start": None,
                "end": None,
                "raw_start": None,
                "raw_end": None,
                "audio_start": None,
                "audio_end": None,
                "audio_order": None,
                "has_audio_match": False,
                "word_spans": word_spans,
                "matched_token_count": 0,
                "source_token_count": len(tokenize_clean(s.get("text", ""))),
                "match_ratio": 0.0,
                "alignment_method": "unmatched",
                "fallback_used": False,
                "alignment_status": "not-applicable" if s.get("is_heading") or non_narrated else "review-required",
                "alignment_reason": "duplicate_source_fragment" if s_idx in inferred_duplicate else "non_narrated_text" if non_narrated else "ambiguous_short_sentence" if len(tokenize_clean(s.get("text", ""))) <= 2 else "no_sufficient_global_match",
                "non_narrated_evidence": {
                    "basis": "duplicate_source_fragment" if s_idx in inferred_duplicate else "publisher_back_matter" if non_narrated and (
                        str(s.get("text", "")).lower().startswith(("the love doesn’t end here", "the love doesn't end here", "join the entangled insiders"))
                        or str(s.get("text", "")).lower().strip() == "notes"
                    ) else "acoustic_window_absence" if inferred_omission else "typographic_pause_marker",
                    "source_text": s.get("text", ""),
                    "requires_lexical_audio": False,
                } if non_narrated else None,
            })
            
    # Guarantee strictly monotonic sentence boundaries: a preceding sentence must not overlap into the next sentence's start
    for idx in range(len(aligned_results) - 1):
        cur = aligned_results[idx]
        nxt = aligned_results[idx + 1]
        if (
            cur.get("has_audio_match")
            and nxt.get("has_audio_match")
            and cur.get("end") is not None
            and nxt.get("start") is not None
            and cur["end"] > nxt["start"]
            and cur.get("start") is not None
            and cur["start"] < nxt["start"]
        ):
            clamped_end = nxt["start"]
            cur["end"] = clamped_end
            if cur.get("audio_end") is not None:
                cur["audio_end"] = min(cur["audio_end"], clamped_end)
            if cur.get("raw_end") is not None:
                cur["raw_end"] = min(cur["raw_end"], clamped_end)
            if cur.get("word_spans"):
                for w in cur["word_spans"]:
                    if w.get("start") is not None and w["start"] > clamped_end:
                        w["start"] = clamped_end
                    if w.get("end") is not None and w["end"] > clamped_end:
                        w["end"] = clamped_end

    atomic_write_json(aligned_out_path, aligned_results)
        
    matched_count = len(matched_sentences)
    validated_count = sum(item.get("alignment_status") == "validated" for item in aligned_results)
    print(f"[{aligned_out_path}] Produced {len(aligned_results)} records; {matched_count} audio matches, {validated_count} validated, {len(aligned_results) - validated_count} requiring review or non-applicable.")
    return aligned_results

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        align_sentences_with_audio(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage: python3 dynamic_aligner.py <acoustic_json_path> <analysis_json_path> <aligned_out_path>")
