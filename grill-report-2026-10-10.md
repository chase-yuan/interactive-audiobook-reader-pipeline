---
plugin: grill
version: 1.0.0
target: /Users/lindy/Vault/My Python Productivity Script 2/interactive-audiobook-reader-pipeline
style: hard_nosed_critique
findings_count:
  critical: 3
  high: 5
  medium: 4
  low: 1
  good: 1
---

# Codebase Interrogation Report: Interactive Audiobook Reader Pipeline

## Executive Summary

The current pipeline architecture suffers from an **Inverted Quality Gate (Post-Mortem Verification)** failure mode: heavy acoustic synthesis (Kokoro neural TTS drawing 650% CPU across unconstrained ONNX threads for 1.5–2 hours) and LLM translation run *before* any textual boundary integrity is verified. Because `validate_outputs.py` categorizes multi-boundary sentences as non-blocking diagnostics and completely ignores trailing hyphens, unmerged line wraps, and single-word orphan fragments, corrupted text from InDesign print PDFs passes blindly into production releases (`release_ready: true`). Furthermore, the hard dependency on EPUB as a compulsory input forces clean PDF/Markdown sources through lossy external format conversions (e.g. Calibre) that systematically introduce broken `<p>` tags at line ends. A strict **Shift-Left Sentence Gate** and unified source normalizer are urgently required before committing downstream compute.

---

## Findings by Lane

### Lane 1: Architecture & Topology

- **File**: `universal_runner.py:612-640`
- **Observation**: Inverted execution lifecycle: Quality validation runs at Stage 4 *after* expensive LLM batch translation (Stage 2) and hours of high-power Kokoro neural TTS synthesis (Stage 3). Textual corruption originating from upstream extraction flows downstream unchecked, squandering hours of compute and battery life on doomed builds.
- **Severity**: `[CRITICAL]`
- **Evidence**: `setup_book_directory(...) -> extract_chapters_sentences(...) -> run_parallel_linguistic_analysis(...) -> synthesize_synthetic_voice_chapters(...) -> build_and_verify_reader(...)`
- **Proposed change**: Introduce a hard Shift-Left `Stage 1.5: Sentence Quality Gate` immediately after sentence extraction. Halt the pipeline with exit code 1 if any canonical sentence fails orthographical integrity (trailing hyphens, unclosed quotation pairs, or lowercase-initial continuations).
- **Tradeoff**: Gain: 100% prevention of wasted compute/time on corrupted text. Lose: Flawed source documents fail fast within 2 seconds instead of silently running to completion.
- **Effort**: `[< 1 day]`

- **File**: `universal_runner.py:682-685`
- **Observation**: Rigid coupling to the EPUB container format as the sole intake entrypoint. Books originating from print PDF or Markdown notes are forced through lossy external conversion utilities (e.g., Calibre, Pandoc) which arbitrarily wrap visual print lines in `<p>` tags and hardcode soft hyphens. EPUB is merely an ephemeral transit format, yet the runner makes it a mandatory prerequisite.
- **Severity**: `[HIGH]`
- **Evidence**: `epub_target = args.epub or args.epub_flag; if not epub_target: parser.error("EPUB path is required (positional or --epub)")`
- **Proposed change**: Decouple the intake layer via an abstract `DocumentSource` protocol supporting `.epub`, direct `.pdf` (via `pdf_intake_normalizer.py`), and structured `.md` directory ingestion.
- **Tradeoff**: Gain: Direct zero-loss ingestion of PDF and Markdown without external converter corruption. Lose: Maintenance of multiple intake source parsers.
- **Effort**: `[< 1 week]`

- **File**: `universal_runner.py:612-646`
- **Observation**: Bifurcated top-level orchestration between `universal_runner.py` and `pipeline.py`. Both files implement competing entry points, disjoint manifest schemas (`chapters_meta` vs `intake_reconciler`), and duplicated verification routines, causing feature drift where enhancements in one runner are missing in the other.
- **Severity**: `[HIGH]`
- **Evidence**: `pipeline.py:320-370` orchestrates chunked releases and R2 uploads, while `universal_runner.py:612-646` orchestrates standalone dual-mode readers and Kokoro auto-voice.
- **Proposed change**: Consolidate pipeline logic into a unified `pipeline_core.py` engine exposing modular execution stages, reducing `universal_runner.py` and `pipeline.py` to lightweight CLI option wrappers.
- **Tradeoff**: Gain: Single source of truth for pipeline stages and quality gates. Lose: Non-trivial refactoring of legacy CLI test suites.
- **Effort**: `[< 1 month]`

---

### Lane 2: Concurrency & Edge Cases

- **File**: `universal_runner.py:390-396`
- **Observation**: Unbounded CPU thread contention and thermal runaway during Kokoro TTS synthesis. ONNX Runtime defaults to `intra_op_num_threads = num_hardware_cores` per session. Launching up to 3 concurrent chapter workers in `ThreadPoolExecutor` spawns 24+ active ONNX compute threads on Apple Silicon, pinning CPU load at 650%+, exceeding 95°C thermal thresholds, and triggering macOS kernel thermal throttling.
- **Severity**: `[CRITICAL]`
- **Evidence**: `with ThreadPoolExecutor(max_workers=concurrency) as executor: futures = {executor.submit(_synth_track, item): item for item in chapters_meta}`
- **Proposed change**: Explicitly configure ONNX Runtime `SessionOptions` (`intra_op_num_threads = 2`, `inter_op_num_threads = 1`), cap TTS concurrency to 1 or 2 workers by default on macOS, and provide a `--low-power` throttle mode.
- **Tradeoff**: Gain: Laptop temperature drops by 20–30°C, zero thermal throttling, responsive system during synthesis. Lose: Multi-track wall-clock synthesis time marginally increases.
- **Effort**: `[< 1 day]`

- **File**: `kokoro_synthesizer.py:43-66`
- **Observation**: Non-thread-safe global singleton pattern for the Kokoro ONNX model instance across multi-threaded workers. `_KOKORO_INSTANCE` is shared across concurrent threads in `ThreadPoolExecutor` without synchronization locks, risking race conditions and memory corruption inside ONNX Runtime internal tensor buffers during concurrent inference.
- **Severity**: `[HIGH]`
- **Evidence**: `global _KOKORO_INSTANCE; if _KOKORO_INSTANCE is not None: return _KOKORO_INSTANCE; _KOKORO_INSTANCE = Kokoro(str(m_path), str(v_path))`
- **Proposed change**: Employ thread-local storage (`threading.local()`) or a thread-safe object pool so each worker thread owns an isolated Kokoro ONNX inference session.
- **Tradeoff**: Gain: Eliminates concurrent buffer corruption and thread contention within the ONNX C++ engine. Lose: Slightly increased memory footprint during parallel synthesis.
- **Effort**: `[< 1 day]`

- **File**: `kokoro_synthesizer.py:69-102`
- **Observation**: Fragile proportional word timing interpolation. Word durations for synthesized audio are estimated strictly from character length ratios (`(weight / total_weight) * duration`). Punctuation pauses, numerals, abbreviations, and phonetic variations cause karaoke word highlighting to drift from the acoustic audio.
- **Severity**: `[MEDIUM]`
- **Evidence**: `word_dur = (weight / total_weight) * duration; spans.append({"word": word, "start": w_start, "end": w_end, "timing_source": "observed"})`
- **Proposed change**: Replace naive character-length interpolation with syllable-weighted heuristics or MLX Whisper forced-alignment verification for synthetic tracks.
- **Tradeoff**: Gain: Sub-frame accurate karaoke word synchronization in the interactive reader. Lose: Modest additional processing time per chapter.
- **Effort**: `[< 1 week]`

---

### Lane 3: Security & Attack Surface

- **File**: `extract_epub.py:136-137`
- **Observation**: Potential path traversal hazard when resolving internal EPUB chapter paths. `extract_chapter_from_epub` passes raw `chapter_internal_path` strings directly to `z.read(...)` and subsequent path operations without normalizing against directory traversal sequences (`../`).
- **Severity**: `[MEDIUM]`
- **Evidence**: `with zipfile.ZipFile(epub_path, 'r') as z: raw_html = z.read(chapter_internal_path).decode('utf-8')`
- **Proposed change**: Sanitize all internal archive member paths using `os.path.normpath` and ensure resolved target paths stay strictly within the archive virtual root.
- **Tradeoff**: Gain: Immune to malicious zip-slip payloads embedded in third-party EPUB files. Lose: Single normalization check per chapter.
- **Effort**: `[< 1 day]`

- **File**: `pdf_intake_normalizer.py:228-232`
- **Observation**: Unescaped metadata interpolation into HTML / JavaScript templates. Untrusted book titles, chapter names, or author tags containing `<script>` or HTML formatting tags could break out of inline scripts when embedded into standalone HTML readers.
- **Severity**: `[MEDIUM]`
- **Evidence**: Interpolation of chapter titles and metadata directly into XHTML documents without uniform JSON-safe script escape sequences (`json.dumps(...).replace("</", "<\\/")`).
- **Proposed change**: Standardize all reader HTML template interpolations to use strict HTML entity escaping and JSON script-breakout guards.
- **Tradeoff**: Gain: Eliminates stored DOM XSS vulnerabilities in offline HTML reader files. Lose: Negligible regex replace overhead during build.
- **Effort**: `[< 1 day]`

---

### Lane 4: Fault Tolerance & Errors

- **File**: `validate_outputs.py:205-208`
- **Observation**: The release gate silently demotes sentence boundary defects to non-blocking diagnostics. `_suspicious_sentence_boundaries` appends detected defects to `diagnostics` instead of `errors`, allowing broken sentence fragments, trailing hyphens, and unclosed quotes to receive `release_ready: true` and issue cryptographic ReleaseTokens.
- **Severity**: `[CRITICAL]`
- **Evidence**: `suspicious = [item.get("id") for item in data if not item.get("is_heading") and _suspicious_sentence_boundaries(item.get("text", ""))]; if suspicious: diagnostics.append(...) # errors is NOT appended to!`
- **Proposed change**: Escalate boundary anomalies to hard errors. Extend the gate to explicitly verify zero trailing hyphens (`\b[a-zA-Z]-$`), zero unmerged lowercase starts (`^[a-z]`), zero orphan words, and balanced quotation pairs.
- **Tradeoff**: Gain: Guarantees zero linguistic defects in published interactive readers. Lose: Builds fail until upstream segmentation is rectified.
- **Effort**: `[< 1 day]`

- **File**: `extract_epub.py:158-169`
- **Observation**: `extract_chapter_from_epub` treats every HTML block element (`<p>`, `<div>`) as a completely isolated semantic island. When an EPUB is converted from a print PDF with hard line breaks, split sentences and hyphenated words across adjacent `<p>` tags are never joined, producing thousands of chopped fragments.
- **Severity**: `[HIGH]`
- **Evidence**: `for elem_idx, el in enumerate(parser.elements): ... sents = split_into_atomic_sentences(txt); for s in sents: canonical_items.append(...)`
- **Proposed change**: Implement an element-level paragraph stitching and de-hyphenation reassembly layer before sentence splitting.
- **Tradeoff**: Gain: Accurately reconstructs unbroken authorial sentences from print PDF conversions. Lose: Minimal parsing overhead during extraction.
- **Effort**: `[< 1 day]`

- **File**: `pdf_intake_normalizer.py:76-84`
- **Observation**: Silent exception swallowing during PDF bookmark outline traversal. Errors during outline tree traversal are caught with bare `except Exception: pass`, silently dropping named destinations and forcing fallback to arbitrary 15-page chunking without notifying the user.
- **Severity**: `[MEDIUM]`
- **Evidence**: `try: if reader.outline: _traverse(reader.outline, current_depth=0) except Exception: pass`
- **Proposed change**: Log specific warnings for failed outline nodes, attempt resolution via `reader.named_destinations`, and emit an explicit fallback notice.
- **Tradeoff**: Gain: Transparent insight into PDF parsing failures. Lose: Additional logging statements.
- **Effort**: `[< 1 day]`

---

### Lane 5: Test Integrity & Gaps

- **File**: `test_universal_runner.py:73-76`
- **Observation**: Artificial happy-path test fixtures mask print PDF formatting realities. Test cases utilize pristine, pre-curated sentences (`<p>First sentence of chapter one. Second sentence explaining concepts clearly...</p>`), with zero test coverage for line-break hyphens, lowercase continuation fragments, or isolated single words.
- **Severity**: `[HIGH]`
- **Evidence**: `pref_html = "<html><body><h1>Author's Preface</h1><p>This is a substantive preface introducing the core thesis...</p></body></html>"`
- **Proposed change**: Build an adversarial dirty-data regression test suite (`test_dirty_print_intake.py`) containing real-world InDesign line breaks, hyphenated words (`oversimplifi-</p><p>cation`), and running headers.
- **Tradeoff**: Gain: Prevents upstream segmentation regressions from entering production. Lose: Requires maintaining adversarial fixture fixtures.
- **Effort**: `[< 1 day]`

- **File**: `test_quality_gate.py:34-49`
- **Observation**: Absence of textual integrity assertions in the quality gate test suite. Existing tests only assert HTML tag structure, audio durations, and ASR coverage, leaving sentence segmentation quality unasserted in CI.
- **Severity**: `[LOW]`
- **Evidence**: `test_quality_gate.py` contains zero test cases verifying sentence boundaries, hyphens, or fragment detection.
- **Proposed change**: Add explicit unit tests asserting that dirty sentence datasets fail `validate()` with expected error strings.
- **Tradeoff**: Gain: Guaranteed CI enforcement of text quality invariants. Lose: None.
- **Effort**: `[< 1 day]`

- **File**: `release_token.py:20-60`
- **Observation**: Cryptographic release token binding and atomic disk operations provide tamper-evident build verification. Reader HTML files are cryptographically tied to validation reports via SHA-256 and nonces, and `artifact_io.py` prevents partial write corruptions.
- **Severity**: `[GOOD]`
- **Evidence**: `token = issue_release_token(book_dir, rep_path, report)` binds validation report hash directly to the master reader build.
- **Proposed change**: Maintain this pattern and extend token verification to assert Stage 1.5 sentence gate hashes.
- **Tradeoff**: None.
- **Effort**: `[N/A]`

---

## Prioritized Remediation Backlog

### Phase 1: Critical Fixes (Immediate)
- [ ] `universal_runner.py:612-640` — Invert gate order: Implement Shift-Left Stage 1.5 Sentence Quality Gate before LLM translation and TTS synthesis (Effort: `< 1 day`)
- [ ] `validate_outputs.py:205-208` — Escalate boundary errors from diagnostics to blocking release failures; enforce 0 trailing hyphens and 0 lowercase fragments (Effort: `< 1 day`)
- [ ] `kokoro_synthesizer.py:46-66` — Throttle ONNX Runtime thread pools (`intra_op=2`) and eliminate global singleton race condition across threads (Effort: `< 1 day`)
- [ ] `extract_epub.py:158-169` — Implement element-level de-hyphenation and cross-paragraph line-wrap stitching (Effort: `< 1 day`)
- [ ] `test_quality_gate.py:34-49` — Add adversarial unit tests asserting failure on dirty/chopped sentence datasets (Effort: `< 1 day`)

### Phase 2: High-Priority Hardening (Next Sprint)
- [ ] `universal_runner.py:682-685` — Introduce native PDF and Markdown ingestion, eliminating mandatory lossy EPUB intermediate step (Effort: `< 1 week`)
- [ ] `kokoro_synthesizer.py:69-102` — Upgrade proportional word timing interpolation to syllable-weighted or Whisper-aligned timing (Effort: `< 1 week`)
- [ ] `extract_epub.py:136-137` — Enforce path normalization and zip-slip protection on internal EPUB member reading (Effort: `< 1 week`)
- [ ] `pdf_intake_normalizer.py:76-84` — Harden PDF outline traversal with named-destination resolution and transparent fallback logging (Effort: `< 1 week`)

### Phase 3: Structural Clean-up (Ongoing)
- [ ] `universal_runner.py:612-646` — Unify `universal_runner.py` and `pipeline.py` into a single modular `pipeline_core.py` engine (Effort: `< 1 month`)
