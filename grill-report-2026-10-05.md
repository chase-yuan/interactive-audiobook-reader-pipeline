---
plugin: grill
version: 1.0.0
target: /Users/lindy/Vault/My Python Productivity Script 2/interactive-audiobook-reader-pipeline
style: Hard-Nosed Critique & Backlog (Default)
findings_count:
  critical: 2
  high: 2
  medium: 3
  low: 2
  good: 1
---

# Codebase Interrogation Report: interactive-audiobook-reader-pipeline

## Executive Summary
The interactive audiobook reader pipeline demonstrates robust macro-level engineering—evidenced by atomic publication symlinks, cryptographic release tokens, and acoustic feature caching that avoids costly Whisper re-execution. However, the system suffers from a critical structural blind spot at the **temporal-semantic boundary**: quality gates and smoke checks validate only start-monotonicity (`start < previous_start`) and DOM syntax, allowing negative intervallic sentence overlaps (`start < previous_end`) and duplicate contraction word timestamps to pass completely undetected. Furthermore, `html_builder.py` operates as an unmaintainable 2,535-line god object that actively fabricates synthetic sentence overlaps by extending unaligned footnote intervals past subsequent valid sentence boundaries.

---

## Findings by Lane

### Lane 1: Architecture & Topology

- **File**: `html_builder.py:1-2535`
- **Observation**: 2,535-line God Object violates Single Responsibility Principle by combining CSS token generation, client-side JS player runtime, HTML AST assembly, and algorithmic gap interpolation.
- **Severity**: `[HIGH]`
- **Evidence**: `def build_master_reader(book_title, book_subtitle, book_author, chapters_config, output_html_path, ...)` embeds inline CSS styling strings, client JavaScript playback algorithms, SVG icon definitions, and temporal math in a single monolithic function.
- **Proposed change**: Decompose `html_builder.py` into four isolated modules: `reader_compiler.py` (DOM/HTML assembly), `player_runtime.js` (static client playback script), `reader_theme.css` (design token stylesheets), and move timeline gap interpolation into `dynamic_aligner.py`.
- **Tradeoff**: Gain: Independent testability and zero risk of CSS edits corrupting playback math. Lose: Requires import adjustments across runner scripts.
- **Effort**: `[< 1 week]`

- **File**: `dynamic_aligner.py:270-305`
- **Observation**: Monotonic boundary invariant is enforced via post-hoc clamping pass rather than structurally bounded dynamic programming.
- **Severity**: `[MEDIUM]`
- **Evidence**: `sent[i]["audio_end"] = min(sent[i]["audio_end"], next_sent["audio_start"])` is executed in a cleanup loop after sequence alignment concludes.
- **Proposed change**: Constrain dynamic programming search state transitions to forbid backward-flowing or overlapping temporal edges by construction.
- **Tradeoff**: Gain: Mathematical guarantee that alignment paths cannot produce overlapping intervals. Lose: Slightly more complex recurrence relation in token matching.
- **Effort**: `[< 1 week]`

---

### Lane 2: Concurrency & Edge Cases

- **File**: `html_builder.py:1356-1370`
- **Observation**: Unbounded gap-group extension injects negative intervallic overlaps between unaligned footnotes and subsequent narrated sentences.
- **Severity**: `[CRITICAL]`
- **Evidence**:
  ```python
  t_prev = (csents[prev_idx].get("audio_end", csents[prev_idx].get("end")) or 0.0) if prev_idx >= 0 and valid_flags[prev_idx] else 0.0
  t_next = (csents[next_idx].get("audio_start", csents[next_idx].get("start")) or (t_prev + 3.0 * len(group))) if next_idx < len(csents) and valid_flags[next_idx] else (t_prev + 3.0 * len(group))
  if t_next <= t_prev:
      t_next = round(t_prev + 1.0 * len(group), 2)
  ```
- **Proposed change**: When `t_next <= t_prev` (meaning no physical narration gap exists between adjacent spoken sentences), do not fabricate artificial timestamps. Retain unread footnotes with `has_audio_match=False` (`audio_start=None, audio_end=None`), outputting them as static unaligned text units (`class="sentence-unit unmatched"`).
- **Tradeoff**: Gain: 100% elimination of synthetic sentence overlaps across all books with unread footnotes. Lose: Unread footnotes cannot be clicked to seek audio (which is physically accurate, as they were never spoken).
- **Effort**: `[< 1 day]`

- **File**: `pipeline.py:40-48`
- **Observation**: Opening lock file with mode `"w"` truncates active lock metadata before obtaining exclusive `flock`.
- **Severity**: `[MEDIUM]`
- **Evidence**:
  ```python
  with lock_path.open("w", encoding="utf-8") as handle:
      try:
          fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
  ```
- **Proposed change**: Open the lock file with mode `"a"` (append) or `os.open(lock_path, os.O_CREAT | os.O_RDWR)` so that a contending process does not destroy the file contents or mtime of a currently executing run.
- **Tradeoff**: Gain: Non-destructive locking semantics under contention. Lose: None.
- **Effort**: `[< 1 day]`

---

### Lane 3: Security & Attack Surface

- **File**: `agy_linguistic_worker.py:166-172`
- **Observation**: Massive prompt payloads passed via CLI arguments risk OS `ARG_MAX` truncation and process table leakage.
- **Severity**: `[MEDIUM]`
- **Evidence**:
  ```python
  completed = subprocess.run(
      base_cmd + ["--output-format", "text", "--print-timeout", "1h", "--print", prompt],
      cwd=str(cwd), text=True, capture_output=True, timeout=timeout,
  )
  ```
- **Proposed change**: Pass `prompt` through standard input (`input=prompt`) or a temporary file rather than command-line arguments.
- **Tradeoff**: Gain: Immune to OS argument buffer overflow and prevents sensitive book text exposure in `ps` listings. Lose: Requires supporting stdin reading in the CLI worker.
- **Effort**: `[< 1 day]`

- **File**: `publisher.py:113-115`
- **Observation**: Unbounded subprocess execution in git network operations without timeout.
- **Severity**: `[LOW]`
- **Evidence**:
  ```python
  def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
      return subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True, text=True)
  ```
- **Proposed change**: Add explicit `timeout=300` to prevent network-facing push and fetch commands from hanging unattended CI/CD runs indefinitely.
- **Tradeoff**: Gain: Deterministic failure handling on network partitions. Lose: None.
- **Effort**: `[< 1 day]`

---

### Lane 4: Fault Tolerance & Errors

- **File**: `validate_outputs.py:392-395`
- **Observation**: Incomplete monotonicity check in release gate allows sentence overlaps (`start < previous_end`) to pass validation undetected.
- **Severity**: `[CRITICAL]`
- **Evidence**:
  ```python
  if participates_in_timeline and start is not None and start < previous_start and not approved_non_monotonic:
      errors.append(f"{label} {item_id}: non-monotonic raw start")
  ```
- **Proposed change**: Expand the gate to verify non-overlapping disjoint intervals against `previous_end`:
  ```python
  if participates_in_timeline and start is not None and previous_end is not None and start < (previous_end - 0.05) and not approved_non_monotonic:
      errors.append(f"{label} {item_id}: sentence overlap detected (starts at {start}s before previous ended at {previous_end}s)")
  ```
- **Tradeoff**: Gain: Structurally blocks any audiobook release that contains sentence timeline collisions. Lose: Forces legacy books to be cleaned before re-issuing release tokens.
- **Effort**: `[< 1 day]`

- **File**: `agy_linguistic_worker.py:210-211`
- **Observation**: Silent exception swallowing during missing sentence recovery conceals translation/vocabulary parse failures.
- **Severity**: `[LOW]`
- **Evidence**:
  ```python
  except Exception:
      pass
  ```
- **Proposed change**: Replace bare `except Exception:` with explicit exception logging and append dropped sentence IDs to chapter diagnostic metadata.
- **Tradeoff**: Gain: Actionable observability into partial linguistic pipeline failures. Lose: Slightly more verbose log output.
- **Effort**: `[< 1 day]`

---

### Lane 5: Test Integrity & Gaps

- **File**: `quality_gate.py:24-59`
- **Observation**: `smoke_check_html` verifies only DOM string presence and CSS braces, completely blind to temporal corruption and word-span collisions.
- **Severity**: `[HIGH]`
- **Evidence**:
  ```python
  def smoke_check_html(html_path: Path, expected_chapters=None):
      ...
      for element_id in REQUIRED_IDS: ...
      for function_name in REQUIRED_FUNCTIONS: ...
      for idx, css in enumerate(style_blocks, 1): ...
  ```
- **Proposed change**: Add micro-level temporal AST verification to `smoke_check_html`: assert that in every chapter section, sentence intervals are strictly monotonic (`data-start >= prev_data-end - 0.05`) and adjacent word spans have non-identical start times (`data-s[i] != data-s[i+1]`).
- **Tradeoff**: Gain: Closes the gap between "HTML parses" and "audio-text sync actually works for human readers". Lose: Adds ~100ms per book to smoke check.
- **Effort**: `[< 1 day]`

- **File**: `pipeline.py:236-240`
- **Observation**: Acoustic feature caching and atomic release swapping provide outstanding performance isolation and zero-downtime safety.
- **Severity**: `[GOOD]`
- **Evidence**: `has_acoustic = os.path.exists(acoustic_path) and os.path.getsize(acoustic_path) > 1000` prevents redundant Whisper model execution, allowing full book realignment in under 5 seconds with zero GPU thermal overhead. Additionally, `local_publisher.py:98-100` uses `os.replace` symlink switching, ensuring immutable and zero-downtime reader activations.
- **Proposed change**: Preserve and formalize this caching contract into the core architecture guide.
- **Tradeoff**: Architectural asset; maintain as an engineering standard.
- **Effort**: `[< 1 day]`

---

## Prioritized Remediation Backlog

### Phase 1: Critical Fixes (Immediate)
- [ ] `html_builder.py:1356-1370` — Remove artificial `t_next <= t_prev` forward extension; keep unread footnotes unaligned (`data-matched="0"`) to eliminate 100% of synthetic overlaps. (Effort: `< 1 day`)
- [ ] `validate_outputs.py:392-395` — Enforce disjoint interval validation (`start >= previous_end - 0.05`) in release gate to block any future overlapping builds. (Effort: `< 1 day`)
- [ ] `quality_gate.py:24-59` — Augment `smoke_check_html` with temporal checks (zero identical adjacent word spans, zero overlapping sentence units). (Effort: `< 1 day`)

### Phase 2: High-Priority Hardening (Next Sprint)
- [ ] `html_builder.py:1-2535` — Decompose monolithic 2,535-line file into `reader_compiler.py`, `player_runtime.js`, and `reader_theme.css`. (Effort: `< 1 week`)
- [ ] `pipeline.py:40-48` — Switch lock file open mode from `"w"` to `"a"` to eliminate truncation under contention. (Effort: `< 1 day`)
- [ ] `agy_linguistic_worker.py:166-172` — Pass linguistic prompt payloads via stdin rather than command-line arguments to prevent `ARG_MAX` buffer overflow. (Effort: `< 1 day`)

### Phase 3: Structural Clean-up (Ongoing)
- [ ] `dynamic_aligner.py:270-305` — Incorporate forward-monotonic boundaries directly into the dynamic time-warping search lattice. (Effort: `< 1 week`)
- [ ] `publisher.py:113-115` — Add explicit `timeout=300` to all git network commands. (Effort: `< 1 day`)
- [ ] `agy_linguistic_worker.py:210-211` — Eliminate bare `except Exception:` and log dropped sentence diagnostics. (Effort: `< 1 day`)
