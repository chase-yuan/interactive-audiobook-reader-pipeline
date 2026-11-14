#!/usr/bin/env python3
"""
EPUB Automated Intake & Preflight Inspection Engine.
Provides instant (< 500ms) diagnostic analysis for any input EPUB:
1. DRM & encryption status check.
2. Reflowable text stream vs. scanned image-only detection.
3. Language identification & neural voice mapping.
4. Recurring exercise/application stop-marker discovery.
5. Zero-configuration recommended execution command synthesis.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


VOICE_MAP = {
    "en": "en-US-GuyNeural",
    "zh": "zh-CN-YunxiNeural",
    "de": "de-DE-ConradNeural",
    "fr": "fr-FR-HenriNeural",
    "ja": "ja-JP-KeitaNeural",
    "es": "es-ES-AlvaroNeural",
}

COMMON_EXERCISE_MARKERS = [
    "applications",
    "exercises",
    "review questions",
    "discussion questions",
    "chapter review",
    "study questions",
    "practice problems",
    "further reading",
    "suggested readings",
]


def inspect_epub(epub_path: str | Path) -> Dict[str, Any]:
    path = Path(epub_path).resolve()
    if not path.is_file():
        return {"error": f"File not found: {path}", "status": "blocked"}

    try:
        zf = zipfile.ZipFile(path, "r")
    except Exception as exc:
        return {"error": f"Invalid zip/EPUB archive: {exc}", "status": "blocked"}

    with zf:
        namelist = set(zf.namelist())

        # 1. DRM & Encryption check
        is_drm_locked = False
        drm_reason = None
        if "META-INF/rights.xml" in namelist:
            is_drm_locked = True
            drm_reason = "Adobe DRM rights.xml detected"
        elif "META-INF/encryption.xml" in namelist:
            try:
                enc_xml = zf.read("META-INF/encryption.xml").decode("utf-8", errors="ignore")
                if "http://www.w3.org/2001/04/xmlenc#" in enc_xml and "Font" not in enc_xml:
                    is_drm_locked = True
                    drm_reason = "Encrypted media/content streams detected"
            except Exception:
                pass

        # 2. Container & OPF resolution
        if "META-INF/container.xml" not in namelist:
            return {"error": "Missing META-INF/container.xml (not a valid EPUB)", "status": "blocked"}

        try:
            container_xml = zf.read("META-INF/container.xml")
            c_root = ET.fromstring(container_xml)
            rootfile_el = c_root.find(".//{*}rootfile")
            if rootfile_el is None or "full-path" not in rootfile_el.attrib:
                return {"error": "Malformed container.xml: missing rootfile", "status": "blocked"}
            opf_path = rootfile_el.attrib["full-path"]
            opf_dir = os.path.dirname(opf_path)
            opf_xml = zf.read(opf_path)
            opf_root = ET.fromstring(opf_xml)
        except Exception as exc:
            return {"error": f"Failed to parse OPF manifest: {exc}", "status": "blocked"}

        # 3. Metadata
        title_el = opf_root.find(".//{*}title")
        title = title_el.text.strip() if title_el is not None and title_el.text else path.stem

        creator_el = opf_root.find(".//{*}creator")
        author = creator_el.text.strip() if creator_el is not None and creator_el.text else "Unknown"

        lang_el = opf_root.find(".//{*}language")
        lang = lang_el.text.strip()[:2].lower() if lang_el is not None and lang_el.text else "en"

        # 4. Spine items
        manifest = {}
        for item in opf_root.findall(".//{*}manifest/{*}item"):
            manifest[item.attrib["id"]] = item.attrib["href"]

        spine_hrefs = []
        for itemref in opf_root.findall(".//{*}spine/{*}itemref"):
            item_id = itemref.attrib.get("idref")
            if item_id in manifest:
                href = manifest[item_id]
                full_href = (Path(opf_dir) / href).as_posix() if opf_dir else href
                spine_hrefs.append(full_href)

        # 5. Content sampling: Prose vs. Image-only & Stop-marker heuristics
        total_p_tags = 0
        total_chars = 0
        total_img_tags = 0
        total_words = 0
        substantive_chapters = 0
        stop_marker_hits: Dict[str, int] = {}

        for href in spine_hrefs:
            if not href.endswith((".html", ".xhtml", ".htm")):
                continue
            try:
                content = zf.read(href).decode("utf-8", errors="ignore")
            except Exception:
                continue

            clean_text = re.sub(r"<[^>]+>", " ", content)
            raw_chars = len(re.sub(r"\s+", "", clean_text))
            words = len(re.findall(r"\b\w+\b", clean_text))

            p_count = len(re.findall(r"<p\b", content, re.I))
            img_count = len(re.findall(r"<img\b|<image\b", content, re.I))

            total_chars += raw_chars
            total_words += words
            total_p_tags += p_count
            total_img_tags += img_count

            if words > 150:
                substantive_chapters += 1

            # Check trailing headings for exercise/application markers
            headings = re.findall(r"<h[1-6][^>]*>(.*?)</h[1-6]>", content, re.I)
            if headings:
                for h in headings[-2:]:  # Look at the last 2 headings
                    clean_h = re.sub(r"<[^>]+>", "", h).strip()
                    lower_h = clean_h.lower()
                    for marker in COMMON_EXERCISE_MARKERS:
                        if marker in lower_h:
                            stop_marker_hits[clean_h] = stop_marker_hits.get(clean_h, 0) + 1

        # Heuristic recommendations
        is_scanned_image_only = total_words < 500 and total_img_tags > 10
        recommended_voice = VOICE_MAP.get(lang, "en-US-GuyNeural")

        recommended_stop_marker = None
        if stop_marker_hits:
            # Pick marker appearing in the most chapters
            sorted_markers = sorted(stop_marker_hits.items(), key=lambda x: x[1], reverse=True)
            top_marker, top_count = sorted_markers[0]
            if top_count >= 2:
                recommended_stop_marker = top_marker

        # Synthesize CLI command
        cli_parts = ["python3", "universal_runner.py", f'"{path.as_posix()}"', "--tts-engine", "edge", "--publish"]
        if recommended_stop_marker:
            cli_parts.extend(["--stop-marker", f'"{recommended_stop_marker}"'])
        if lang != "en" and lang in VOICE_MAP:
            cli_parts.extend(["--auto-voice", recommended_voice])

        recommended_cmd = " ".join(cli_parts)

        return {
            "status": "ready" if not is_drm_locked and not is_scanned_image_only else "warning",
            "file": str(path),
            "title": title,
            "author": author,
            "language": lang,
            "chapters_count": len(spine_hrefs),
            "substantive_chapters": substantive_chapters,
            "total_words": total_words,
            "estimated_hours": round(total_words / 9000.0, 1),  # ~150 words/min -> 9,000 words/hr
            "is_drm_locked": is_drm_locked,
            "drm_reason": drm_reason,
            "is_scanned_image_only": is_scanned_image_only,
            "total_p_tags": total_p_tags,
            "total_img_tags": total_img_tags,
            "recommended_voice": recommended_voice,
            "recommended_stop_marker": recommended_stop_marker,
            "stop_marker_hits": stop_marker_hits,
            "recommended_cmd": recommended_cmd,
        }


def format_report(info: Dict[str, Any]) -> str:
    if info.get("status") == "blocked":
        return f"❌ [BLOCKED] {info.get('error')}"

    lines = [
        "==================================================",
        f"📖 EPUB 智能前置探查报告: {info['title']}",
        "==================================================",
        f"👤 作者: {info['author']}",
        f"🌐 语种: {info['language'].upper()} | 章节数: {info['substantive_chapters']} 核心轨 (总计 {info['chapters_count']} 个文档)",
        f"📊 文本体量: 约 {info['total_words']:,} 词 ({info['total_p_tags']:,} 段文字流) | 预估朗读时长: 约 {info['estimated_hours']} 小时",
    ]

    # Health Checks
    lines.append("\n🔍 排版与健康度门禁:")
    if info["is_drm_locked"]:
        lines.append(f"  ❌ DRM 加密: 已发现加密限制 ({info['drm_reason']}) -> 需解密")
    else:
        lines.append("  ✅ DRM 状态: 无版权锁 (Clean Reflowable)")

    if info["is_scanned_image_only"]:
        lines.append("  ❌ 版面类型: 扫描图片版 (文字流不足，需先走 OCR)")
    else:
        lines.append("  ✅ 版面类型: 标准重排语义文本流 (Reflowable XHTML)")

    # Stop markers
    if info["recommended_stop_marker"]:
        lines.append(f"  🎯 智能排雷: 检测到海量课后练习/讨论题，推荐截断标记: \"{info['recommended_stop_marker']}\" (覆盖 {info['stop_marker_hits'][info['recommended_stop_marker']]} 章)")
    else:
        lines.append("  ✅ 智能排雷: 未发现干扰正文的重复习题集，全文章节通读")

    # Final execution proposal
    lines.append("\n⚡ 推荐执行命令 (最优零配置方案):")
    lines.append(f"  {info['recommended_cmd']}")
    lines.append("==================================================")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect EPUB and synthesize optimal audiobook runner configuration.")
    parser.add_argument("epub", help="Path to input EPUB file")
    parser.add_argument("--json", action="store_true", help="Output raw JSON analysis")
    args = parser.parse_args()

    res = inspect_epub(args.epub)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(format_report(res))
