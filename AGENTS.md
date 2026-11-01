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

---

## 4. Autonomous Supervisor & Anti-Hang Protocol (自主不间断巡检与防死锁规范)

> [!IMPORTANT]
> **拒绝“离席休眠”与被动等待（Zero-Abandonment Invariant）**：
> 流水线在执行长耗时任务（如语言学分析、Whisper 强制对齐、全书构建）时，严禁输出一段“预计 20 分钟后完成”然后主动结束对话 Turn 将控制权交还给用户。这会导致 Agent 彻底进入被动休眠，进程发生网络死锁或挂起时无人看守，迫使用户反复手动催问进度。

### 4.1 Anti-Hang & Watchdog Invariants (防挂起四大铁律)
1. **SP1 (Strict Fast-Fail Timeouts & Circuit Breakers · 短超时快速熔断)**:
   - 严禁对任何单批次网络请求或外部 CLI 子进程设置无限制或超长超时（如禁止 `timeout=3600` 或 `--print-timeout 1h`）。
   - 单批次请求超时阈值严格限定在 **120 秒** 以内。超时必须触发熔断（`TimeoutExpired`），捕获并立即自动切换至备选模型（fallback model）或重试，绝不在卡死套接字上空转。
2. **SP2 (Collision-Proof Checkpoint Caching · 防碰撞内容签名缓存)**:
   - 批次断点缓存必须绑定句子内容的 SHA-256 哈希签名（`cache_{first_id}_{last_id}_{len}_{content_hash}.json`）。
   - 严禁仅使用局部自增 ID（如 `s-0`）作为全书级缓存键，杜绝多章节并发时互相踩踏或脏读缓存。
3. **SP3 (Continuous Supervisor Watchdog · 主动看门狗守护)**:
   - 当任务运行时间超过单个工具同步等待上限（WaitMsBeforeAsync）转为后台任务时，Agent **严禁直接结束 Turn**。
   - Agent 必须使用 `schedule` 注册定时唤醒（如 60~90s 心跳定时器）或通过工具循环主动巡检任务心跳与产物生成。
   - 若发现任务进程 CPU 为 0% 且日志在 2 个巡检周期内无变化，看门狗必须主动 `kill` 僵死子进程并自动重启重试。
4. **SP4 (Single-Runner Orchestration · 单一入口全流程贯通)**:
   - 严禁将处理拆解为“先跑这几个章节的脚本 -> 停下来汇报 -> 等用户命令 -> 再跑对齐 -> 停下来汇报 -> 再上架”。
   - 必须通过统一协调入口（如 `pipeline.py` 或统一编排脚本）全自动连续流转：
     `抽取/对齐 ➔ 语言学解析 ➔ 校验门禁 ➔ 切片构建 ➔ R2同步 ➔ 生产部署 ➔ 边缘验证 ➔ 输出卡密`。



