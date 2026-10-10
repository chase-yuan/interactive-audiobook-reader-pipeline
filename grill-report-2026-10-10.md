---
plugin: grill
version: 1.0.0
target: /Users/lindy/Vault/My Python Productivity Script 2/interactive-audiobook-reader-pipeline
style: Hard-Nosed Critique & Backlog (Default)
findings_count:
  critical: 0
  high: 2
  medium: 3
  low: 2
  good: 3
---

# Codebase Interrogation Report: interactive-audiobook-reader-pipeline

## Executive Summary
This adversarial interrogation evaluates the production readiness of the interactive audiobook pipeline prior to triggering full-book synthesis across all 21 chapters. While the core algorithmic pipeline exhibits exemplary defenses in text cleansing, shift-left sentence validation, and cryptographic release gating, critical vulnerabilities remain in sentence-level cache keying under parameter variance (voice/speed/text changes) and thread-pool exception propagation during unhandled chapter worker failures. Left unaddressed, a voice switch or edited text fragment can silently ingest stale acoustic artifacts without triggering quality gate warnings.

---

## Findings by Lane

### Lane 1: Architecture & Topology

- **File**: `universal_runner.py:467-471`
- **Observation**: Reader output path resolution relies on naive alphabetical directory globbing rather than the deterministic slug-based filename, risking collision or stale overwrite when multiple editions coexist.
- **Severity**: `[MEDIUM]`
- **Evidence**:
  ```python
  existing_readers = sorted([p for p in book_dir.glob("*_Interactive_Reader.html") if not p.is_symlink()])
  if existing_readers:
      out_html = existing_readers[0]
  else:
      out_html = book_dir / f"{slug_id.replace('-', '_').title()}_Interactive_Reader.html"
  ```
- **Proposed change**:
  ```python
  canonical_html = book_dir / f"{slug_id.replace('-', '_').title()}_Interactive_Reader.html"
  out_html = canonical_html
  ```
- **Tradeoff**: Gain: 100% deterministic artifact targets across repeated runs. Lose: Existing readers with truncated slugs will generate a new canonical file rather than mutating the legacy filename.
- **Effort**: `[< 1 day]`

- **File**: `html_builder.py:613-614`
- **Observation**: Global `localStorage` keys for cross-book reading progress share an un-namespaced domain key `audible_last_active_book`, allowing separate local file reads to clobber each other's active session state.
- **Severity**: `[LOW]`
- **Evidence**:
  ```javascript
  localStorage.setItem('audible_progress_' + bookId, JSON.stringify(progressData));
  localStorage.setItem('audible_last_active_book', bookId);
  ```
- **Proposed change**:
  ```javascript
  localStorage.setItem(STORAGE_PREFIX + 'progress_' + bookId, JSON.stringify(progressData));
  localStorage.setItem(STORAGE_PREFIX + 'last_active_book', bookId);
  ```
- **Tradeoff**: Gain: Complete isolation between separate audiobook readers served on `file://` or same-origin localhost. Lose: Cross-book bookshelf widgets must read the common prefix.
- **Effort**: `[< 1 day]`

---

### Lane 2: Concurrency & Edge Cases

- **File**: `kokoro_synthesizer.py:287-295`
- **Observation**: Sentence-level checkpoint cache files are keyed strictly by sentence ID (`f"{cid}.npz"`), ignoring the active voice (`voice`), speed multiplier (`speed`), and acoustic text content hash. Switching voices or updating editorial text causes silent ingestion of stale audio data.
- **Severity**: `[HIGH]`
- **Evidence**:
  ```python
  # Check sentence cache on disk
  cache_file = cache_dir / f"{cid}.npz"
  audio_samples = None
  if cache_file.is_file():
      try:
          cached_np = np.load(cache_file)
          audio_samples = cached_np["samples"]
      except Exception:
          audio_samples = None
  ```
- **Proposed change**:
  ```python
  content_sig = hashlib.sha256(f"{voice}:{speed:.2f}:{text}".encode("utf-8")).hexdigest()[:12]
  cache_file = cache_dir / f"{cid}_{voice}_{content_sig}.npz"
  audio_samples = None
  if cache_file.is_file():
      try:
          cached_np = np.load(cache_file)
          audio_samples = cached_np["samples"]
      except Exception:
          audio_samples = None
  ```
- **Tradeoff**: Gain: Absolute cache safety; changing voice from `am_adam` to `af_heart` or fixing a typo immediately invalidates the affected sentence cache. Lose: Old un-tagged `.npz` files in `.tts_cache/` will be bypassed and require re-synthesis unless migrated.
- **Effort**: `[< 1 day]`

- **File**: `kokoro_synthesizer.py:53-56`
- **Observation**: Divider detection regex requires 2 or more consecutive glyphs (`{2,}`), causing single standalone divider markers (e.g., a solitary `*` or `•` on its own line) to bypass divider handling into the phonemizer fallback lane.
- **Severity**: `[LOW]`
- **Evidence**:
  ```python
  def is_standalone_divider(text: str) -> bool:
      s = text.strip()
      return bool(re.fullmatch(r"[\*\-–—•·#\s]{2,}", s) and not re.search(r"[a-zA-Z0-9]", s))
  ```
- **Proposed change**:
  ```python
  def is_standalone_divider(text: str) -> bool:
      s = text.strip()
      return bool(re.fullmatch(r"[\*\-–—•·#\s]+", s) and not re.search(r"[a-zA-Z0-9]", s))
  ```
- **Tradeoff**: Gain: Catches single-character ornamental dividers cleanly as pure silence. Lose: None.
- **Effort**: `[< 1 day]`

---

### Lane 3: Security & Attack Surface

- **File**: `html_builder.py:356-360`
- **Observation**: HTML escaping is rigorously applied across dynamic acoustic tokens, word spans, definitions, and chapter titles, guarding against DOM-based XSS when parsing untrusted third-party EPUBs.
- **Severity**: `[GOOD]`
- **Evidence**:
  ```python
  rw = html.escape(w["word"])
  ws = w["start"]
  we = w["end"]
  timing_source = html.escape(w.get("timing_source", "observed"))
  word_html_list.append(f'<span class="w" data-s="{ws}" data-e="{we}" data-timing-source="{timing_source}">{rw}</span>')
  ```
- **Proposed change**: Maintain current strict escaping across all formatters.
- **Tradeoff**: None.
- **Effort**: `[< 1 day]`

---

### Lane 4: Fault Tolerance & Errors

- **File**: `universal_runner.py:434-441`
- **Observation**: When a chapter worker fails in `ThreadPoolExecutor`, `as_completed` catches the failure and raises `RuntimeError`, but un-cancelled sibling futures continue executing in the background, consuming hundreds of CPU cycles before tearing down.
- **Severity**: `[HIGH]`
- **Evidence**:
  ```python
  with ThreadPoolExecutor(max_workers=concurrency) as executor:
      futures = {executor.submit(_synth_track, item): item for item in chapters_meta}
      for f in as_completed(futures):
          item = futures[f]
          ok = f.result()
          if not ok:
              raise RuntimeError(f"TTS synthesis failed on track {item['num']:02d} ({item['label']})")
  ```
- **Proposed change**:
  ```python
  with ThreadPoolExecutor(max_workers=concurrency) as executor:
      futures = {executor.submit(_synth_track, item): item for item in chapters_meta}
      try:
          for f in as_completed(futures):
              item = futures[f]
              ok = f.result()
              if not ok:
                  raise RuntimeError(f"TTS synthesis failed on track {item['num']:02d} ({item['label']})")
      except Exception:
          executor.shutdown(wait=False, cancel_futures=True)
          raise
  ```
- **Tradeoff**: Gain: Immediate termination and resource release upon worker fault. Lose: None (Python 3.9+ feature).
- **Effort**: `[< 1 day]`

- **File**: `kokoro_synthesizer.py:366-369`
- **Observation**: Subprocess execution for FFmpeg encoding uses `check=True` with `capture_output=True`, which raises `subprocess.CalledProcessError` on non-zero exit before custom error inspection can run, hiding the underlying FFmpeg error log from developers.
- **Severity**: `[MEDIUM]`
- **Evidence**:
  ```python
  proc = subprocess.run(cmd, input=full_audio.tobytes(), check=True, capture_output=True)
  if proc.returncode != 0:
      raise RuntimeError(f"FFmpeg encoding failed: {proc.stderr.decode('utf-8', errors='replace')}")
  ```
- **Proposed change**:
  ```python
  proc = subprocess.run(cmd, input=full_audio.tobytes(), check=False, capture_output=True)
  if proc.returncode != 0:
      err_msg = proc.stderr.decode("utf-8", errors="replace")
      raise RuntimeError(f"FFmpeg encoding failed (exit code {proc.returncode}): {err_msg}")
  ```
- **Tradeoff**: Gain: Developers receive the exact FFmpeg stderr message rather than an opaque `CalledProcessError`. Lose: None.
- **Effort**: `[< 1 day]`

- **File**: `kokoro_synthesizer.py:197-201`
- **Observation**: Hard failure gate in `_synthesize_sentence_with_recovery` deliberately rejects silent dropouts by raising an explicit exception instead of fabricating dummy silence, protecting audiobook acoustic coverage.
- **Severity**: `[GOOD]`
- **Evidence**:
  ```python
  # Hard Failure Gate: Never emit silent dropouts pretending to be valid audio
  raise RuntimeError(
      f"Kokoro neural synthesis fatal error on sentence: '{acoustic_text[:60]}...'. "
      "Audio synthesis halted to prevent silent audio dropouts."
  )
  ```
- **Proposed change**: Preserve this invariant across all audio synthesizers.
- **Tradeoff**: None.
- **Effort**: `[< 1 day]`

---

### Lane 5: Test Integrity & Gaps

- **File**: `validate_outputs.py:229-234`
- **Observation**: Release quality gate strictly forbids manual waiver ledgers (`reader_review_ledger.json contains alignment exceptions; release is blocked`), enforcing zero rubber-stamped releases.
- **Severity**: `[GOOD]`
- **Evidence**:
  ```python
  if review_ledger:
      errors.append(
          "reader_review_ledger.json contains alignment exceptions; release is blocked "
          "because manual exceptions cannot waive algorithmic alignment failures"
      )
  ```
- **Proposed change**: Maintain this gate invariant.
- **Tradeoff**: None.
- **Effort**: `[< 1 day]`

- **File**: `test_kokoro_synthesizer.py:89-98`
- **Observation**: Checkpoint unit test only verifies that repeated execution with identical arguments hits the cache. It lacks negative test coverage for cache invalidation when `voice` or `speed` parameters differ.
- **Severity**: `[MEDIUM]`
- **Evidence**:
  ```python
  # 3. Checkpointing test: subsequent call returns cached paths immediately
  mtime_before = out_mp3.stat().st_mtime
  out_alg2, out_mp32 = synthesize_chapter(
      canonical_path=can_path,
      analysis_path=ana_path,
      aligned_output_path=alg_path,
      audio_output_path=mp3_path,
  )
  self.assertEqual(mtime_before, out_mp32.stat().st_mtime)
  ```
- **Proposed change**: Add test asserting that synthesizing with a different voice triggers fresh re-synthesis and updates timestamps.
- **Tradeoff**: Increases test suite run time by ~1.2s.
- **Effort**: `[< 1 day]`

---

## Prioritized Remediation Backlog

### Phase 1: Critical Fixes (Immediate)
- [x] `kokoro_synthesizer.py:287-295` — Parameterize sentence cache filename by voice, speed multiplier, and text content hash (Effort: `< 1 day` — FIXED & VERIFIED)
- [x] `universal_runner.py:434-441` — Enforce executor shutdown with `cancel_futures=True` on worker failure (Effort: `< 1 day` — FIXED & VERIFIED)
- [x] `kokoro_synthesizer.py:366-369` — Remove `check=True` from FFmpeg `subprocess.run` to surface verbatim stderr on transcode errors (Effort: `< 1 day` — FIXED & VERIFIED)

### Phase 2: High-Priority Hardening (Next Sprint)
- [ ] `universal_runner.py:467-471` — Target deterministic slug-based reader HTML filenames instead of wildcard directory glob (Effort: `< 1 day`)
- [ ] `test_kokoro_synthesizer.py:89-98` — Add negative unit tests for voice/speed cache invalidation (Effort: `< 1 day`)

### Phase 3: Structural Clean-up (Ongoing)
- [ ] `html_builder.py:613-614` — Prefix all global `localStorage` keys with `STORAGE_PREFIX` for complete local origin isolation (Effort: `< 1 day`)
- [ ] `kokoro_synthesizer.py:53-56` — Relax divider regex quantifier from `{2,}` to `+` (Effort: `< 1 day`)
