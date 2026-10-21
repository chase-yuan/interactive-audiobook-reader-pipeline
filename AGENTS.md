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

---

## 3. Aesthetic Principle Zero Protocol (美学第零原则 · 极简设计规范)

> [!IMPORTANT]
> **审美是价值观的物理折现**：好看是在动手编码前就必须确立的第零原则（Principle Zero）。严禁为了图省事向界面注入低质粗糙元素或破坏排版呼吸感。

### 3.1 Hard Invariants (正向设计不变量)
1. **AP0 (Zero Decorative Icon Invariant - 零多余表情符不变量)**:
   - 严禁在任何 UI 组件、按钮、状态指示、沉浸舱、弹窗或提示信息中使用装饰性 Emoji（如 `👁`、`🙈`、`📖`、`💡`、`✨`、`🚀`、`ℹ️`）。
   - 仅允许使用系统无衬线排版、微型胶囊徽章（Pill Badge）或 1.5px 极细规范化 SVG 线条图标传递状态。
2. **AP1 (Boxless Architecture & High Data-to-Ink Ratio - 无框架构与高数据墨水比)**:
   - 杜绝多层嵌套卡片容器、高饱和度边框与僵硬边框线（禁止 `border >= 3px solid`）。
   - 采用开放式无边框微底色（`#f8fafc` / `#0b0f19`），通过负空间（留白）与字体字阶区分层级。
3. **AP2 (100% Tokenized Design System - 绝对令牌化规范)**:
   - 所有组件颜色必须 100% 引用 `var(--token-name)` 设计令牌，严禁在组件样式规则中硬编码 16 进制颜色（`#hex`）或 `rgba(...)`。
   - 所有色彩必须在 `:root` 与 `[data-theme]` 统一定义，严格通过 `test_design_tokens.py` 自动化测试门禁。
4. **AP3 (Label Elimination & Inline Integration - 消除官僚说明标签与繁冗括号)**:
   - 严禁保姆式、打补丁式文字说明（如 `(点此显字)`、`说明：`、`句意：`）。
   - 交互状态必须内嵌为精炼无冗余的语义控件（如 `译文`、`盲听`、`3×`），直接依靠视觉反馈与微动效传达操作结果。
5. **AP4 (Zero-Jitter Typography Invariant - 排版零跳动绝对不变量)**:
   - 单词高亮、音频卡拉 OK 寻迹（Karaoke Word Tracking）以及单句专注舱高亮词（`.active-word`）**严禁动态改变 `padding`、`margin`、`font-size` 或 `letter-spacing`**。
   - 必须维持单词物理盒模型的绝对恒定（CLS = 0），杜绝高亮时单词放大缩小、推挤文本导致的视觉抖动。
6. **AP5 (Instant Ergonomic Flow - 顺滑人体工学交互)**:
   - 杜绝强迫用户长按等待（如长按 1.5s 退出等高阻力交互）。
   - 操作必须符合直觉：单触即退、单击步进（如 `1×` $\rightarrow$ `3×` $\rightarrow$ `5×` 循环切）、记忆偏好（如中英文显隐状态通过 `localStorage` 自动持久化）。


