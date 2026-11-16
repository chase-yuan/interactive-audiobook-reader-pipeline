# Interactive Audiobook Reader Pipeline

<p align="center">
  <b>The Apple Books-grade bilingual interactive reader and acoustic synchronization pipeline, engineered natively for macOS and Apple Silicon.</b><br>
  <i>Features word-level acoustic synchronization, full-keyboard interactive shadow typing, single-sentence focus cabins, and cryptographic release quality gates.</i>
</p>

<p align="center">
  <a href="README.md">简体中文</a> | <a href="README_EN.md"><b>English</b></a>
</p>

<p align="center">
  <a href="https://audiblelibrary.online/books/the-psychology-of-money/"><img src="https://img.shields.io/badge/Live%20Demo-audiblelibrary.online-4338ca?style=flat-square&logo=safari&logoColor=white" alt="Live Demo"></a>
  <a href="https://apple.com"><img src="https://img.shields.io/badge/Platform-macOS%2013%2B-0f172a?style=flat-square&logo=apple&logoColor=white" alt="Platform"></a>
  <a href="https://apple.com"><img src="https://img.shields.io/badge/Architecture-Apple%20Silicon%20(M1--M5)-334155?style=flat-square" alt="Hardware"></a>
  <a href="https://github.com/ml-explore/mlx"><img src="https://img.shields.io/badge/Engine-Apple%20MLX%20Whisper-0284c7?style=flat-square" alt="Engine"></a>
  <a href="https://github.com/chase-yuan/interactive-audiobook-reader-pipeline"><img src="https://img.shields.io/badge/Tests-245%20Passed-10b981?style=flat-square" alt="Tests"></a>
  <a href="https://github.com/chase-yuan/interactive-audiobook-reader-pipeline"><img src="https://img.shields.io/badge/Gate-Cryptographically%20Verified-475569?style=flat-square" alt="Quality Gate"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-64748b?style=flat-square" alt="License"></a>
</p>

---

## Core Design Philosophy: Why Build This Tool?

This project was born out of a personal exploration into focus, embodied learning, and cognitive learning science during deep bilingual reading:

1. **Dual-Modal Immersion for Laser Focus**: Reading alone often leads to mind-wandering; passive listening often leads to zone-outs. By reading text while listening to studio narration, dual-channel sensory input locks cognitive bandwidth into deep, sustained immersion.
2. **Kinetic Word Tracking as a Visual Anchor**: Real-time highlighting that leaps word-by-word with the audio narration provides an unshakeable visual anchor, completely eliminating the cognitive friction of losing one's place or trailing off.
3. **Pure English Mode: Embracing "Desirable Difficulty"**: By keeping the interface in pure English by default, the brain is deprived of premature crutches. This introduces the cognitive psychological concept of *desirable difficulty*, training the mind to process English directly in context.
4. **On-Demand Bilingual Mode: Dynamic Cognitive Unloading**: Effective learning requires challenge without burnout. The reader allows seamless toggle between pure English and sentence-level bilingual translation on demand, unloading cognitive fatigue during dense chapters.
5. **Interactive Shadow Typing: From Passive Input to Embodied Muscle Memory**: Understanding is not mastery. Through full-keyboard sentence-by-sentence typing while listening, sentence rhythms, idiomatic phrasing, and spelling are anchored directly into physical muscle memory.
6. **Contextual Idiomatic Translation & Nuance Breakdown**: Moving beyond rigid machine translation, nuance cards provide literary-grade idiomatic translations alongside CEFR C1/C2 vocabulary annotations, parts of speech, and phonetic IPA transcripts.

---

## 🚀 Key Features Matrix

### 1. ⌨️ Interactive Shadow Typing Engine
- **Monkeytype-Grade Mechanical Audio Feedback**: Authentic tactile acoustic sound packs (Blue/Brown switch emulation) for satisfying tactile immersion;
- **Zero Layout Shift (CLS = 0)**: Physically locked word-box dimensions guarantee that keystrokes never cause visual word wrapping, text pushing, or layout jitter;
- **Smart Punctuation & Space Auto-Absorption**: Spacebar automatically absorbs commas, periods, and hyphens for pure, uninterrupted flow typing;
- **Cloze Keyword Cloze Mode**: Automatically masks CEFR key vocabulary words to train Active Recall during narration;
- **Live Performance Projection**: Real-time WPM, keystroke accuracy, vocabulary typed counters, and ultra-fine acoustic progress lines.

### 2. 🎯 Single Sentence Focus Cabin
- **Zero Visual Distractions**: Instantly collapses long prose paragraphs into an isolated, high-contrast single sentence card;
- **Stepped Font Size Scaler**: Seamlessly step font sizes up or down with keyboard shortcuts (`+` / `-`) for ergonomic desktop and mobile reading;
- **Unified Keyboard Navigation**: Space to play/pause, Left/Right arrows to step sentences, Enter to toggle bilingual annotations.

### 3. 🛡️ Industrial Red-Team Acoustic Continuity Gates
- **Zero Human Testers Policy**: Built-in automated auditor `test_library_acoustic_continuity.py` inspects **34 books (905 chapters) in 1.2 seconds**;
- **Leading Speech Void Sniffing**: Non-ch1 speech delays strictly bounded to `< 4.0s` to capture unindexed chapter summaries and prologues;
- **Inter-Sentence Void Gates**: Automatically detects and blocks releases with unhandled `> 6.0s` silence (missing tables, sidebar callouts, or dropped paragraphs);
- **Automated Front-Matter Stitching**: Seamlessly extracts and aligns EPUB front-matter summaries to chapter audio headers.

### 4. 🧠 Dual Neural Speech Architecture
- **Apple Silicon Native Forced Alignment**: Direct integration with Apple's official `mlx-whisper` leverages Unified Memory on M-series chips for sub-millisecond word boundaries;
- **High-Definition Neural Speech**: Built-in Microsoft Edge HD neural voices (`BrianMultilingualNeural`) with 10x parallel pre-fetch and offline 82M Onnx Kokoro neural synthesis.

---

## 30-Second Quick Start

The repository includes a built-in public-domain demo (*The Art of War*, English translation). Runs entirely on the Python 3 standard library:

```bash
# 1. Clone the repository
git clone https://github.com/chase-yuan/interactive-audiobook-reader-pipeline.git
cd interactive-audiobook-reader-pipeline

# 2. Build the interactive reader (Zero external dependencies)
python3 universal_runner.py demo/sample.epub --text-only
```

---

## Production Modes

### Mode 1: Pure Text Bilingual Reader (`--text-only`)
For books without studio audio. Generates bilingual readers with vocabulary annotations and keyboard navigation:

```bash
python3 universal_runner.py /path/to/book.epub --text-only --concurrency 8 --book-dir ./my_book
```

### Mode 2: Studio Audio Interactive Reader (`complete`)
Combines EPUB text with studio narration (`.mp3` or `.m4a`) via Apple Silicon MLX forced alignment:

```bash
# Install Apple Silicon MLX acoustic support
pip install -e '.[acoustic]'

# Compile the full audiobook interactive reader
python3 universal_runner.py --epub /path/to/book.epub --audio-dir /path/to/mp3s --book-dir ./my_book
```

### Mode 3: Autonomous Neural Voice Synthesis (`TTS`)
For books without studio recordings, synthesizes broadcast-grade narration and alignments:

```bash
python3 universal_runner.py /path/to/book.epub --book-dir ./my_book
```

---

## Apple Silicon Unified Memory Acceleration

| Hardware Platform | Audio Length | Alignment Time | Real-time Factor | Cost |
| :--- | :---: | :---: | :---: | :---: |
| **Apple M5 / M4 Max** | 1 Hour Audio | **~1.5 min** | **~40x Speed** | **$0.00 (Offline)** |
| **Apple M3 / M2 Pro** | 1 Hour Audio | **~3.5 min** | **~17x Speed** | **$0.00 (Offline)** |
| **Apple M1 / M2 Air** | 1 Hour Audio | **~4.8 min** | **~12x Speed** | **$0.00 (Offline)** |
| Cloud GPU Services | 1 Hour Audio | ~8 min + network | ~7x Speed | $0.50–$1.50 / book |

---

## Release Verification & Quality Gates

Before any book is released, it must pass deterministic physical gates:
- **Acoustic Void Detection**: Rejects builds with unhandled >4.0s leading gaps or >6.0s inter-sentence voids;
- **Cryptographic ReleaseToken**: Issued only with ≥ 95% acoustic coverage and zero empty translations;
- **Automated Regression Suite**: Over 106+ automated test assertions:

```bash
python3 -m unittest test_release_gate.py test_html_builder.py test_design_tokens.py test_shift_left_sentence_gate.py test_leading_acoustic_gap_gate.py test_library_acoustic_continuity.py
```

---

## Live Showcase

Explore the production deployment directly in desktop or mobile browsers:
👉 **[audiblelibrary.online](https://audiblelibrary.online/)**
- *The Psychology of Money*: Full bilingual interactive reading and shadow typing
- Daily study streaks, active listening telemetry, and global scholar leaderboard
- Collector's Ex Libris cards with adaptive responsive typography

---

## License

This project is open-source under the [MIT License](LICENSE).
