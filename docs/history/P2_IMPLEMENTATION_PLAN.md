# P2 阶段：工业级智能摄入与全自动发布体系实现规范 (P2 Implementation Plan)

> **当前分支**: `experiment/p0-industrial-hardening`
> **代码库**: `interactive-audiobook-reader-pipeline/`
> **关联发布库**: `Audible/` (GitHub Pages: `https://zack1997999.github.io/Audible/`)

---

## 一、 项目背景与前置状态 (Context)

本项目是一个高性能、毫米级原声卡拉OK点读与语言学习交互有声书引擎：
1. **P0 阶段已完成**：长章节 50 句微批次分块（Chunking）、英文缩写（`grandfather J.`）防误断句、插图图说（`<figcaption>`）噪音过滤、GPU 声学字典热恢复、LocalStorage 命名空间隔离。
2. **P1 阶段已完成**：在 96 章节、超 20 小时原声的巨著《Elon Musk》（11,708 句）上实战跑通了多 Agent 并发语义分析与 LIS 动态声学对齐，全书已上线交付。
3. **P2 阶段核心使命**：从“单书深度定制与手写补丁”升级为 **“可证明的内容映射契约 + 可恢复发布协议”**，实现**零配置/低摩擦摄入、前置防烧钱门禁、高性能阅读器内核与一键全渠道发布**。

---

## 二、 P2 四大核心开发任务与设计规格

### 任务 1: P2.0 契约闭合与技术债清理 (Cleanup & Contract Closure)
1. **废除临时补丁脚本**：
   - 彻底删除 `generate_audible_reader.py`、`compile_live_reader.py` 等硬编码脚本。
   - 所有构建逻辑统一收敛到核心模块 [`html_builder.py`](html_builder.py) 中。
2. **消除 Manifest 双重数据源**：
   - 在 `Audible/index.html` 中彻底消除静态 `INLINE_MANIFEST`，统一由根目录的 `manifest.json` 单一数据源驱动。

---

### 任务 2: P2.1 智能摄入协调器 (`intake_reconciler.py`)
1. **EPUB 结构解析**：
   - 解析 `content.opf` 和 `toc.ncx` / `nav.xhtml`，提取有序的章节标题、正文文本与高清封面图片，剔除纯图片/空白占位页面。
2. **多维声学协调匹配（避免只靠前20秒盲猜）**：
   - 结合 **MP3 音频时长分布**、**章节首尾文本声学锚点（Head/Tail Anchors）** 与 **模糊文本相似度（Fuzzy SequenceMatch）**。
   - 自动识别并跳过片头广告（Audible Jingle / Disclaimers）与片尾致谢。
   - 自动检测并处理 $M:1$（多章合一）与 $1:N$（单章拆分）。
3. **哈希强绑定计划 (`intake_plan.json`)**：
   - 自动输出结构化的摄入计划，并在终端打印 10 秒人类核对表格。
   - 计划中包含输入文件的 SHA-256 哈希签名。
4. **前置防烧钱门禁 (Pre-LLM Quality Gate)**：
   - 只有在 `intake_plan.json` 被核准且声学初筛匹配度 $\ge 90\%$ 时，才允许拉起大模型 Worker，从物理上杜绝因错位而浪费 LLM Token。

---

### 任务 3: P2.2 高性能学习级阅读器内核 2.0 (`html_builder.py`)
1. **二分查找时间区间索引 (Binary Search Sync)**：
   - 针对《马斯克》等 20MB / 1.2 万句的大型单体页面，将当前章节句子的 `[start, end]` 预排为时间有序索引。
   - `requestAnimationFrame` 逐帧高亮同步从 $O(N)$ 遍历优化为 $O(\log N)$ 二分查找，音频暂停或后台切页时自动休眠，彻底解决 iOS Safari 内存与耗电隐患。
2. **原生变调补偿无级变速 (Speed & Pitch Control)**：
   - 原生调用 `audio.playbackRate = rate; audio.preservesPitch = true;` 支持 `0.75x`、`1.0x`、`1.25x`、`1.5x`、`1.75x`、`2.0x` 变速不变调（轻量、零 CORS 风险）。
3. **单句 A/B Shadowing 跟读状态机**：
   - 实现包含 `idle -> playing -> pause_buffer -> replaying` 的跟读状态机。
   - 支持快捷键 `R` 自动单句循环 $N$ 次并带有微小停顿缓冲。
4. **Anki 句卡标准导出**：
   - 导出符合 UTF-8 标准的 TSV 格式。
   - 字段格式严密对齐用户的 `audioanki` 规范：`[背景]。你说：“[台词]”` + 语境翻译 + C1/C2 重点词汇。

---

### 任务 4: P2.3 可恢复幂等全渠道发布器 (`publisher.py`)
1. **Journal 状态机与断点续传**：
   - 整个发布流程通过 `publisher_journal.json` 记录步骤状态（`preflight -> archive -> r2_upload -> remote_verify -> git_stage -> git_push -> smoke_test`），任意步骤中断重跑零重复劳动。
2. **基于 SHA-256 的 R2 差量秒传**：
   - 读取目标文件实际 SHA-256，与 R2 元数据比对，已存在的对象直接跳过。
   - 上传设置正确的 `Content-Type: audio/mpeg` 与 `Cache-Control`。
3. **严格的 HTTP 206 范围请求探测 (Range Prober)**：
   - 发布前对 R2 上的音频发起 `Range: bytes=0-15`（开头）、中间片段和末尾片段探测，必须严格返回 `206 Partial Content` 且带有合法 `Content-Range` 头，确保进度条拖动与快进绝对可用。
4. **原子化 Git 发布与书架注册**：
   - 自动提取并裁剪书籍封面至 `Audible/assets/covers/<slug>.jpg`。
   - 计算全书总时长与章节数，原子更新 `Audible/manifest.json`。
   - 仅暂存（stage）明确的白名单文件，执行 `git commit` 并 `git push origin main`。
   - 线上发布完成后，自动调用 HTTP 请求进行部署后冒烟验收，输出最终体验直达链接。

---

## 三、 验收标准 (Acceptance Criteria)

1. **测试驱动 (TDD)**：所有新功能在 `tests/` 下必须拥有对应的单元测试和模拟测试（Mock R2, Mock Git, Mock EPUB）。
2. **幂等性验证**：同一本书重复执行发布命令，结果应为：0 次重复上传、0 次无意义 Git 提交。
3. **错误注入与回滚验证**：在发布步骤的人工断网或异常退出下，原有的线上书架与旧版本不可被破坏。
