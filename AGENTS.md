# Interactive Audiobook Reader Pipeline — AI Agent Architecture Guide

> [!IMPORTANT]
> **Canonical Universal Entrypoints (唯一通用入口)**:
> 1. `universal_runner.py`: The universal tri-mode runner for EPUB / audiobooks to interactive readers (text-only / studio audio / autonomous Kokoro TTS).
> 2. `pipeline.py`: The universal industrial pipeline runner for Obsidian / audiobook directories to chunked Audible publishing.
> 
> **Zero Repository Pollution Rule (零污染铁律)**:
> - **NEVER** create book-specific runners (e.g. `<book_name>_runner.py`) in the repository root directory!
> - The repository root is strictly reserved for universal, reusable pipeline core modules.
> - One-off experiment scripts belong inside the target book directory under `~/Vault/audiobook/<BookName>/`, never in this open-source repository.
>
> **Industrial End-to-End Delivery Invariant (端到端完整交付铁律)**:
> - 当用户要求“跑这本书”、“制作这本书”或运行有声书流水线时，任务的**唯一合格终点是全自动上线至在线书架（Audible Library）并输出激活卡密**。
> - 本地生成 HTML 阅读器并通过质检门禁仅为**阶段性检查点（Checkpoint）**，绝不是最终交付！
> - 流水线必须一站式自动执行生产发布：音频同步 R2 CDN ➔ 章节切片 ➔ 黄金母本密封 ➔ 双源目录同步 ➔ Git 推送生产环境 ➔ 边缘节点校验 ➔ 输出卡密。
> - 严禁在本地 HTML 编译通过后停步等待用户二次提醒上架！

---

## 1. Quick Reference for AI Agents

| Task | Canonical Command |
| :--- | :--- |
| **New EPUB -> Text Reader** | `python3 universal_runner.py /path/to/book.epub --text-only --concurrency 8` |
| **New EPUB -> Autonomous TTS Audiobook** | `python3 universal_runner.py /path/to/book.epub --book-dir /path/to/book_dir` |
| **New EPUB + Audio -> Audiobook** | `python3 universal_runner.py /path/to/book.epub --audio-dir /path/to/audio --concurrency 8` |
| **Directory -> Full Chunked Release** | `python3 pipeline.py --book-dir /path/to/book_dir --publish` |
| **Run Pipeline Test Suite** | `python3 -m unittest test_release_gate.py test_html_builder.py test_design_tokens.py test_shift_left_sentence_gate.py` |

---

## 2. Core Architecture

- `html_builder.py`: Compiles Apple Books-grade bilingual readers (HTML + CSS + JS).
- `dynamic_aligner.py`: MLX Whisper forced alignment engine.
- `intake_reconciler.py`: EPUB chapter parser and metadata extractor.
- `quality_gate.py`: Quality validation, acoustic coverage thresholds, and release report verification.
- `publisher.py` / `local_publisher.py`: Chunked deployer, R2 uploader, and release sealer.

