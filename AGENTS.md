# Interactive Audiobook Reader Pipeline — AI Agent Architecture Guide

> [!IMPORTANT]
> **Canonical Universal Entrypoints (唯一通用入口)**:
> 1. `universal_runner.py`: The universal dual-mode runner for EPUB / audiobooks to interactive readers.
> 2. `pipeline.py`: The universal industrial pipeline runner for Obsidian / audiobook directories to chunked Audible publishing.
> 
> **Zero Repository Pollution Rule (零污染铁律)**:
> - **NEVER** create book-specific runners (e.g. `<book_name>_runner.py`) in the repository root directory!
> - The repository root is strictly reserved for universal, reusable pipeline core modules.
> - One-off experiment scripts belong in `archive/` or inside the target book directory under `/Users/lindy/Vault/audiobook/<BookName>/`.

---

## 1. Quick Reference for AI Agents

| Task | Canonical Command |
| :--- | :--- |
| **New EPUB -> Text Reader** | `python3 universal_runner.py /path/to/book.epub --text-only --concurrency 8` |
| **New EPUB + Audio -> Audiobook** | `python3 universal_runner.py /path/to/book.epub --audio-dir /path/to/audio --concurrency 8` |
| **Directory -> Full Chunked Release** | `python3 pipeline.py --book-dir /path/to/book_dir --publish` |
| **Generate Xianyu Marketing Kit** | `python3 xianyu_publisher.py <book_id>` |
| **Run Pipeline Test Suite** | `python3 -m unittest test_release_gate.py test_html_builder.py test_design_tokens.py test_shift_left_sentence_gate.py test_xianyu_publisher.py` |

---

## 2. Core Architecture

- `html_builder.py`: Compiles Apple Books-grade bilingual readers (HTML + CSS + JS).
- `dynamic_aligner.py`: MLX Whisper forced alignment engine.
- `intake_reconciler.py`: EPUB chapter parser and metadata extractor.
- `quality_gate.py`: Quality validation, acoustic coverage thresholds, and release report verification.
- `publisher.py` / `local_publisher.py`: Chunked deployer, R2 uploader, and release sealer.
- `xianyu_publisher.py`: Cloud-native Xianyu marketing copy and 1:1 Apple-Design WebKit poster generator.
