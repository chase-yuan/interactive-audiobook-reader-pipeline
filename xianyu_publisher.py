#!/usr/bin/env python3
"""
Xianyu Book Publisher · Refactored Cloud-Native Edition
Automated Marketing Kit Generator for Interactive Audiobook Readers.

Generates:
1. 1:1 Apple-Design Square Cover Card (cover_promo.png) emphasizing pure Web interactive reading (Zero Baidu Netdisk / Zero MP3 files download).
2. High-conversion Xianyu marketing copy (Marketing_Copy.md) aligned with the project's learning science philosophy.
3. Automatically copies marketing copy to macOS clipboard via pbcopy.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Canonical Paths
REPO_ROOT = Path(__file__).resolve().parent
AUDIBLE_ROOT = Path("/Users/lindy/Vault/Audible")
OUTPUT_BASE_DEFAULT = Path("/Users/lindy/Vault/Xianyu_Book_Releases")
TOOLS_DIR = REPO_ROOT / "tools"
BIN_DIR = REPO_ROOT / "bin"
SWIFT_RENDERER_SOURCE = TOOLS_DIR / "render_poster_wk.swift"
RENDERER_BIN = BIN_DIR / "render_poster_wk"

# Well-known Chinese book titles dictionary for Audible library catalog
CANONICAL_CHINESE_TITLES: Dict[str, str] = {
    "beyond-feelings": "超越感觉",
    "48-laws": "权力的48条法则",
    "elon-musk": "埃隆·马斯克传",
    "range": "胜者思维：通才的崛起",
    "the-housemaid": "女佣的秘密",
    "confidence-game": "信任博弈：骗局的艺术",
    "influence": "影响力",
    "story": "故事：剧作原理与结构",
    "denationalisation-of-money": "货币非国家化",
    "competing-against-luck": "克服运气的竞争",
    "deng-xiaoping": "邓小平时代",
    "the-psychology-of-money": "金钱心理学",
    "build": "创造：做有价值的事",
    "fourth-wing": "第四翼",
    "protocols": "高绩效协议",
    "bitcoin-standard": "比特币标准",
    "the-most-important-thing": "投资最重要的事",
    "the-little-book-that-builds-wealth": "巴菲特的护城河",
    "financial-intelligence": "财务智慧",
    "the-outsiders": "商界局外人",
    "the-21-success-secrets-of-self-made-millionaires": "白手起家的21个成功秘诀",
}

# Well-known Chinese subtitles / category hooks
CANONICAL_CHINESE_SUBTITLES: Dict[str, str] = {
    "beyond-feelings": "批判性思考指南",
    "48-laws": "现实权谋与人性法则",
    "elon-musk": "硅谷钢铁侠的硬核传奇",
    "range": "为什么通才能战胜专才",
    "the-housemaid": "反转不断的高分悬疑小说",
    "confidence-game": "骗局背后的心理操纵术",
    "influence": "人人必读的说服心理学",
    "story": "好莱坞故事教父编剧圣经",
    "denationalisation-of-money": "哈耶克货币终极思考",
    "competing-against-luck": "创新与商业成功密码",
    "deng-xiaoping": "当代中国转型的历史密码",
    "the-psychology-of-money": "关于财富、贪婪与幸福的智慧",
    "build": "iPod之父非传统做物指南",
    "the-21-success-secrets-of-self-made-millionaires": "白手起家百万富翁思维习惯",
}

# Thematic hooks tailored to learning science
THEMATIC_HOOKS: Dict[str, str] = {
    "beyond-feelings": "走出感觉与主观偏见，建立真正严密、独立的批判性思考逻辑框架。",
    "the-psychology-of-money": "看透金钱诱惑与人性弱点，用时间复利与长期主义重塑财富常识。",
    "48-laws": "洞悉千年权力运行暗流，在复杂现实博弈中掌握主动权的自卫手册。",
    "elon-musk": "从第一性原理出发，横跨商业、工程与火星梦想的硬核野心全记录。",
    "story": "好莱坞故事教父编剧圣经，穿透虚饰、直抵人心的叙事结构与认知密码。",
    "competing-against-luck": "克里斯坦森终极商业思想：聚焦用户待办任务（Jobs to Be Done）。",
    "deng-xiaoping": "全面剖析当代中国转型的历史十字路口与政治智慧大作。",
    "denationalisation-of-money": "哈耶克石破天惊之作：重构货币认知与自由竞争秩序。",
}

HTML_POSTER_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    width: 1024px;
    height: 1024px;
    background-color: #f7f4ee;
    background-image: 
      radial-gradient(circle at 12% 12%, rgba(255, 255, 255, 0.98) 0%, transparent 45%),
      radial-gradient(circle at 88% 88%, rgba(232, 220, 204, 0.70) 0%, transparent 55%);
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Helvetica Neue", sans-serif;
    color: #2b1d14;
    overflow: hidden;
    position: relative;
  }

  .container {
    width: 1024px;
    height: 1024px;
    padding: 44px 48px 36px 48px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  /* Top Header */
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 2px solid rgba(190, 168, 146, 0.35);
    padding-bottom: 16px;
  }

  .header-left {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .brand-badge {
    display: inline-flex;
    align-items: center;
    background: #2b1d14;
    color: #fcf9f5;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 2px;
    padding: 5px 14px;
    border-radius: 6px;
    width: fit-content;
    text-transform: uppercase;
  }

  .title-group {
    display: flex;
    align-items: baseline;
    gap: 12px;
    margin-top: 2px;
    flex-wrap: nowrap;
  }

  .title-cn {
    font-size: 38px;
    font-weight: 900;
    color: #2b1d14;
    letter-spacing: -0.5px;
    line-height: 1.1;
    white-space: nowrap;
    flex-shrink: 0;
  }

  .title-en {
    font-size: 26px;
    font-weight: 800;
    color: #8c4e28;
    letter-spacing: 0.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    flex-shrink: 1;
  }

  .subtitle {
    font-size: 15px;
    color: #6e5a4d;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .header-tag {
    background: #fdf5ec;
    border: 1.5px solid #d4a373;
    color: #8c4e28;
    padding: 7px 16px;
    border-radius: 999px;
    font-size: 13.5px;
    font-weight: 800;
    box-shadow: 0 4px 12px rgba(212, 163, 115, 0.15);
    display: flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
    flex-shrink: 0;
    margin-left: 16px;
  }

  /* Main Split Stage */
  .main-stage {
    display: flex;
    align-items: center;
    justify-content: space-between;
    height: 730px;
    margin-top: 10px;
  }

  /* Left: 100% Uncropped 3D Physical Book */
  .book-container {
    width: 450px;
    display: flex;
    justify-content: center;
    align-items: center;
    position: relative;
  }

  .book-card {
    width: 420px;
    position: relative;
    border-radius: 4px 16px 16px 4px;
    background: #2b1d14;
    box-shadow: 
      -12px 14px 28px rgba(43, 29, 20, 0.22),
      22px 32px 55px rgba(43, 29, 20, 0.28),
      0 0 1px rgba(0, 0, 0, 0.4);
    border-left: 8px solid #ded5c8;
    overflow: hidden;
    line-height: 0;
  }

  .book-cover {
    width: 100%;
    height: auto;
    display: block;
    border-radius: 2px 14px 14px 2px;
  }

  /* Right: Core Features Showcase (Learning Science & Interactive Audio) */
  .feature-container {
    width: 450px;
    height: 680px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .station-header {
    display: flex;
    flex-direction: column;
    gap: 6px;
    border-bottom: 1.5px solid rgba(190, 168, 146, 0.3);
    padding-bottom: 14px;
  }

  .station-eyebrow {
    font-size: 13px;
    font-weight: 800;
    letter-spacing: 2px;
    color: #8c4e28;
    text-transform: uppercase;
  }

  .station-claim {
    font-size: 27px;
    font-weight: 900;
    color: #1e1b18;
    letter-spacing: -0.4px;
  }

  /* 4 Crisp Feature Pillars */
  .feature-list {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }

  .feature-card {
    background: #ffffff;
    border: 1px solid rgba(215, 195, 175, 0.6);
    border-radius: 14px;
    padding: 16px 20px;
    box-shadow: 0 4px 14px rgba(30, 27, 24, 0.04);
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .feature-num {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    background: #fdf5ec;
    border: 1px solid #ebd3bf;
    color: #8c4e28;
    font-size: 18px;
    font-weight: 900;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }

  .feature-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .feature-headline {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .feature-title {
    font-size: 21px;
    font-weight: 900;
    color: #1e1b18;
    letter-spacing: -0.2px;
  }

  .feature-badge {
    font-size: 11.5px;
    font-weight: 700;
    color: #8c4e28;
    background: #fdf5ec;
    border: 1px solid #ecd5c2;
    padding: 2px 7px;
    border-radius: 4px;
  }

  .feature-caption {
    font-size: 14px;
    color: #6e5a4d;
    line-height: 1.35;
    font-weight: 500;
  }

  .station-meta-pill {
    background: #f6efe4;
    border: 1px solid #dccbb8;
    border-radius: 10px;
    padding: 12px 18px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    font-size: 13.5px;
    font-weight: 700;
    color: #4a372c;
  }

  .station-meta-pill .dot {
    color: #d4a373;
    font-weight: 900;
  }

  /* Bottom Ribbon */
  .bottom-ribbon {
    background: #1e1b18;
    color: #fcf9f5;
    border-radius: 10px;
    padding: 14px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 8px 20px rgba(30, 27, 24, 0.2);
  }

  .ribbon-item {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14.5px;
    font-weight: 700;
    letter-spacing: 0.3px;
  }

  .ribbon-check {
    color: #d4a373;
    font-weight: 900;
  }
</style>
</head>
<body>
  <div class="container">
    
    <!-- Top Header -->
    <div class="header">
      <div class="header-left">
        <div class="brand-badge">AUDIBLELIBRARY · 原生视听双轨点读精读站</div>
        <div class="title-group">
          <div class="title-cn">《__TITLE_CN__》</div>
          <div class="title-en">__TITLE_EN__</div>
        </div>
        <div class="subtitle">__SUBTITLE__ ｜ 录音室原声 · 毫秒级字音同步</div>
      </div>
      <div class="header-tag">专属激活码 · 网页即开即读</div>
    </div>

    <!-- Main Stage: 50/50 Split -->
    <div class="main-stage">
      
      <!-- Left: 100% Complete Uncropped 3D Book -->
      <div class="book-container">
        <div class="book-card">
          <img src="__COVER_SRC__" class="book-cover" alt="__TITLE_EN__ Cover">
        </div>
      </div>

      <!-- Right: Core Features -->
      <div class="feature-container">
        
        <div class="station-header">
          <div class="station-eyebrow">INTERACTIVE READER · 原版有声点读站</div>
          <div class="station-claim">沉浸点读 · 视听双轨同频</div>
        </div>

        <div class="feature-list">
          
          <div class="feature-card">
            <div class="feature-num">01</div>
            <div class="feature-info">
              <div class="feature-headline">
                <span class="feature-title">视听双轨伴读</span>
                <span class="feature-badge">告别走神</span>
              </div>
              <div class="feature-caption">边看文本边听真人原声伴读，眼睛耳朵双输入，告别走神</div>
            </div>
          </div>

          <div class="feature-card">
            <div class="feature-num">02</div>
            <div class="feature-info">
              <div class="feature-headline">
                <span class="feature-title">字音同频跳动</span>
                <span class="feature-badge">绝不脱节</span>
              </div>
              <div class="feature-caption">声音读到哪、单词实时高亮，视线紧扣音频，彻底告别滑水</div>
            </div>
          </div>

          <div class="feature-card">
            <div class="feature-num">03</div>
            <div class="feature-info">
              <div class="feature-headline">
                <span class="feature-title">纯英双语秒切</span>
                <span class="feature-badge">随时减负</span>
              </div>
              <div class="feature-caption">想练语感看纯英，遇到晦涩长难句一键展开双语对照</div>
            </div>
          </div>

          <div class="feature-card">
            <div class="feature-num">04</div>
            <div class="feature-info">
              <div class="feature-headline">
                <span class="feature-title">难词音标全内置</span>
                <span class="feature-badge">即点即查</span>
              </div>
              <div class="feature-caption">轻点句子直接看地道精翻与核心词音标，无需跳出查词</div>
            </div>
          </div>

        </div>

        <div class="station-meta-pill">
          <span>⚡️ 双击单句循环复读 · 随时随地跟读磨耳朵</span>
          <span class="dot">·</span>
          <span>全端自适应</span>
        </div>

      </div>

    </div>

    <!-- Bottom Ribbon -->
    <div class="bottom-ribbon">
      <div class="ribbon-item">
        <span class="ribbon-check">✓</span>
        <span>手机 / iPad / 电脑全端秒开</span>
      </div>
      <div class="ribbon-item">
        <span class="ribbon-check">✓</span>
        <span>免装任何软件 · 浏览器打开即读</span>
      </div>
      <div class="ribbon-item">
        <span class="ribbon-check">✓</span>
        <span>拍下秒发专属网址 + 激活码</span>
      </div>
    </div>

  </div>
</body>
</html>
"""


def _ensure_swift_renderer() -> Path:
    """Ensure the native Swift WebKit renderer binary is compiled and available."""
    if RENDERER_BIN.is_file() and os.access(RENDERER_BIN, os.X_OK):
        return RENDERER_BIN

    # Check fallback in skill path
    fallback_bin = Path("/Users/lindy/.gemini/config/skills/xianyu-book-publisher/scripts/render_poster_wk")
    if fallback_bin.is_file() and os.access(fallback_bin, os.X_OK):
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fallback_bin, RENDERER_BIN)
        RENDERER_BIN.chmod(0o755)
        return RENDERER_BIN

    # Compile via swiftc if source exists
    if SWIFT_RENDERER_SOURCE.is_file():
        BIN_DIR.mkdir(parents=True, exist_ok=True)
        cmd = ["swiftc", str(SWIFT_RENDERER_SOURCE), "-o", str(RENDERER_BIN)]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            RENDERER_BIN.chmod(0o755)
            return RENDERER_BIN

    raise RuntimeError("Failed to locate or compile native Swift WebKit renderer 'render_poster_wk'.")


def _image_to_base64(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Cover image not found: {path}")
    ext = path.suffix.lower().replace(".", "")
    if ext == "jpg":
        ext = "jpeg"
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/{ext};base64,{b64}"


def resolve_book_metadata(
    book_id_or_dir: str,
    manifest_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Auto-discover complete book metadata from Audible manifest and local directory."""
    manifest_file = manifest_path or (AUDIBLE_ROOT / "manifest.json")
    catalog_books = []
    if manifest_file.is_file():
        try:
            catalog_books = json.loads(manifest_file.read_text(encoding="utf-8")).get("books", [])
        except Exception:
            pass

    # Normalize input
    raw_str = book_id_or_dir.strip()
    book_id = ""
    local_dir: Optional[Path] = None

    if Path(raw_str).is_dir():
        local_dir = Path(raw_str).resolve()
        # Derive book_id from directory name or inventory
        book_id = local_dir.name.lower().replace(" ", "-").replace(":", "").replace("_", "-")
    else:
        book_id = raw_str.lower().replace(" ", "-")

    # Match in manifest.json
    matched_entry = None
    for b in catalog_books:
        if b.get("id") == book_id or b.get("id", "").replace("-", "") == book_id.replace("-", ""):
            matched_entry = b
            book_id = b.get("id")
            break

    # If not matched directly, check if directory points to Beyond Feelings etc.
    if not matched_entry and local_dir:
        for b in catalog_books:
            if b.get("title", "").lower() in local_dir.name.lower() or b.get("id") in local_dir.name.lower():
                matched_entry = b
                book_id = b.get("id")
                break

    # Fallback default values
    raw_title = (matched_entry or {}).get("title") or (local_dir.name if local_dir else book_id.replace("-", " ").title())
    if ":" in raw_title:
        title_en, auto_sub = [p.strip() for p in raw_title.split(":", 1)]
    elif " - " in raw_title:
        title_en, auto_sub = [p.strip() for p in raw_title.split(" - ", 1)]
    else:
        title_en = raw_title
        auto_sub = ""

    subtitle = CANONICAL_CHINESE_SUBTITLES.get(book_id) or (matched_entry or {}).get("subtitle") or auto_sub or "原版有声交互点读精读工作站"
    subtitle = re.sub(r",?\s*(?:Ninth|9th|Eighth|8th|Tenth|10th)\s+Edition", "", subtitle, flags=re.I).strip()
    if not subtitle:
        subtitle = "原版有声交互点读精读工作站"

    author = (matched_entry or {}).get("author") or "经典原著"
    total_duration = (matched_entry or {}).get("totalDuration") or "完整章节"
    chapters_count = (matched_entry or {}).get("chaptersCount") or 21
    title_cn = CANONICAL_CHINESE_TITLES.get(book_id) or title_en

    # Cover path discovery
    cover_path: Optional[Path] = None
    if matched_entry and matched_entry.get("cover"):
        cand = AUDIBLE_ROOT / matched_entry["cover"].split("?")[0]
        if cand.is_file():
            cover_path = cand

    if not cover_path and local_dir:
        for cand_name in ("cover.jpg", "cover.png", "cover.jpeg"):
            if (local_dir / cand_name).is_file():
                cover_path = local_dir / cand_name
                break

    if not cover_path:
        cand_audible = AUDIBLE_ROOT / "assets" / "covers" / f"{book_id}.jpg"
        if cand_audible.is_file():
            cover_path = cand_audible

    if not cover_path:
        # Check audiobook library
        vault_audiobook = Path(f"/Users/lindy/Vault/audiobook/{local_dir.name if local_dir else ''}")
        if (vault_audiobook / "cover.jpg").is_file():
            cover_path = vault_audiobook / "cover.jpg"

    if not cover_path or not cover_path.is_file():
        raise FileNotFoundError(f"Could not automatically locate cover image for book '{book_id}'.")

    hook = THEMATIC_HOOKS.get(book_id) or (matched_entry or {}).get("description") or f"现代英语原版最硬核的认知与语言力量。"

    return {
        "id": book_id,
        "title_cn": title_cn,
        "title_en": title_en,
        "subtitle": subtitle,
        "author": author,
        "total_duration": total_duration,
        "chapters_count": chapters_count,
        "cover_path": cover_path,
        "hook": hook,
        "url": f"https://audiblelibrary.online/books/{book_id}/",
    }


def render_poster(
    meta: Dict[str, Any],
    out_png: Path,
) -> None:
    """Render 1:1 Apple-Design square cover card using native WebKit renderer."""
    renderer = _ensure_swift_renderer()
    cover_b64 = _image_to_base64(meta["cover_path"])

    html_content = (
        HTML_POSTER_TEMPLATE
        .replace("__BOOK_ID__", meta["id"])
        .replace("__TITLE_EN__", meta["title_en"])
        .replace("__TITLE_CN__", meta["title_cn"])
        .replace("__SUBTITLE__", meta["subtitle"])
        .replace("__COVER_SRC__", cover_b64)
    )

    tmp_html = Path(f"/tmp/poster_render_{os.getpid()}.html")
    tmp_html.write_text(html_content, encoding="utf-8")

    out_png.parent.mkdir(parents=True, exist_ok=True)
    try:
        cmd = [str(renderer), str(tmp_html), str(out_png)]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        if not out_png.is_file() or out_png.stat().st_size == 0:
            raise RuntimeError(f"Poster rendering failed; empty output file: {res.stdout} {res.stderr}")
    finally:
        if tmp_html.is_file():
            tmp_html.unlink(missing_ok=True)


def generate_marketing_copy(
    meta: Dict[str, Any],
    out_dir: Path,
) -> str:
    """Generate high-conversion, cloud-native Xianyu marketing copy (Zero Netdisk / Zero MP3 files)."""
    book_id = meta["id"]
    title_cn = meta["title_cn"]
    title_en = meta["title_en"]
    hook = meta["hook"]
    url = meta["url"]
    clean_en_compact = re.sub(r"[^\w]", "", title_en)
    keywords = f"{title_cn} {clean_en_compact} 英文原版 英语精读 有声书 影子跟读 纯英双语切换 考研英语 托福雅思 听力口语磨耳朵 沉浸式阅读"

    # Detail description tailored strictly to pain points & instant web passkey delivery
    detail_text = f"""《{title_cn}》（{title_en}）原版有声交互点读精读站：
{hook}

你是不是也这样：
自己硬啃原版书，满页生词，查两次词典就走神读不下去？
听原版有声书，听着听着就成了白噪音，完全不知道读到了哪？

这个网页版交互点读精读站，就是专门解决这些痛点的：

【四大核心特色】
1. 【点哪读哪 · 字音同步】：录音室真人原声伴读，读到哪、单词高亮到哪，眼睛耳朵双输入，告别走神滑水。
2. 【难词音标全内置】：轻点句子直接展开地道精翻与核心高阶词汇音标，告别反复切屏查词典。
3. 【纯英双语秒切】：想练语感看纯英文，遇到难句一键切双语对照，阅读节奏自己掌控。
4. 【双击单句循环跟读】：双击任意句子瞬间循环复读磨耳朵，口语跟读与听力精听利器。

【极简交付 · 开箱即用】
拍下自动秒发：专属在线阅读网址 + 专属激活码。
手机 / iPad / 电脑浏览器打开即读，免装任何软件，永久有效。

关键词：{keywords}"""

    # 3 High-converting SEO titles strictly obeying Xianyu 30-character limit
    opt1 = f"《{title_cn}》英文原版有声点读精读站 纯英双语秒切 影子跟读"
    if len(opt1) > 30:
        opt1 = f"《{title_cn}》原版有声点读精读站 纯英双语秒切 影子跟读"
    
    opt2 = f"《{title_cn}》英文原版有声交互点读站 视听双轨 难词全内置"
    if len(opt2) > 30:
        opt2 = f"《{title_cn}》原版有声点读精读站 视听双轨 难词全内置"
        
    opt3 = f"《{title_cn}》原声点读精读站 手机平板电脑免装软件即读"
    if len(opt3) > 30:
        opt3 = f"《{title_cn}》原声点读精读工作站 随时随地想读就读"

    title_options = f"""1. {opt1}
2. {opt2}
3. {opt3}"""

    md_content = f"""# 闲鱼商品发布文案 · 《{title_cn}》

---

## 闲鱼发布标题（精选 3 组推荐，字符严格适配闲鱼 30 字规范）

```text
{title_options}
```

---

## 宝贝详情描述（已自动注入剪贴板，可直接粘贴到闲鱼详情）

```text
{detail_text}
```

---

## 配套交付物资检查清单

- [x] 主图海报：`cover_promo.png`（1:1 纯净正方形、原书封面 100% 完整无遮挡、零牛皮癣）
- [x] 在线阅读地址：`{url}`
- [x] 密钥生成工具：`keygen.py`（单本密钥格式：`KEY-...`）
- [x] 交付模式：纯网页 + 专属激活码即开即读（免装软件、零等待）
"""

    out_dir.mkdir(parents=True, exist_ok=True)
    md_file_path = out_dir / f"{book_id}_Marketing_Copy.md"
    readme_path = out_dir / "README.md"
    md_file_path.write_text(md_content, encoding="utf-8")
    readme_path.write_text(md_content, encoding="utf-8")

    # Sync to macOS clipboard via pbcopy
    try:
        subprocess.run(["pbcopy"], input=detail_text.encode("utf-8"), check=False)
        print("📋 [CLIPBOARD] Successfully piped marketing copy into macOS clipboard via pbcopy.")
    except Exception as exc:
        print(f"⚠️ [CLIPBOARD] pbcopy notice: {exc}")

    return detail_text


def publish_xianyu_kit(
    book_id_or_dir: str,
    out_base: Optional[Path] = None,
    folder_name: Optional[str] = None,
) -> Path:
    """End-to-end Xianyu Release Kit generator."""
    meta = resolve_book_metadata(book_id_or_dir)
    book_id = meta["id"]

    out_base_dir = out_base or OUTPUT_BASE_DEFAULT
    # Determine folder name (e.g., 21_Beyond_Feelings or similar)
    if not folder_name:
        # Check existing directories in output base to find match or generate numbered folder
        folder_name = book_id.replace("-", "_").title()
        if out_base_dir.is_dir():
            for d in out_base_dir.iterdir():
                if d.is_dir() and (book_id in d.name.lower() or book_id.replace("-", "_") in d.name.lower()):
                    folder_name = d.name
                    break

    target_dir = out_base_dir / folder_name
    target_dir.mkdir(parents=True, exist_ok=True)

    out_png = target_dir / "cover_promo.png"
    print(f"🎨 [POSTER] Rendering 1:1 promo poster -> {out_png} ...")
    render_poster(meta, out_png)
    print(f"✅ [POSTER] 1:1 Cover poster successfully generated ({out_png.stat().st_size} bytes).")

    print(f"📝 [COPYWRITING] Emitting cloud-native marketing copy -> {target_dir} ...")
    generate_marketing_copy(meta, target_dir)
    print(f"🎉 [SUCCESS] Xianyu Release Kit is ready at: {target_dir}")
    return target_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Xianyu Book Publisher · Cloud-Native Marketing Kit Generator")
    parser.add_argument("book", help="Book identifier (e.g. beyond-feelings) or audiobook directory path")
    parser.add_argument("--out-base", default=str(OUTPUT_BASE_DEFAULT), help="Base directory for Xianyu releases")
    parser.add_argument("--folder", help="Specific folder name inside out-base")
    args = parser.parse_args()

    publish_xianyu_kit(
        book_id_or_dir=args.book,
        out_base=Path(args.out_base),
        folder_name=args.folder,
    )


if __name__ == "__main__":
    main()
