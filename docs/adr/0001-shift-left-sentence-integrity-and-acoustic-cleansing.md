# 1. Architecture Decision Record: Shift-Left Sentence Integrity & Acoustic Cleansing

- **Status**: Accepted
- **Date**: 2026-10-10
- **Deciders**: CTO Autonomous Engineering

## Context

During the production build of *Beyond Feelings: A Guide to Critical Thinking* and subsequent 5-Lane Grill Red-Team Audit (`grill-report-2026-10-10.md`), several catastrophic systemic defects were uncovered:
1. **Post-Mortem Inverted Quality Gate**: Quality validation (`validate_outputs.py`) executed at Stage 4 *after* Stage 2 LLM translation and Stage 3 Kokoro TTS synthesis. Corrupted text from upstream extraction consumed 1.5–2 hours of high-intensity CPU computation and LLM token budgets before any validation occurred.
2. **Quality Gate Blindspot**: `validate_outputs.py` categorized multi-boundary sentence splits as non-blocking `diagnostics` and completely ignored trailing line-break hyphens (`[a-zA-Z]-$`), lowercase-initial continuation fragments (`^[a-z]`), and orphan single-word lines. A dataset with 2,648 broken sentences received `release_ready: true`.
3. **Lossy Print Ingestion & Paragraph Chopping**: Calibre/InDesign PDF-to-EPUB conversion wrapped individual visual print lines in `<p>` tags and hard-split words across lines. `extract_epub.py` treated each `<p>` tag as an isolated semantic block, never stitching broken sentences or de-hyphenating words.
4. **Phonetic Pronunciation of Typographic Symbols**: Kokoro ONNX tokenizer's neural phonemizer explicitly pronounced non-speech characters: `*` $\to$ `"asterisk"`, `**` $\to$ `"asterisk asterisk"`, `#` $\to$ `"hash"`, `~` $\to$ `"tilde"`, `\` $\to$ `"backslash"`, and `[1]` $\to$ `"one"`. Footnotes, section dividers (`* * *`), and markdown formatting were literally sung out as spoken words in the synthesized audiobook.
5. **Thermal Runaway & Unbounded ONNX Threading**: Kokoro ONNX runtime defaulted to all available CPU threads across 3 concurrent chapter workers, pinning CPU utilization at 650%+, exceeding 95°C thermal thresholds, and causing severe system throttling.

## Decision

1. **Shift-Left Stage 1.5 Sentence Integrity Gate**:
   - Introduce `validate_canonical_sentences()` immediately following sentence extraction in `universal_runner.py` and `validate_outputs.py`.
   - The gate halts pipeline execution with exit code 1 if any canonical sentence exhibits:
     - Trailing hyphens (`\b[a-zA-Z]-$`)
     - Non-heading lowercase continuation beginnings (`^[a-z]`)
     - Non-heading orphan single-word fragments (`^[A-Za-z]+$`)
     - Unclosed paired quotation marks (`"`, `“`, `”`).
2. **Element-Level De-Hyphenation & Cross-Paragraph Stitching in `extract_epub.py`**:
   - Prior to sentence splitting, inspect adjacent block elements.
   - Reconnect hyphenated word fragments (`oversimplifi-` + `cation` $\to$ `oversimplification`).
   - Merge lines that do not end in terminal sentence punctuation (`.`, `!`, `?`, `"`, `”`) or where the next line begins with lowercase.
   - Automatically filter out repeated running headers/footers.
3. **Acoustic Text Cleanser in `kokoro_synthesizer.py` (Visual vs Acoustic Decoupling)**:
   - Separate display text (`text`) from synthesized acoustic text (`acoustic_text`).
   - Strip footnote asterisks (`*`, `**`), daggers (`†`, `‡`), markdown headers (`#`), bullet glyphs (`•`), and bracketed citation numbers (`[1]`, `[12]`) before sending to `tts.create()`.
   - Convert standalone divider elements (`* * *`, `***`, `---`) to pure 0.5s silence without invoking Kokoro TTS.
   - Preserve prosodic and semantic symbols: commas, colons, em-dashes, and currency/percentages.
4. **Thermal Throttling & Thread Safety in `kokoro_synthesizer.py`**:
   - Explicitly configure ONNX Runtime `SessionOptions` with `intra_op_num_threads = 2` and `inter_op_num_threads = 1`.
   - Protect Kokoro session instances with thread-local sessions or synchronization locks.
   - Cap default synthesis concurrency to 1 or 2 workers on macOS to keep CPU temperature $< 70$°C.

## Trade-offs & Alternatives Rejected

- *Rejected: Post-synthesis acoustic alignment patching*: Attempting to detect and fix chopped sentences after audio generation is computationally wasteful and mathematically impossible to align correctly. Fix must be upstream.
- *Rejected: Blindly stripping all non-alphanumeric characters from display cards*: Display cards in the interactive reader should preserve clean visual formatting for human eyes; only the acoustic prompt passed to TTS should be stripped.
- *Rejected: External Calibre CLI heuristics*: External converters cannot be trusted to understand authorial prose boundaries. Upstream stitching must be deterministic in Python.
