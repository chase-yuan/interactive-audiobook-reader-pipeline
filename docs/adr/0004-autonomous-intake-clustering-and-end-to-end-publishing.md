# 4. Architecture Decision Record: Autonomous Raw-Material Intake, Dynamic Macro-Track Clustering, and One-Click Industrial Publishing

- **Status**: Accepted
- **Date**: 2026-10-24
- **Deciders**: Chief Pipeline Architect & Autonomous Industrial Engineering

---

## 1. Context & Problem Statement

The design goal of the Interactive Audiobook Reader Pipeline is **one-click, zero-human-in-the-loop industrial delivery**: an engineer or autonomous agent executes a single command with raw inputs (an EPUB file and commercial audio tracks), and the pipeline runs through extraction, linguistic analysis, acoustic alignment, quality gatekeeping, R2 CDN sync, chunked Audible portal publishing, and keygen passkey emission without stopping for manual intervention.

In real-world commercial production (exemplified by high-density non-fiction titles such as Nassim Nicholas Taleb's *Antifragile*), raw material ingestion encountered four systemic architectural failure modes:

1. **Fragile Audio Track Resolution**:
   - Commercial audiobooks employ diverse, unpredictable filename conventions:
     - Book prefix + 3-digit track: `Antifragile Things That Gain from Disorder (Unabridged) - 001.mp3`
     - Bare numbers: `001.mp3`, `01.mp3`, `1.mp3`
     - Multi-disc/track tokens: `CD1_01.mp3`, `Disc 1 - 01.mp3`, `Track 01.mp3`, `Part 01.mp3`
     - Title-prefixed tokens: `01 - Introduction.mp3`, `01. The Beginning.mp3`
   - Existing `audio_resolver.py` used a rigid regex `(?<!\d)(?:chapter|ch)[ _-]*0*{chapter_number}(?!\d)` and hard-coded `*.mp3` globbing. It failed on 3-digit padded numbers, book-prefixed names, and modern `.m4b`/`.m4a` containers, immediately aborting execution with `missing audio`.

2. **Structural Asymmetry: Fragmented EPUB vs Macro Audio Tracks**:
   - Commercial publishers and Calibre converters routinely chop prose into hundreds of fine-grained HTML fragments (e.g. *Antifragile* contains 202 spine files: `index_split_000.html` to `index_split_201.html`).
   - Conversely, commercial audiobooks are mastered into $M$ macro tracks (e.g. 34 MP3 files of 10–35 minutes each).
   - Ingesting spine items 1:1 caused immediate pipeline failure:
     - Tracks 35–202 failed with `FileNotFoundError: No matching studio audio file found for Chapter 35`.
     - Early fragments (e.g. 500 characters) matched against 25-minute audio files suffered catastrophic bilateral acoustic word ratio collapses ($< 10\% \ll 85\%$), halting the gatekeeper.
   - Theoretical dynamic programming reconciliation in `intake_reconciler.py` was artificially restricted to `max_group: 3`, required external pre-generated probes, and was never wired into `universal_runner.py`.

3. **Acoustic Gatekeeper Blindspot on Unread Tables and Marginalia**:
   - Analytical, mathematical, and philosophical literature contains extensive tabular data (e.g. Taleb's *Antifragile* Table 1 "The Triad" has 30 rows of multi-column classifications), mathematical proofs, footnotes, and sidebars.
   - Audiobook narrators do not read out 30 rows of raw table cells; they speak the table title or transition straight to prose.
   - `extract_epub.py` parsed every table row into individual canonical sentences. When unread, Whisper forced alignment produced zero acoustic word spans.
   - `validate_outputs.py` classified these as unaligned errors (`review-required`), dropping acoustic coverage below 95%.
   - Furthermore, the gatekeeper enforced a hard ceiling (`MAX_NON_NARRATED_CHAPTER_COUNT = 60`, `MAX_NON_NARRATED_CHAPTER_RATIO = 0.20`), while explicitly rejecting manual review waivers (`reader_review_ledger.json`). Consequently, legitimate books containing large unread reference tables were permanently blocked from release.

4. **Fragmented Execution & Incomplete Autonomous Delivery**:
   - Generation of local HTML was treated as an exit point rather than an intermediate checkpoint.
   - Release required multiple fragmented commands: manual directory structuring, running `pipeline.py --publish`, executing `publish_book.py`, and invoking `keygen.py`.
   - Any failure along the chain required human diagnosis and intervention.

---

## 2. Decision & Architecture Blueprint

### 2.1 Resilient Global Audio Discovery Engine (`audio_resolver.py`)

Replace isolated regex file probing with a **Two-Phase Audio Profiling & Track Binding Engine**:

```
[Raw Audio Directory]
         │
         ▼
[Phase 1: Global Audio Pool Profiler]
  ├─ Collect all supported extensions: .mp3, .m4a, .m4b, .aac, .flac, .opus
  ├─ Natural Alphanumeric Sort (re.split(r'(\d+)'))
  ├─ Metadata Extraction (ffprobe duration + ID3 track/title tags)
  ├─ Naming Pattern Classification (prefix, delimiter, zero-padding width)
  └─ Build 1-Indexed Track Index Table: { 1: Track_01, 2: Track_02, ..., M: Track_M }
         │
         ▼
[Phase 2: Cascade Resolver (chapter_number -> AudioResolution)]
  ├─ Priority 1: Exact keyword match (chapter_01, ch01)
  ├─ Priority 2: Direct lookup in 1-Indexed Track Index Table (e.g. - 001.mp3 -> 1)
  ├─ Priority 3: Ordinal position match (pool[chapter_number - 1])
  └─ Priority 4: Semantic tag/title correlation (ID3 title vs Chapter heading)
```

- **Invariant**: As long as the audio directory contains $M$ audio files in sequential order, track binding succeeds 100% deterministically regardless of filename variance.

---

### 2.2 Autonomous Triangulated EPUB Auto-Clustering Engine (`intake_reconciler.py`)

When the pipeline ingests an EPUB with $N$ spine documents and $M$ audio files where $N > M$, it activates the **Autonomous Triangulated Clustering Engine** without human prompting:

```
[EPUB: N Micro Fragments]                       [Audio: M Macro Tracks]
           │                                               │
           ├────────────┐                     ┌────────────┤
           ▼            ▼                     ▼            ▼
      [TOC Tree]   [Text Chars]         [Duration]   [Fast ASR Probes]
     (NCX / NAV)   (CDF Mass)           (CDF Mass)  (MLX Whisper 30s Head/Tail)
           │            │                     │            │
           └──────┬─────┴─────────────────────┴─────┬──────┘
                  │                                 │
                  ▼                                 ▼
         [Triangulated Boundary Optimization (Dynamic Programming)]
           Score(i..k -> Track j) = 0.50 * AnchorSimilarity(Head/Tail)
                                  + 0.30 * DurationProportionMatch
                                  + 0.20 * TOCHeadingWeight
                  │
                  ▼
         [M Clustered Macro Tracks]
           Cluster j = Concat(Fragment i, ..., Fragment k)
                  │
                  ▼
         [Synthesized Canonical Sentence Streams]
           book_ch01_canonical_sentences.json (1..M 1:1 with Audio Tracks)
```

1. **High-Speed Autonomous Boundary Probing**:
   - Uses Apple Silicon `mlx_whisper` to probe the head (first 30s) and tail (last 30s) of each audio track.
   - Multi-threaded execution across unified memory completes 68 probes for 34 tracks in $< 15$ seconds.
2. **Cumulative Mass CDF Alignment**:
   - Audio duration and text character length exhibit Pearson correlation $r > 0.99$.
   - The engine defines a search window $\Delta$ around the expected character boundary $\mu = \frac{C_{\text{total}}}{D_{\text{total}}}$ to bound computation.
3. **Canonical Sentence Synthesis**:
   - Fragments belonging to cluster $j$ are stitched seamlessly.
   - Sentences are monotonically re-indexed (`s-0`, `s-1`, ..., `s-K`).
   - Cluster heading metadata is extracted from the primary TOC level.
   - Output: Downstream modules (linguistic analysis, forced alignment, HTML builder) operate on $M$ macro chapters that map 1:1 to audio tracks.

---

### 2.3 Structural Table & Marginalia Acoustic Exemption Gatekeeper

Decouple **Visual Completeness** from **Acoustic Timeline Participation**:

```
[EPUB Parsing] ──> Tag Detection: <table>, <tr>, <td>, <aside>, <figure>
                         │
                         ▼
             canonical_sentences.json:
               { "id": "s-15", "tag": "td", "is_tabular": true, "text": "..." }
                         │
                         ▼
[Stage 3: Dynamic Forced Aligner]
  ├─ Narrator reads prose around table:
  │    Prev sentence ends at T_start; Next sentence begins at T_end.
  ├─ Whisper ASR confirms zero phonetic tokens for table cells between T_start and T_end.
  └─ Aligner marks table units:
       {
         "alignment_status": "not-applicable",
         "alignment_reason": "structural_tabular_omitted_by_narrator",
         "is_tabular": true,
         "has_audio_match": false
       }
                         │
                         ▼
[Stage 4: Quality Gatekeeper (validate_outputs.py)]
  ├─ Exclude validated structural tables & marginalia from acoustic coverage denominator.
  ├─ Exclude validated tabular omissions from MAX_NON_NARRATED_CHAPTER_RATIO ceiling.
  └─ Invariant: 20% omission ceiling strictly guards against UNEXPLAINED prose omissions.
                         │
                         ▼
[Compiled Reader (html_builder.py)]
  ├─ Tables remain 100% visible, fully styled, and bilingually translated.
  └─ Karaoke playback skips over unread cells smoothly without timeline desync.
```

- **Zero-Rubber-Stamp Invariant**: Acoustic exemption is granted strictly through **objective physical tag provenance** (`is_tabular: true`) combined with **bilateral acoustic timeline continuity**, eliminating arbitrary manual waiver files.

---

### 2.4 End-to-End Autonomous Publishing Assembly Line

The pipeline enforces a single, unbroken execution flow:

```
[Raw EPUB + Audio Directory]
              │
              ▼  (universal_runner.py / pipeline.py --publish)
[Stage 1: Autonomous Ingestion & Clustering] (N -> M alignment)
              │
              ▼
[Stage 1.5: Shift-Left Sentence Integrity Gate] (Zero broken sentences)
              │
              ▼
[Stage 2: Parallel High-Throughput Linguistic Worker] (Bilingual + CEFR B2/C1/C2)
              │
              ▼
[Stage 3: MLX Whisper Forced Alignment & Structural Table Exemption]
              │
              ▼
[Stage 4: Quality Gatekeeper & Cryptographic ReleaseToken Issuance]
              │
              ▼
[Stage 5: Master Bilingual Interactive Reader Compilation]
              │
              ▼
[Stage 6: Cloudflare R2 Audio CDN Synchronization] (HTTP 206 range verified)
              │
              ▼
[Stage 7: Chunked Production Release Sealing] (books/<id>/, manifest.json, rights/)
              │
              ▼
[Stage 8: Production Git Push & Keygen Dispatch Emission]
              │
              ▼
[Output: Live Production URL + Customer Passkey on Clipboard]
```

---

## 3. Trade-offs & Alternatives Considered

1. **Alternative: Requiring human manual chapter mapping configuration (`--manifest`)**:
   - *Rejected*: Violates the core principle of autonomous industrial engineering. An industrial pipeline must digest raw commercial artifacts without requiring users to craft JSON manifests by hand.
2. **Alternative: Blindly flattening the EPUB into a single giant text and running Whisper across the entire audiobook**:
   - *Rejected*: Monolithic forced alignment across 15+ hours of audio has quadratic complexity, high memory footprint, and catastrophic error propagation if drift occurs. Macro-track clustering provides localized error isolation ($O(M)$ independent tracks).
3. **Alternative: Deleting unread tables and notes from the reader HTML**:
   - *Rejected*: The interactive reader is an Apple Books-grade educational tool. Discarding tables, diagrams, or authorial notes ruins the reader's scholarship and aesthetic value. Tables must remain visible and translated.
4. **Alternative: Loosening the acoustic coverage gate to 70%**:
   - *Rejected*: Lowering global coverage hides real transcription and alignment bugs. The solution is semantic tag awareness (`is_tabular: true`), not lowering quality standards.

---

## 4. Verification & Hard Invariants

1. **AP0–AP5 Aesthetic Principle Zero Protocol**:
   - Clustered readers must satisfy 100% tokenized CSS, boxless architecture, zero-jitter typography, and zero decorative emojis.
2. **Deterministic Reproducibility**:
   - `intake_cluster_manifest.json` records SHA-256 digests of all input fragments and audio tracks. Re-running the pipeline on identical inputs yields identical track groupings.
3. **Physical Playback & Acoustic Lead Tolerance**:
   - Every audio track bound via the auto-clustering engine must pass `check_acoustic_lead_silence` (mean lead $\le 0.10$s) and `check_audio_physical_integrity`.
4. **Gatekeeper Delivery Invariant**:
   - When `--publish` is specified, the pipeline terminates only upon successful Git push to production and emission of the live passkey. It never pauses at the intermediate local HTML stage.
