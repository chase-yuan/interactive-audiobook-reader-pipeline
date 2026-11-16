# Interactive Audiobook Reader Pipeline (双语有声书制作与发布流水线)

<p align="center">
  <b>面向 macOS 与 Apple Silicon 原生打造的工业级双语有声点读书制作、声学对齐与数字化发布流水线。</b><br>
  <i>以 Apple Books 级排版标准，实现 EPUB 句子级纯净拆分、MLX 毫秒级声学强制对齐、全键盘影子跟打、单句专注舱与密码学发布门禁。</i>
</p>

<p align="center">
  <a href="README.md"><b>简体中文</b></a> | <a href="README_EN.md">English</a>
</p>

<p align="center">
  <a href="https://audiblelibrary.online/books/the-psychology-of-money/"><img src="https://img.shields.io/badge/线上示范站-audiblelibrary.online-4338ca?style=flat-square&logo=safari&logoColor=white" alt="Live Demo"></a>
  <a href="https://apple.com"><img src="https://img.shields.io/badge/支持平台-macOS%2013%2B-0f172a?style=flat-square&logo=apple&logoColor=white" alt="Platform"></a>
  <a href="https://apple.com"><img src="https://img.shields.io/badge/硬件架构-Apple%20Silicon%20(M1--M5)-334155?style=flat-square" alt="Hardware"></a>
  <a href="https://github.com/ml-explore/mlx"><img src="https://img.shields.io/badge/声学引擎-Apple%20MLX%20Whisper-0284c7?style=flat-square" alt="Engine"></a>
  <a href="https://github.com/chase-yuan/interactive-audiobook-reader-pipeline"><img src="https://img.shields.io/badge/测试矩阵-245%20项全部通过-10b981?style=flat-square" alt="Tests"></a>
  <a href="https://github.com/chase-yuan/interactive-audiobook-reader-pipeline"><img src="https://img.shields.io/badge/发布门禁-密码学校验放行-475569?style=flat-square" alt="Quality Gate"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/开源协议-MIT-64748b?style=flat-square" alt="License"></a>
</p>

---

## 核心设计理念：为什么做这个工具？

我做这个工具的初衷，源自自己在英文深度精读中对“专注力”与“学习科学”的切实探索：

1. **视听双轨协同，锁定深度专注**：单纯阅读容易走神，单纯听书容易滑水。而在阅读文本的同时聆听专业录音室的原声朗读，双感官通道协同输入，能让大脑迅速进入高度专注的沉浸心流。
2. **动态跳动高亮，视觉流动锚定**：伴随朗读节奏实时跳动的单词高亮，为眼球提供了精准的视觉锚点。它让视觉焦点紧紧咬住听觉流动，彻底杜绝“听着听着不知道读到哪”或“视线溜号走神”的脱节痛点。
3. **纯英阅读模式：引入“必要的难度 (Desirable Difficulty)”**：默认纯英文浸润，不让大脑过早依赖中文译文这一拐杖。通过给大脑施加适度而必要的认知负荷，逼迫大脑在纯英语境中直接建立语义联结与原语语感。
4. **按需双语模式：精准为大脑减负**：学习需要挑战，但也需要保护持续性。系统支持随时一键展开双语对照或逐句点读，在遭遇晦涩长难句或认知过载时即时为大脑减负，让精读兼具挑战与从容。
5. **交互式影子跟打：由“被动输入”跃迁为“具身肌肉记忆”**：听懂不代表掌握。借助键盘打字跟读，将每一句话的拼写、语感与节奏刻入肌肉深层记忆。
6. **语境地道翻译与高阶生词解析**：摒弃生硬呆板的字面机翻，提供高度契合图书叙事语境的地道中文译文；结合词性、国际音标 (IPA) 与 CEFR C1/C2 词汇解析，帮助读者在具体上下文中真正吃透核心短语与生词。

---

## 🚀 核心功能矩阵 (Features)

### 1. ⌨️ 交互式影子跟打系统 (Interactive Shadow Typing)
- **Monkeytype 级机械键轴音效**：内置青轴/茶轴级真实敲击音频反馈，打造极度解压的触觉声学体验；
- **排版零跳动绝对不变量 (Zero-Layout-Shift / CLS = 0)**：严格锁定单词物理盒模型，高亮打字与未敲击状态绝不发生文本推挤抖动；
- **智能标点与空格吸收**：空格键自动吸收句中逗号、句号、连字符等标点，实现行云流水的纯字母敲击体验；
- **Cloze 核心生词挖空模式**：基于 CEFR 难度自动将核心关键词挖空，强化主动提取（Active Recall）记忆效果；
- **实时统计与投射**：实时 WPM、击键准确率、生词敲击量与极细声学发丝进度条。

### 2. 🎯 单句沉浸专注舱 (Single Sentence Focus Mode)
- **视觉噪音归零**：一键将全篇复杂的长篇文本折叠为当前单句的高清卡片；
- **字体多阶无级缩放 (Font Size Stepper)**：按 `+` / `-` 阶梯式平滑调整字体，满足大屏精读与弱视力舒适阅读；
- **快捷键完全操控**：空格暂停/播放、左右方向键快速跳句、回车键一键切换纯英/双语对照。

### 3. 🛡️ 工业级声学连贯性硬门禁 (Acoustic Continuity Gates)
- **告别人肉测试员**：内置独立红队测试工具 `test_library_acoustic_continuity.py`，**1.2 秒内自动穿透全库 34 本书、905 个章节**；
- **前置音频空洞嗅探**：非首章前置未对齐空白严格限制在 `4.0s` 内，自动捕获播音员朗读的卷首导读与章节地图；
- **句间声学空洞拦截**：句间间隙阈值收紧至 `6.0s`，强制拦截被遗漏的图表（Tables）、边栏故事（Sidebars）与作者长注释；
- **全自动化 EPUB 摘要缝合**：自动解析 EPUB Front-matter 卷首语并无缝内联，出厂零断层。

### 4. 🧠 神经语音双引擎架构 (MLX Whisper & Autonomous TTS)
- **Apple Silicon 原生强制对齐**：通过 Apple 官方 `mlx-whisper` 榨干 M 系列统一内存，毫秒级逐词时间戳提取；
- **高清神经语音合成**：内置 Microsoft Edge HD 神经网络语音（默认 `BrianMultilingualNeural`）与 82M 本地 Kokoro 双引擎，支持 10 倍并发流式预加载。

---

## 30 秒极速体验

仓库已内置公版示范用例（《孙子兵法》英译版），纯 Python 标准库即可运行：

```bash
# 1. 克隆流水线仓库
git clone https://github.com/chase-yuan/interactive-audiobook-reader-pipeline.git
cd interactive-audiobook-reader-pipeline

# 2. 构建交互式双语书（纯标准库运行，零外部依赖）
python3 universal_runner.py demo/sample.epub --text-only
```

---

## 生产级三大工作模式

### 模式 1：纯文本双语精读器 (`--text-only`)
适用于尚未配齐音频的电子书。自动完成章节划分、逐句对照、高阶词汇解析与纯键盘导航支持：

```bash
python3 universal_runner.py /path/to/book.epub --text-only --concurrency 8 --book-dir ./my_book
```

### 模式 2：沉浸式原声点读书 (`complete`)
将 EPUB 文本与原声朗读音频（`.mp3` 或 `.m4a`）结合，通过 Apple Silicon MLX 运行单词级对齐：

```bash
# 安装 Apple Silicon 原生 MLX 声学支持
pip install -e '.[acoustic]'

# 构建完整有声点读电子书
python3 universal_runner.py --epub /path/to/book.epub --audio-dir /path/to/mp3s --book-dir ./my_book
```

### 模式 3：自主神经语音合成点读书 (`TTS`)
针对无自带音频的原版书籍，调用高清神经语音合成器生成广播级自然人声旁白与词级对齐：

```bash
python3 universal_runner.py /path/to/book.epub --book-dir ./my_book
```

---

## Apple Silicon 统一内存加速表现

| 硬件平台 | 音频时长 | 本地对齐耗时 | 处理吞吐效率 | 费用 |
| :--- | :---: | :---: | :---: | :---: |
| **Apple M5 / M4 Max** | 1 小时录音 | **~1.5 分钟** | **~40 倍速** | **$0.00 (离线)** |
| **Apple M3 / M2 Pro** | 1 小时录音 | **~3.5 分钟** | **~17 倍速** | **$0.00 (离线)** |
| **Apple M1 / M2 Air** | 1 小时录音 | **~4.8 分钟** | **~12 倍速** | **$0.00 (离线)** |
| 云端 GPU 方案 | 1 小时录音 | ~8 分钟 + 延迟 | ~7 倍速 | $0.50–$1.50 / 本 |

---

## 生产放行门禁与质量保障体系

本工程在合并和发布任何一本书前，必须通过严格的物理门禁：
- **声学真空检测**：禁止未声明的 >4.0s 前置留白与 >6.0s 句间断层；
- **密码学 ReleaseToken**：对齐覆盖率 ≥ 95%、无非单调时间戳、无空翻译时颁发；
- **全量单元测试矩阵**：运行覆盖 106+ 项自动化测试：

```bash
python3 -m unittest test_release_gate.py test_html_builder.py test_design_tokens.py test_shift_left_sentence_gate.py test_leading_acoustic_gap_gate.py test_library_acoustic_continuity.py
```

---

## 线上示范站 (Live Showcase)

可直接在桌面或移动端浏览器访问示范站点：
👉 **[audiblelibrary.online](https://audiblelibrary.online/)**
- 《金钱心理学》完整双语交互点读与键盘跟打体验
- 每日阅读打卡（Daily Streak）、学习时长统计与学者排行榜
- 典藏藏书票与移动端自适应排版

---

## 开源协议

本项目基于 [MIT License](LICENSE) 协议完全开源。
