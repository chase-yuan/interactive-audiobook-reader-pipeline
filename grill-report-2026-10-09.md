---
plugin: grill
version: 1.0.0
target: /Users/lindy/Vault/My Python Productivity Script 2/interactive-audiobook-reader-pipeline
branch: feat/zero-audio-synthesizer
style: Hard-Nosed Critique & Backlog
findings_count:
  critical: 2
  high: 3
  medium: 3
  low: 1
  good: 1
---

# Codebase Interrogation Report: Zero-Audiobook Autonomous TTS Pipeline

## Executive Summary
对“无音频书籍（PDF/EPUB）一键直出有声书”的架构演进进行冷酷的红队盘问，发现新架构在**打破 Whisper 惯性思维**后，迎来了计算复杂度的断崖式简化，但在**流水线既有门禁合约**与**音频物理底层**上潜伏着 5 个致命暗礁。最核心的系统性缺陷在于：现有 `validate_outputs.py` 的质量门禁是一套严格绑定 Whisper 产物的闭环契约（强制校验 `word_spans` 与 `acoustic_coverage`），如果直接使用自生成音频注入，现有门禁系统将直接判定为“非法发布”并拒绝签发 `ReleaseToken`。此外，音频拼接中的 MP3 编码帧延迟累积、24kHz 重采样断层以及 PDF 复杂版面断句，必须建立严密的物理不变量约束，否则将生产出时间轴线性漂移或发音爆音的缺陷残品。

---

## Findings by Lane

### Lane 1: Architecture & Topology

- **File**: `validate_outputs.py:383-385`
- **Observation**: 现有质量门禁在 `COMPLETE` 模式下硬编码断言每个非标题句子必须具有 `word_spans`，否则直接视为严重对齐缺失并阻断发布。纯 TTS 逐句直出默认仅有句子级 `start`/`end`，直接灌入会导致全书所有句子均被判定为质量不达标。
- **Severity**: `[CRITICAL]`
- **Evidence**:
  ```python
  if not is_heading and not non_narrated and not owner_accepted and (not item.get("word_spans") or not item.get("has_audio_match", True)):
      errors.append(f"{label} {item_id}: missing audio word spans")
  ```
- **Proposed change**: 方案二选一（或结合）：
  1. 在 `kokoro_synthesizer.py` 中，根据句子内单词的字符长度权重与音节密度，确定性推导物理连续的 `word_spans`（保证每个词有合理的微秒级时间片）；
  2. 或在 `content_profile.py` 中新增 `SYNTHETIC_SPEECH` 模式，在 `validate_outputs.py` 中放宽声学强制字级匹配，仅严格断言句子级单调性与全覆盖。
- **Tradeoff**: Gain: 顺畅通过 `issue_release_token` 密码学门禁，阅读器继续享有单词高亮；Lose: 单词级高亮依赖字符时长估算而非真实声学对齐（但对于 TTS 而言误差通常 < 80ms，完全可接受）。
- **Effort**: `[< 1 day]`

- **File**: `content_profile.py:11-15`
- **Observation**: 内容模式集合 `VALID_MODES` 仅包含 `{complete, abridged, course, text_only}`，缺乏对“由文字自生成语音（AI Synthesized）”模式的显式类型定义，导致配置必须假冒为 `complete` 从而触发全套不兼容的校验规则。
- **Severity**: `[HIGH]`
- **Evidence**:
  ```python
  COMPLETE = "complete"
  ABRIDGED = "abridged"
  COURSE = "course"
  TEXT_ONLY = "text_only"
  VALID_MODES = {COMPLETE, ABRIDGED, COURSE, TEXT_ONLY}
  ```
- **Proposed change**: 新增 `SYNTHETIC = "synthetic"` 或在 `universal_runner.py` 中规范自生成元数据配置，将合成引擎、音色名及哈希绑定至 `audio_content_profile.json`。
- **Tradeoff**: Gain: 架构语义严格对齐，彻底隔离 Whisper 有声书与 TTS 有声书的质检规则；Lose: 需同步更新 `validate_outputs.py` 的模式分支。
- **Effort**: `[< 1 day]`

---

### Lane 2: Concurrency & Edge Cases

- **File**: `kokoro_synthesizer.py (Proposed Design) & audio_resolver.py:1-40`
- **Observation**: MP3 编码器的开头固定填充延迟（LAME Encoder Delay，约 1105 samples / 25~46ms）。如果逐句生成单句 MP3 文件后再使用 ffmpeg concat 拼接，每句话都会累积 40ms 的无声填充，全书 400 句累积下来，整章结尾会出现 **15~18 秒的致命时间轴线性漂移**！
- **Severity**: `[CRITICAL]`
- **Evidence**:
  在有损压缩格式（MP3）中，连续追加独立的 MP3 块会导致解码端出现音频与采样点脱节。
- **Proposed change**: 确立**物理拼接不变量**：
  1. 必须在**未压缩的 16-bit / 32-bit float PCM 线性波形内存**中进行句子拼接与静音填充；
  2. 按照采样点索引绝对换算 `start` 和 `end`（`sample_idx / sample_rate`）；
  3. 整章内存波形组装完毕后，**一次性调用 ffmpeg 压制为单一 `chapter_XX.mp3`**。
- **Tradeoff**: Gain: 100% 杜绝多段编码延迟累积，时间戳精度保持在 1 个采样点以内（< 0.05ms）；Lose: 每章合成期间需常驻约 50MB~100MB 内存缓存未压缩音频。
- **Effort**: `[< 1 day]`

- **File**: `kokoro_synthesizer.py (Edge-Case Gauntlet)`
- **Observation**: 电子书中频繁出现纯符号、星号、破折号或纯数字段落（如 `* * *`、`1.`、`—`、`...`）。若原样传入 Kokoro G2P（音素转换器），会抛出 `ValueError: empty phonemes` 或生成超长高频杂音，导致整个章节合成进程异常崩溃。
- **Severity**: `[HIGH]`
- **Evidence**:
  书籍中 applications 与分割线含有大量非字母句子。
- **Proposed change**: 引入防御性净化中间件：
  1. 过滤判断 `re.search(r'[a-zA-Z0-9]', text)`；
  2. 若无任何可发音字符，自动静默分配固定静音片段（如 0.4s 纯静音波形），赋予 `[start, end]` 后直接跳过神经合成，绝不允许异常向上穿透。
- **Tradeoff**: Gain: 100% 避免因单一符号崩溃丢弃整章计算进度；Lose: 增加轻量前置正则检查。
- **Effort**: `[< 1 day]`

- **File**: `html_builder.py & player runtime:24kHz to 44.1kHz Resampling`
- **Observation**: Kokoro 原生采样率为 `24,000 Hz`。iOS WebKit（Safari / Apple Books Web 容器）在后台锁屏播放非标准工频（24kHz）音频时，部分机型会触发重采样底噪爆音，且与部分蓝牙耳机的 AAC 解码时钟不同步。
- **Severity**: `[MEDIUM]`
- **Evidence**:
  iOS CoreAudio 默认混音总线为 44.1kHz / 48kHz，24kHz 音频在低功耗锁屏音频会话中偶发卡顿。
- **Proposed change**: 在整章 PCM 输出至 ffmpeg 编码时，统一加上 `-ar 44100` 高质量重采样滤镜，输出行业标称的 44.1kHz 192kbps MP3。
- **Tradeoff**: Gain: 完美兼容 iOS WebKit 锁屏跟读与所有车载/蓝牙设备；Lose: ffmpeg 压制多耗时 0.2 秒。
- **Effort**: `[< 1 day]`

---

### Lane 3: Security & Attack Surface

- **File**: `pdf_intake_normalizer.py (Proposed Input Gate)`
- **Observation**: PDF 解析若遇到恶意的递归书签树（Cyclic PDF Outline）或超大畸形页面，容易造成递归遍历爆栈或内存泄露。
- **Severity**: `[LOW]`
- **Evidence**:
  `pypdf.PdfReader.outline` 支持无限嵌套列表结构。
- **Proposed change**: 书签遍历算法必须加入扁平化深度保护（`max_depth=6`），并校验页面索引必须严格在 `[0, total_pages - 1]` 闭区间内。
- **Tradeoff**: Gain: 杜绝畸形 PDF 拒绝服务风险；Lose: 极罕见的多层目录被截断在第 6 层。
- **Effort**: `[< 1 day]`

---

### Lane 4: Fault Tolerance & Errors

- **File**: `kokoro_synthesizer.py (Checkpointing)`
- **Observation**: 若整本书 21 个章节、8,461 句在单次循环中处理，中途若遭遇系统休眠、终端关闭或单点错误，未保存的状态将导致所有已合成音频全部丢失，必须从头重新跑 1 个多小时。
- **Severity**: `[HIGH]`
- **Evidence**:
  长耗时离线批处理若无章节级断点持久化，容灾能力为零。
- **Proposed change**: 实施**章节级原子化检查点契约**：
  1. 每个章节独立输出 `audio/chapter_XX.mp3` 与 `chapter_XX_aligned_sentences.json`；
  2. 若对应文件已存在且通过 SHA256 完整性检验，重跑时直接秒级跳过；
  3. 支持随时 `Ctrl+C` 中断并在下次执行时无缝接力。
- **Tradeoff**: Gain: 具备生产级断点续跑能力，不怕断电或意外退出；Lose: 增加轻量前置存在性探测逻辑。
- **Effort**: `[< 1 day]`

---

### Lane 5: Test Integrity & Gaps

- **File**: `test_universal_runner.py & quality_gate.py:1-120`
- **Observation**: 原有测试集完全没有对“AI 合成有声书”的声学物理闭环校验用例。缺乏自动化手段探测“生成的 MP3 是否其实全是静音”、“时间戳是否和物理音频总时长吻合”。
- **Severity**: `[MEDIUM]`
- **Evidence**:
  现有测试用例仅测试了 Whisper 对齐后的 Coverage 判定。
- **Proposed change**: 在 `quality_gate.py` 新增两项物理断言：
  1. **音频时长闭环断言**：`abs(ffprobe(chapter_XX.mp3).duration - last_sentence.end) < 0.20s`；
  2. **非静音能量断言**：利用 `ffprobe -af silencedetect` 确认全章静音占比低于 25%，防止生成哑巴文件。
- **Tradeoff**: Gain: 0 人工监听即可 100% 确保合成音频是真实清晰的声音；Lose: 增加两道物理探针执行开销（约 0.3s/章）。
- **Effort**: `[< 1 day]`

---

## Prioritized Remediation Backlog

### Phase 1: Critical Fixes & Core Implementation (Immediate)
- [ ] `validate_outputs.py` / `content_profile.py` — 支持自生成时间轴校验与字符级 `word_spans` 合成，防止 ReleaseToken 门禁硬拒（Effort: `< 1 day`）
- [ ] `kokoro_synthesizer.py` — 实现内存 PCM 采样点级无损拼接，杜绝 MP3 帧边界延迟累积漂移（Effort: `< 1 day`）
- [ ] `kokoro_synthesizer.py` — 增加非发音符号/星号的防御性静音垫片中间件（Effort: `< 1 day`）

### Phase 2: Pipeline Hardening & Fault Tolerance (Next)
- [ ] `kokoro_synthesizer.py` — 实现章节级断点续传（Checkpointing），防止意外中断重算（Effort: `< 1 day`）
- [ ] `kokoro_synthesizer.py` — 统一输出 44.1kHz 192kbps 广播级规格，保障 iOS WebKit 锁屏稳定性（Effort: `< 1 day`）
- [ ] `quality_gate.py` — 增加时长一致性与静音率物理探针（Effort: `< 1 day`）

### Phase 3: Upstream Unification & Merge (Post-Verification)
- [ ] `universal_runner.py` — 接入 `--auto-voice <voice>` CLI 统一入口，彻底抹平无音频与有音频边界（Effort: `< 1 day`）
- [ ] `git merge feat/zero-audio-synthesizer` — 在通过全部单测与回归测试后安全合并回 `main`（Effort: `< 1 day`）
