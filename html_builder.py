"""
Module: html_builder.py
Description: Compiles Multi-Chapter Apple Books-grade Interactive Readers with top-left dropdown switcher, zero-jitter word-by-word karaoke tracking, and unified tap inspection.
"""

import json
import html
import os
import re
import sys
import hashlib
from pathlib import Path
from artifact_io import atomic_write_text
from release_token import ReleaseToken, verify_release_token

def build_master_reader(book_title, book_subtitle, book_author, chapters_config, output_html_path,
                        *, release_token: ReleaseToken = None, release_report_path, book_id=None,
                        preview=False):
    """
    chapters_config: list of dicts with:
      - 'num': unique internal track number (e.g. 0, 1, 2)
      - 'title': str (e.g. 'The Cult of the Head Start')
      - 'role': optional 'preface', 'introduction', or 'chapter'
      - 'display_number': optional printed chapter number for role='chapter'
      - 'label': optional complete navigation/heading label override
      - 'audio': str (e.g. './audio/chapter_01.mp3')
      - 'aligned_json': str (path to aligned sentences JSON)
    """
    if book_id is None or not str(book_id).strip():
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(book_title).strip().lower()).strip("_")
        book_id = slug or "default"
    else:
        book_id = str(book_id).strip()

    output_html_path = os.path.abspath(output_html_path)
    book_dir = os.path.dirname(output_html_path)
    if preview:
        if release_token is not None:
            raise ValueError("Preview compilation must not receive a release token")
    else:
        verify_release_token(release_token, book_dir, release_report_path)
    with open(release_report_path, encoding="utf-8") as report_file:
        report = json.load(report_file)
    authorized = {
        os.path.abspath(os.path.join(book_dir, chapter["aligned"]))
        for chapter in report.get("chapters", []) if chapter.get("aligned")
    }
    requested = {os.path.abspath(c["aligned_json"]) for c in chapters_config}
    if requested != authorized:
        raise RuntimeError("HTML compilation chapter set does not match the validated release report")

    report_sha256 = hashlib.sha256(Path(release_report_path).read_bytes()).hexdigest()

    loaded_chapters = []
    for c in chapters_config:
        with open(c['aligned_json'], 'r', encoding='utf-8') as f:
            sents = json.load(f)
        role = c.get('role', 'preface' if c['num'] == 0 else 'chapter')
        display_number = c.get('display_number', c['num'] if role == 'chapter' else None)
        label = c.get('label')
        if not label:
            if role == 'preface':
                label = 'Preface'
            elif role == 'introduction':
                label = 'Introduction'
            elif role == 'chapter' and display_number is not None:
                label = f'Chapter {display_number}'
            else:
                label = c['title']
        loaded_chapters.append({
            'num': c['num'],
            'title': c['title'],
            'role': role,
            'display_number': display_number,
            'label': str(label),
            'audio': c['audio'],
            'public_audio': c.get('public_audio'),
            'sentences': sents
        })
        
    has_audio = any(bool(c.get('audio') or c.get('public_audio')) for c in loaded_chapters)
    first_ch_audio = loaded_chapters[0]['audio'] if (loaded_chapters and loaded_chapters[0].get('audio')) else ""
    first_ch_public_audio = loaded_chapters[0].get('public_audio') if loaded_chapters else None
    first_ch_num = loaded_chapters[0]['num'] if loaded_chapters else 0
    audio_src = first_ch_public_audio or first_ch_audio or "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQAAAAA="
    play_btn_attr = "" if has_audio else ' style="display: none;"'
    audio_track_attr = "" if has_audio else ' style="display: none;"'
    repeat_group_attr = "" if has_audio else ' style="display: none;"'
    
    html_head = f"""<!DOCTYPE html>
<html lang="en" data-theme="sepia">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="reader-release-report-sha256" content="{html.escape(report_sha256)}">
<meta name="reader-build-kind" content="{'experimental-preview' if preview else 'release'}">
<title>{html.escape(('EXPERIMENTAL PREVIEW — ' if preview else '') + book_title)}: {html.escape(book_subtitle)}</title>
<script>
(function() {{
  var bId = {json.dumps(book_id)};
  var t = localStorage.getItem('audible_theme') || localStorage.getItem('audible_reader_theme') || localStorage.getItem('reader_' + bId + '_theme') || localStorage.getItem(bId + '_theme');
  if (t && (t === 'sepia' || t === 'light' || t === 'dark')) {{
    document.documentElement.setAttribute('data-theme', t);
  }}
}})();
</script>
<style>
:root {{
  --font-serif: "Charter", "Iowan Old Style", "Palatino Linotype", "Georgia", "Source Han Serif SC", "PingFang SC", serif;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-size-base: 1.20rem;
  --line-height-base: 1.88;
  --max-content-width: 740px;
}}

[data-theme="sepia"] {{
  --bg-page: #fbf7ee;
  --bg-page-glass: rgba(251, 247, 238, 0.88);
  --bg-panel: #f4eee2;
  --bg-panel-glass: rgba(244, 238, 226, 0.92);
  --bg-hover: #eae1d2;
  --text-main: #2d261e;
  --text-sub: #786854;
  --accent: #92400e;
  --accent-light: #d97706;
  --word-highlight-bg: #fef08a;
  --word-highlight-text: #78350f;
  --border: #e6dcce;
  --border-subtle: rgba(45, 38, 30, 0.08);
  --card-shadow: 0 4px 20px rgba(45, 38, 30, 0.06);
}}

[data-theme="light"] {{
  --bg-page: #ffffff;
  --bg-page-glass: rgba(255, 255, 255, 0.88);
  --bg-panel: #f8f9fa;
  --bg-panel-glass: rgba(248, 249, 250, 0.92);
  --bg-hover: #f1f3f5;
  --text-main: #1a1a1a;
  --text-sub: #666666;
  --accent: #2563eb;
  --accent-light: #3b82f6;
  --word-highlight-bg: #dbeafe;
  --word-highlight-text: #1e40af;
  --border: #e5e7eb;
  --border-subtle: rgba(0, 0, 0, 0.06);
  --card-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}}

[data-theme="dark"] {{
  --bg-page: #12151c;
  --bg-page-glass: rgba(18, 21, 28, 0.88);
  --bg-panel: #1b202c;
  --bg-panel-glass: rgba(27, 32, 44, 0.92);
  --bg-hover: #262e3f;
  --text-main: #e2e8f0;
  --text-sub: #94a3b8;
  --accent: #60a5fa;
  --accent-light: #93c5fd;
  --word-highlight-bg: #2563eb;
  --word-highlight-text: #ffffff;
  --border: #2d3748;
  --border-subtle: rgba(255, 255, 255, 0.08);
  --card-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: var(--font-serif);
  background-color: var(--bg-page);
  color: var(--text-main);
  font-size: var(--font-size-base);
  line-height: var(--line-height-base);
  padding-bottom: 140px;
  transition: background-color 0.25s ease, color 0.25s ease;
  -webkit-font-smoothing: antialiased;
}}

/* Top Sticky Navigation Bar */
.top-nav {{
  position: sticky;
  top: 0;
  z-index: 1000;
  background: var(--bg-page-glass);
  border-bottom: 1px solid var(--border-subtle);
  box-shadow: 0 1px 12px rgba(0, 0, 0, 0.04);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  transition: background-color 0.25s ease, border-color 0.25s ease;
}}

.nav-bar {{
  max-width: var(--max-content-width);
  margin: 0 auto;
  padding: 8px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}}

.chapter-nav-wrapper {{
  position: relative;
  flex: 1;
  min-width: 0;
}}

.chapter-btn {{
  display: flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
  padding: 6px 14px;
  border-radius: 20px;
  font-family: var(--font-sans);
  font-size: 0.86rem;
  font-weight: 500;
  cursor: pointer;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  transition: all 0.2s ease;
}}

.chapter-btn:hover {{
  background: var(--bg-hover);
  border-color: var(--accent-light);
}}

.dropdown-arrow {{
  font-size: 0.72rem;
  color: var(--text-sub);
  margin-left: 2px;
}}

.chapter-dropdown {{
  display: none;
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  width: 290px;
  max-height: 420px;
  overflow-y: auto;
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  box-shadow: 0 16px 36px rgba(0, 0, 0, 0.12);
  padding: 6px;
  z-index: 2000;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}}

.chapter-dropdown.open {{
  display: block;
  animation: dropdownFadeIn 0.18s ease-out;
}}

@keyframes dropdownFadeIn {{
  from {{ opacity: 0; transform: translateY(-4px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

.chapter-item {{
  padding: 8px 12px;
  border-radius: 8px;
  font-family: var(--font-sans);
  font-size: 0.86rem;
  color: var(--text-main);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 2px;
  transition: background 0.15s ease;
}}

.chapter-item:hover {{
  background: var(--bg-hover);
}}

.chapter-item.active {{
  background: var(--bg-panel);
  color: var(--accent);
  font-weight: 600;
}}

.chapter-item-tag {{
  font-size: 0.70rem;
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}}

.nav-actions {{
  display: flex;
  align-items: center;
  gap: 8px;
}}

.icon-btn {{
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
  padding: 6px 14px;
  border-radius: 20px;
  font-family: var(--font-sans);
  font-size: 0.84rem;
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  transition: all 0.2s ease;
  line-height: 1.2;
}}

.icon-btn:hover {{
  background: var(--bg-hover);
  border-color: var(--accent-light);
}}

.icon-btn:active {{
  transform: scale(0.96);
}}

.icon-btn.primary {{
  background: var(--accent);
  color: #ffffff;
  border-color: var(--accent);
  font-weight: 600;
}}

.icon-btn.primary:hover {{
  filter: brightness(1.08);
}}

/* Collapsible Control Drawer */
.control-drawer {{
  display: none;
  background: var(--bg-panel-glass);
  border-bottom: 1px solid var(--border-subtle);
  padding: 14px 20px;
  max-height: calc(100vh - 60px);
  max-height: calc(100dvh - 60px);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  backdrop-filter: saturate(180%) blur(24px);
  -webkit-backdrop-filter: saturate(180%) blur(24px);
}}

.control-drawer.open {{
  display: block;
  animation: drawerSlideDown 0.22s cubic-bezier(0.16, 1, 0.3, 1);
}}

@keyframes drawerSlideDown {{
  from {{ opacity: 0; transform: translateY(-6px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

.drawer-inner {{
  max-width: var(--max-content-width);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
}}

.control-drawer audio {{
  width: 100%;
  height: 38px;
  border-radius: 20px;
  outline: none;
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
}}

[data-theme="dark"] .control-drawer audio {{
  filter: invert(0.88) hue-rotate(180deg) brightness(1.1);
}}

.drawer-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}}

.drawer-group {{
  display: flex;
  align-items: center;
  gap: 8px;
}}

.segmented-control {{
  display: inline-flex;
  align-items: center;
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  border-radius: 20px;
  padding: 2px 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}}

.seg-btn {{
  background: none;
  border: none;
  color: var(--text-main);
  font-family: var(--font-sans);
  font-size: 0.82rem;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.15s ease;
  line-height: 1.2;
}}

.seg-btn:hover {{
  background: var(--bg-hover);
}}

.seg-btn:active {{
  transform: scale(0.96);
}}

.seg-divider {{
  width: 1px;
  height: 14px;
  background: var(--border-subtle);
  margin: 0 1px;
}}

.seg-select {{
  background: none;
  border: none;
  color: var(--text-main);
  font-family: var(--font-sans);
  font-size: 0.82rem;
  font-weight: 500;
  padding: 4px 6px;
  border-radius: 16px;
  cursor: pointer;
  outline: none;
}}

.pill-btn {{
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  color: var(--text-main);
  padding: 5px 12px;
  border-radius: 20px;
  font-family: var(--font-sans);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  transition: all 0.15s ease;
  line-height: 1.2;
}}

.pill-btn:hover {{
  background: var(--bg-hover);
  border-color: var(--accent-light);
}}

.pill-btn:active {{
  transform: scale(0.96);
}}

.pill-btn.active {{
  background: var(--accent);
  color: #ffffff;
  border-color: var(--accent);
}}

.toggle-pill {{
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}}

.toggle-pill input[type="checkbox"] {{
  display: none;
}}

.toggle-badge {{
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: var(--bg-page);
  border: 1px solid var(--border-subtle);
  color: var(--text-sub);
  padding: 5px 12px;
  border-radius: 20px;
  font-family: var(--font-sans);
  font-size: 0.82rem;
  font-weight: 500;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
  transition: all 0.2s ease;
  line-height: 1.2;
}}

.toggle-pill input[type="checkbox"]:checked + .toggle-badge {{
  color: var(--text-main);
  border-color: var(--accent-light);
  background: var(--bg-hover);
}}

.toggle-pill input[type="checkbox"]:checked + .toggle-badge::before {{
  content: "✓ ";
  color: var(--accent);
  font-weight: 700;
}}

.drawer-tips {{
  display: none;
  font-family: var(--font-sans);
  font-size: 0.82rem;
  background: var(--bg-page);
  padding: 16px 20px;
  border-radius: 14px;
  border: 1px solid var(--border-subtle);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.03);
  animation: drawerSlideDown 0.2s ease-out;
}}

.drawer-tips.open {{
  display: block;
}}

.tips-columns {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}}

@media (max-width: 600px) {{
  .control-drawer {{
    padding: 10px 14px;
    max-height: calc(100vh - 54px);
    max-height: calc(100dvh - 54px);
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }}
  .drawer-inner {{
    gap: 10px;
  }}
  .drawer-row {{
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 8px;
  }}
  .drawer-group {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    width: 100%;
  }}
  .tips-columns {{
    grid-template-columns: 1fr;
    gap: 14px;
  }}
}}

.tips-section {{
  display: flex;
  flex-direction: column;
  gap: 8px;
}}

.tips-section-title {{
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 2px;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--border-subtle);
}}

.tips-row {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 0.82rem;
  color: var(--text-main);
  line-height: 1.4;
}}

.kbd-key {{
  display: inline-block;
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: 0.72rem;
  color: var(--text-main);
  background: var(--bg-panel);
  border: 1px solid var(--border-subtle);
  border-bottom: 2px solid var(--border);
  border-radius: 5px;
  padding: 2px 7px;
  box-shadow: 0 1px 1px rgba(0,0,0,0.06);
  white-space: nowrap;
}}

/* Main Layout */
.container {{
  max-width: var(--max-content-width);
  margin: 28px auto;
  padding: 0 20px;
}}

.chapter-section {{
  display: none;
}}

.chapter-section.active {{
  display: block;
}}

.book-header {{
  text-align: center;
  margin-bottom: 36px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border);
}}

.book-subtitle {{
  font-family: var(--font-sans);
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--accent);
  margin-bottom: 8px;
}}

.book-title {{
  font-size: 2.1rem;
  font-weight: 700;
  line-height: 1.25;
  margin-bottom: 10px;
}}

.book-author {{
  font-family: var(--font-sans);
  font-size: 0.95rem;
  color: var(--text-sub);
}}

/* Sentence Units & Tap Inspection */
.sentence-unit {{
  margin-bottom: 12px;
  border-radius: 8px;
  transition: background 0.15s ease;
}}

.sentence-text {{
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  transition: background 0.15s ease;
}}

.sentence-text:hover {{
  background: var(--bg-hover);
}}

.sentence-unit.active .sentence-text {{
  background: var(--bg-panel);
}}

.sentence-unit[data-matched="0"] .sentence-text {{
  opacity: 0.92;
}}

.w {{
  display: inline;
  border-radius: 3px;
  box-decoration-break: clone;
  -webkit-box-decoration-break: clone;
}}

.w.active-word {{
  background-color: var(--word-highlight-bg) !important;
  color: var(--word-highlight-text) !important;
  border-radius: 3px;
}}

/* Collapsible Inspection Card */
.inspect-panel {{
  display: none;
  background: var(--bg-panel);
  border-left: 3px solid var(--accent);
  border-radius: 0 8px 8px 0;
  padding: 10px 14px;
  margin: 6px 0 14px 6px;
  box-shadow: var(--card-shadow);
  cursor: pointer;
}}

.sentence-unit.active .inspect-panel {{
  display: block;
}}

.inspect-trans {{
  font-family: var(--font-serif);
  font-size: 1.02rem;
  line-height: 1.72;
  color: var(--text-main);
  margin-bottom: 8px;
}}

.inspect-vocab-list {{
  border-top: 1px solid var(--border);
  padding-top: 6px;
  margin-top: 6px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}}

.vocab-row {{
  font-family: var(--font-sans);
  font-size: 0.82rem;
  line-height: 1.45;
  display: flex;
  align-items: baseline;
  gap: 6px;
}}

.v-word {{
  font-weight: 700;
  color: var(--accent);
}}

.v-pos {{
  font-size: 0.72rem;
  color: var(--text-sub);
  font-style: italic;
}}

.v-def {{
  color: var(--text-main);
}}

.chapter-heading-1 {{
  font-size: 1.35rem;
  font-weight: 700;
  margin-top: 32px;
  margin-bottom: 12px;
  color: var(--accent);
  border-bottom: 1px solid var(--border);
  padding-bottom: 6px;
}}

.chapter-intext-heading {{
  font-family: var(--font-sans);
  font-size: 1.05rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  text-align: center;
  margin: 24px 0 16px;
  padding: 8px 12px;
}}

.epigraph-citation {{
  font-style: italic;
  color: var(--text-sub);
  font-size: 0.95rem;
  margin-bottom: 20px;
  padding-left: 16px;
  border-left: 2px solid var(--accent-light);
}}

/* Mobile Specific Refinements */
@media (max-width: 640px) {{
  :root {{
    --font-size-base: 1.15rem;
    --line-height-base: 1.82;
  }}
  .container {{
    padding: 0 14px;
    margin: 16px auto;
  }}
  .book-title {{
    font-size: 1.65rem;
  }}
  .nav-bar {{
    padding: 6px 12px;
  }}
  .icon-btn {{
    padding: 4px 10px;
    font-size: 0.78rem;
  }}
  .chapter-btn {{
    font-size: 0.85rem;
  }}
  .chapter-dropdown {{
    width: 240px;
  }}
}}
</style>
</head>
<body onclick="closeDropdowns(event)">

<header class="top-nav">
  <div class="nav-bar">
    <div class="chapter-nav-wrapper">
      <button class="chapter-btn" id="chapterSelectBtn" onclick="toggleChapterDropdown(event)">
        <span>{html.escape(book_title)} · <span id="currentChapterLabel">Ch. 0</span></span>
        <span class="dropdown-arrow">▾</span>
      </button>
      <div class="chapter-dropdown" id="chapterDropdown">
"""

    for ch in loaded_chapters:
        cnum = ch["num"]
        ctitle = ch["title"]
        label = ch["label"]
        active_cls = " active" if cnum == first_ch_num else ""
        html_head += f"""        <div class="chapter-item{active_cls}" id="menu-ch-{cnum}" onclick="switchChapter({cnum})">
          <span class="chapter-item-tag">{label}</span>
          <span>{html.escape(ctitle)}</span>
        </div>\n"""

    html_head += f"""      </div>
    </div>
    
    <div class="nav-actions">
      <button class="icon-btn primary" id="globalPlayBtn" onclick="toggleGlobalPlay()"{play_btn_attr}>▶ Play</button>
      <button class="icon-btn" id="drawerToggleBtn" onclick="toggleDrawer()">⚙️ Menu</button>
    </div>
  </div>
  
  <div class="control-drawer" id="controlDrawer">
    <div class="drawer-inner">
      <audio id="audioTrack" controls preload="metadata" src="{html.escape(audio_src)}"{audio_track_attr}></audio>
      <div class="drawer-row">
        <div class="drawer-group">
          <div class="segmented-control" role="group" aria-label="Font size">
            <button class="seg-btn" onclick="adjustFontSize(-1)" title="Decrease font size">A−</button>
            <div class="seg-divider"></div>
            <button class="seg-btn" onclick="adjustFontSize(1)" title="Increase font size">A+</button>
          </div>
          <button class="pill-btn" onclick="toggleTheme()" title="Switch theme (Sepia / Light / Dark)">🌓 Theme</button>
        </div>
        <div class="drawer-group"{repeat_group_attr}>
          <div class="segmented-control">
            <select id="shadowRepeatSelect" class="seg-select" onchange="setShadowRepetitions(this.value)" title="Repetitions">
              <option value="1">1×</option><option value="3" selected>3×</option><option value="5">5×</option>
            </select>
            <div class="seg-divider"></div>
            <button class="seg-btn" id="shadowBtn" onclick="toggleShadowing()">Repeat</button>
          </div>
        </div>
        <div class="drawer-group">
          <label class="toggle-pill" title="Auto-scroll to active sentence">
            <input type="checkbox" id="autoScrollCheck" checked onchange="toggleAutoScroll(this.checked)">
            <span class="toggle-badge">Auto-scroll</span>
          </label>
          <button class="pill-btn" id="tipsToggleBtn" onclick="toggleTips()" title="Keyboard & Gesture shortcuts">💡 Shortcuts</button>
        </div>
      </div>
      <div class="drawer-tips" id="drawerTips">
        <div class="tips-columns">
          <div class="tips-section">
            <div class="tips-section-title">Touch & Mouse</div>
            <div class="tips-row"><span class="kbd-key">Tap Sentence</span><span>{'Play audio & show breakdown' if has_audio else 'Show translation & vocabulary breakdown'}</span></div>
            <div class="tips-row"><span class="kbd-key">{'Double Tap' if has_audio else 'Tap Active'}</span><span>{'Repeat sentence loop' if has_audio else 'Collapse translation card'}</span></div>
            {f'<div class="tips-row"><span class="kbd-key">Tap Card</span><span>Collapse card</span></div>' if has_audio else ''}
          </div>
          <div class="tips-section">
            <div class="tips-section-title">Keyboard Shortcuts</div>
            <div class="tips-row"><span class="kbd-key">Space</span><span>Toggle breakdown card</span></div>
            <div class="tips-row"><span class="kbd-key">← / →</span><span>Previous / Next sentence</span></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</header>

<main class="container">
"""

    for ch in loaded_chapters:
        cnum = ch["num"]
        ctitle = ch["title"]
        caudio = ch["audio"]
        cpublic_audio = ch.get("public_audio") or ""
        csents = ch["sentences"]
        active_cls = " active" if cnum == first_ch_num else ""
        ch_heading_label = ch["label"].upper()
        clean_title = ctitle.strip()
        disp_num = str(ch.get("display_number")) if ch.get("display_number") is not None else ""
        disp_part = rf"|\b(?:Chapter\s+)?{re.escape(disp_num)}(?!\d)\s*[\.\:—–-]\s*" if disp_num else ""
        prefix_pattern = rf"^(?:{re.escape(ch['label'])}\s*[:—–-]?\s*{disp_part})"
        sub_title = re.sub(prefix_pattern, "", clean_title, flags=re.IGNORECASE).strip()
        if not sub_title or clean_title.upper() == ch_heading_label.upper() or clean_title.upper() == f"CHAPTER {cnum}":
            title_html = ch_heading_label
        else:
            title_html = f"{ch_heading_label}<br>{html.escape(sub_title)}"
        
        html_head += f"""
  <!-- CHAPTER {cnum} -->
  <section class="chapter-section{active_cls}" id="chapter-{cnum}" data-audio="{html.escape(caudio)}" data-public-audio="{html.escape(cpublic_audio)}" data-ch="{cnum}">
    <header class="book-header">
      <div class="book-subtitle">{html.escape(book_subtitle)}</div>
      <h1 class="book-title">{title_html}</h1>
      <div class="book-author">{html.escape(book_author)}</div>
    </header>

    <div class="book-content">
"""
        for s in csents:
            raw_sid = s["id"]
            sid = f"c{cnum}-{raw_sid}"
            is_h = s.get("is_heading", False)
            start = s.get("audio_start", s.get("start"))
            end = s.get("audio_end", s.get("end"))
            word_spans = s.get("word_spans", [])
            # Estimated words are useful diagnostic evidence but must never
            # turn a paraphrase into a clickable karaoke sentence.
            spans_are_observed = all(w.get("timing_source", "observed") == "observed" for w in word_spans)
            has_match = 1 if s.get("has_audio_match", True) and spans_are_observed and isinstance(start, (int, float)) and isinstance(end, (int, float)) and end > start else 0
            start_arg = "null" if start is None else str(start)
            end_arg = "null" if end is None else str(end)
            trans = html.escape(s.get("trans", ""))
            vocab = s.get("vocab", [])
            raw_text = s.get("text", "")
            
            word_html_list = []
            if word_spans:
                for w in word_spans:
                    rw = html.escape(w["word"])
                    ws = w["start"]
                    we = w["end"]
                    timing_source = html.escape(w.get("timing_source", "observed"))
                    word_html_list.append(f'<span class="w" data-s="{ws}" data-e="{we}" data-timing-source="{timing_source}">{rw}</span>')
            else:
                for rw in s["text"].split():
                    word_html_list.append(f'<span class="w" data-s="{start_arg}" data-e="{end_arg}">{html.escape(rw)}</span>')
            
            sentence_text_html = " ".join(word_html_list)
            
            vocab_html_list = []
            for v in vocab:
                vw = html.escape(v.get("word", ""))
                vp = html.escape(v.get("pos", ""))
                vd = html.escape(v.get("def", ""))
                vocab_html_list.append(f'<div class="vocab-row"><span class="v-word">{vw}</span><span class="v-pos">{vp}</span><span class="v-def">{vd}</span></div>')
                
            vocab_section = ""
            if vocab_html_list:
                vocab_section = f'<div class="inspect-vocab-list">{"".join(vocab_html_list)}</div>'
                
            h_class = ""
            if is_h:
                h_class += " chapter-heading-1"
            elif re.match(r"^CHAPTER\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN|NINETEEN|TWENTY|[A-Z\-]+|\d+)\s*$", raw_text.strip(), re.IGNORECASE):
                h_class += " chapter-intext-heading"
            elif raw_text.strip().startswith(("—", "–", "--", "- ")):
                h_class += " epigraph-citation"
            html_head += f"""
      <div class="sentence-unit" id="{sid}" data-start="{start_arg}" data-end="{end_arg}" data-audio-order="{s.get('audio_order', '')}" data-epigraph="{1 if s.get('alignment_method') == 'leading_epigraph_attribution' else 0}" data-matched="{has_match}" data-text="{html.escape(raw_text)}" data-trans="{trans}" data-vocab="{html.escape(json.dumps(vocab, ensure_ascii=False))}">
        <div class="sentence-text{h_class}" onclick="handleSentenceClick(event, '{sid}', {start_arg}, {end_arg}, {has_match})">
          <span class="s-content">{sentence_text_html}</span>
        </div>
        <div class="inspect-panel" onclick="handleInspectPanelClick(event, '{sid}')" title="Click to collapse / 点击折叠">
          <div class="inspect-trans">{trans}</div>
          {vocab_section}
        </div>
      </div>
"""

        html_head += """    </div>
  </section>
"""

    book_id_json = json.dumps(book_id)
    html_tail = f"""
</main>

<script>
window.__BOOK_ID__ = {book_id_json};
window.__INITIAL_CHAPTER__ = {first_ch_num};
window.__INITIAL_PUBLIC_AUDIO__ = {json.dumps(first_ch_public_audio)};
window.__HAS_AUDIO__ = {json.dumps(has_audio)};
const STORAGE_PREFIX = 'reader_' + (window.__BOOK_ID__ || 'default') + '_';
""" + """
const audio = document.getElementById('audioTrack');
const globalPlayBtn = document.getElementById('globalPlayBtn');
const controlDrawer = document.getElementById('controlDrawer');
const drawerToggleBtn = document.getElementById('drawerToggleBtn');
const chapterDropdown = document.getElementById('chapterDropdown');
const currentChapterLabel = document.getElementById('currentChapterLabel');

let activeChapterNum = parseInt(localStorage.getItem(STORAGE_PREFIX + 'active_ch') || String(window.__INITIAL_CHAPTER__), 10);
let autoScrollEnabled = localStorage.getItem(STORAGE_PREFIX + 'autoscroll') !== 'false';
let currentPlayingId = null;
let currentActiveWordEl = null;
let sentenceTimeIndex = [];
let syncFrameId = null;
const shadowState = { phase: 'idle', repetitions: 3, completed: 0, sentence: null, timer: null };

document.getElementById('autoScrollCheck').checked = autoScrollEnabled;

function toggleAutoScroll(enabled) {
  autoScrollEnabled = enabled;
  localStorage.setItem(STORAGE_PREFIX + 'autoscroll', enabled);
}

// Chapter Switching
function toggleChapterDropdown(event) {
  if (event) event.stopPropagation();
  chapterDropdown.classList.toggle('open');
}

function closeDropdowns(event) {
  if (chapterDropdown.classList.contains('open')) {
    chapterDropdown.classList.remove('open');
  }
}

function resolveAudioSource(section) {
  const localSource = section.dataset.audio;
  const publicSource = section.dataset.publicAudio;
  return window.location.protocol === 'file:' || !publicSource ? localSource : publicSource;
}

function reportLibraryProgress(chNum, pct) {
  try {
    const bookId = window.__BOOK_ID__ || (window.location.pathname.split('/').filter(Boolean).pop() || '').replace('.html', '');
    if (!bookId) return;
    const menuEl = document.getElementById('menu-ch-' + chNum);
    const tagText = menuEl ? menuEl.querySelector('.chapter-item-tag')?.textContent?.trim() : null;
    const titleText = menuEl ? menuEl.querySelector('span:not(.chapter-item-tag)')?.textContent?.trim() : null;
    const label = tagText || (chNum === 0 ? 'Preface' : ('Chapter ' + chNum));
    const progressData = {
      chapter: typeof chNum === 'number' ? chNum : 0,
      chapterLabel: label,
      chapterTitle: titleText || label,
      percent: Math.min(100, Math.max(0, Math.round(pct || 0))),
      updatedAt: Date.now()
    };
    localStorage.setItem('audible_progress_' + bookId, JSON.stringify(progressData));
    localStorage.setItem('audible_last_active_book', bookId);
  } catch (e) {}
}

function rebuildSentenceTimeIndex() {
  const section = document.querySelector('.chapter-section.active');
  sentenceTimeIndex = section ? Array.from(section.querySelectorAll('.sentence-unit')).map(el => ({
    start: parseFloat(el.dataset.start || '0'),
    end: parseFloat(el.dataset.end || '0'),
    el: el
  })).filter(item => Number.isFinite(item.start) && Number.isFinite(item.end) && item.end > item.start && item.el.dataset.matched !== '0').sort((a, b) => a.start - b.start) : [];
}

function findSentenceAt(time) {
  let low = 0;
  let high = sentenceTimeIndex.length - 1;
  let candidate = null;
  while (low <= high) {
    const middle = (low + high) >> 1;
    const item = sentenceTimeIndex[middle];
    if (item.start <= time) {
      candidate = item;
      low = middle + 1;
    } else {
      high = middle - 1;
    }
  }
  return candidate && time < candidate.end ? candidate.el : null;
}

function switchChapter(chNum) {
  activeChapterNum = chNum;
  localStorage.setItem(STORAGE_PREFIX + 'active_ch', chNum);
  
  const menuEl = document.getElementById('menu-ch-' + chNum);
  if (menuEl) {
    const tagText = menuEl.querySelector('.chapter-item-tag')?.textContent?.trim();
    currentChapterLabel.textContent = tagText || (chNum === 0 ? 'Preface' : 'Ch. ' + chNum);
  } else {
    currentChapterLabel.textContent = chNum === 0 ? 'Preface' : 'Ch. ' + chNum;
  }
  
  document.querySelectorAll('.chapter-item').forEach(el => el.classList.remove('active'));
  if (menuEl) menuEl.classList.add('active');
  chapterDropdown.classList.remove('open');
  
  document.querySelectorAll('.chapter-section').forEach(sec => {
    sec.classList.remove('active');
    if (parseInt(sec.dataset.ch, 10) === chNum) {
      sec.classList.add('active');
      const audioSrc = resolveAudioSource(sec);
      if (audio.getAttribute('src') !== audioSrc) {
        const wasPlaying = !audio.paused;
        audio.src = audioSrc;
        currentPlayingId = null;
        if (currentActiveWordEl) {
          currentActiveWordEl.classList.remove('active-word');
          currentActiveWordEl = null;
        }
        if (wasPlaying) audio.play();
      }
    }
  });
  rebuildSentenceTimeIndex();
  reportLibraryProgress(chNum, 0);
  
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

switchChapter(activeChapterNum);

function toggleDrawer() {
  const isOpen = controlDrawer.classList.contains('open');
  if (isOpen) {
    controlDrawer.classList.remove('open');
    drawerToggleBtn.innerHTML = '⚙️ Menu';
    localStorage.setItem(STORAGE_PREFIX + 'drawer_open', 'false');
  } else {
    controlDrawer.classList.add('open');
    drawerToggleBtn.innerHTML = '✕ Close';
    localStorage.setItem(STORAGE_PREFIX + 'drawer_open', 'true');
  }
}

const savedDrawerState = localStorage.getItem(STORAGE_PREFIX + 'drawer_open');
if (savedDrawerState === 'true') {
  controlDrawer.classList.add('open');
  drawerToggleBtn.innerHTML = '✕ Close';
}

const themes = ['sepia', 'light', 'dark'];

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'sepia';
  const curIdx = themes.indexOf(current);
  const next = themes[(curIdx >= 0 ? curIdx + 1 : 1) % themes.length];
  setTheme(next);
}

function setTheme(theme) {
  if (!themes.includes(theme)) return;
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem(STORAGE_PREFIX + 'theme', theme);
  localStorage.setItem('audible_reader_theme', theme);
  localStorage.setItem('audible_theme', theme);
  const themePreset = document.getElementById('themePreset');
  if (themePreset) themePreset.value = theme;
}

window.toggleTheme = toggleTheme;
window.setTheme = setTheme;

const savedTheme = localStorage.getItem('audible_theme') || localStorage.getItem('audible_reader_theme') || localStorage.getItem(STORAGE_PREFIX + 'theme') || 'sepia';
if (savedTheme && themes.includes(savedTheme)) {
  setTheme(savedTheme);
}
window.addEventListener('storage', event => {{
  if (event.key !== 'audible_theme' && event.key !== 'audible_reader_theme') return;
  if (themes.includes(event.newValue) && event.newValue !== document.documentElement.getAttribute('data-theme')) {{
    document.documentElement.setAttribute('data-theme', event.newValue);
    const themePreset = document.getElementById('themePreset');
    if (themePreset) themePreset.value = event.newValue;
  }}
}});

let currentFontSizeRem = 1.20;

function setFontSizePreset(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return;
  currentFontSizeRem = n;
  document.documentElement.style.setProperty('--font-size-base', n + 'rem');
  document.documentElement.style.setProperty('--reader-font-size', n + 'rem');
  localStorage.setItem(STORAGE_PREFIX + 'font_size_preset', String(n));
  localStorage.setItem(STORAGE_PREFIX + 'font_size', String(n));
  const sel = document.getElementById('fontSizePreset');
  if (sel) sel.value = String(n);
}

function adjustFontSize(delta) {
  const next = Math.max(0.95, Math.min(1.8, (currentFontSizeRem || 1.2) + delta * 0.1));
  setFontSizePreset(next);
}

window.setFontSizePreset = setFontSizePreset;
window.adjustFontSize = adjustFontSize;
window.applyFontSize = setFontSizePreset;

const savedFontSize = localStorage.getItem(STORAGE_PREFIX + 'font_size_preset') || localStorage.getItem(STORAGE_PREFIX + 'font_size') || '1.2';
setFontSizePreset(savedFontSize);

function toggleTips() {
  const tipsEl = document.getElementById('drawerTips');
  const btn = document.getElementById('tipsToggleBtn');
  if (tipsEl) {
    tipsEl.classList.toggle('open');
    if (btn) btn.classList.toggle('active');
  }
}

let lastSentenceClickTime = 0;
let lastSentenceClickId = null;

function startSentenceShadowing(sentenceEl) {
  if (!sentenceEl || sentenceEl.dataset.matched !== '1') return;
  if (shadowState.timer) clearTimeout(shadowState.timer);
  shadowState.phase = 'playing';
  shadowState.completed = 0;
  shadowState.sentence = sentenceEl;
  const btn = document.getElementById('shadowBtn');
  if (btn) btn.textContent = 'Stop Repeat';
  
  const activeSection = document.querySelector('.chapter-section.active') || document.querySelector('.chapter-section');
  if (activeSection) {
    const desiredSrc = resolveAudioSource(activeSection);
    if (desiredSrc && audio.getAttribute('src') !== desiredSrc) {
      audio.src = desiredSrc;
    }
  }
  const start = parseFloat(sentenceEl.dataset.start);
  audio.currentTime = start;
  audio.play();
  globalPlayBtn.textContent = '⏸ Pause';
  sentenceEl.classList.add('active');
}

function handleSentenceClick(event, id, start, end, hasMatch) {{
  if (event) event.stopPropagation();
  const el = document.getElementById(id);
  if (!el) return;
  
  const now = Date.now();
  const isDoubleTap = (lastSentenceClickId === id && (now - lastSentenceClickTime) < 350);
  lastSentenceClickTime = now;
  lastSentenceClickId = id;
  
  if (isDoubleTap && window.__HAS_AUDIO__) {{
    startSentenceShadowing(el);
    return;
  }}

  if (el.classList.contains('active') && !isDoubleTap) {{
    el.classList.remove('active');
    return;
  }}
  
  localStorage.setItem(STORAGE_PREFIX + 'last_sentence_c' + activeChapterNum, id);
  if (window.__HAS_AUDIO__ && hasMatch && Number.isFinite(start) && Number.isFinite(end) && end > start) {{
    audio.currentTime = start;
    audio.play();
    globalPlayBtn.textContent = '⏸ Pause';
  }}
  el.classList.add('active');
}}

function handleInspectPanelClick(event, id) {
  if (event) event.stopPropagation();
  const selection = window.getSelection();
  if (selection && selection.toString().trim().length > 0) return;
  
  const el = document.getElementById(id);
  if (el) {
    el.classList.remove('active');
  }
}

function toggleGlobalPlay() {
  if (audio.paused) {
    audio.play();
    globalPlayBtn.textContent = '⏸ Pause';
  } else {
    audio.pause();
    globalPlayBtn.textContent = '▶ Play';
  }
}

audio.preservesPitch = true;
audio.mozPreservesPitch = true;
audio.webkitPreservesPitch = true;

function setShadowRepetitions(value) {
  shadowState.repetitions = Math.max(1, parseInt(value, 10) || 3);
}

function stopShadowing() {
  if (shadowState.timer) clearTimeout(shadowState.timer);
  shadowState.phase = 'idle';
  shadowState.completed = 0;
  shadowState.sentence = null;
  shadowState.timer = null;
  const btn = document.getElementById('shadowBtn');
  if (btn) btn.textContent = 'Repeat';
}

function toggleShadowing() {
  if (shadowState.phase !== 'idle') {
    stopShadowing();
    return;
  }
  const sentence = findSentenceAt(audio.currentTime) || document.getElementById(currentPlayingId);
  if (sentence) {
    startSentenceShadowing(sentence);
  }
}

function advanceShadowing() {
  if (shadowState.phase === 'idle' || !shadowState.sentence) return;
  const end = parseFloat(shadowState.sentence.dataset.end);
  if (audio.currentTime < end) return;
  audio.pause();
  shadowState.completed += 1;
  if (shadowState.completed >= shadowState.repetitions) {
    stopShadowing();
    return;
  }
  shadowState.phase = 'pause_buffer';
  shadowState.timer = setTimeout(() => {
    if (!shadowState.sentence) return;
    shadowState.phase = 'replaying';
    audio.currentTime = parseFloat(shadowState.sentence.dataset.start);
    audio.play();
  }, 650);
}

function startSyncLoop() {
  if (syncFrameId === null && !audio.paused && !document.hidden) syncFrameId = requestAnimationFrame(syncPlayback);
}

function stopSyncLoop() {
  if (syncFrameId !== null) cancelAnimationFrame(syncFrameId);
  syncFrameId = null;
}

audio.addEventListener('play', () => { globalPlayBtn.textContent = '⏸ Pause'; startSyncLoop(); });
audio.addEventListener('pause', () => { globalPlayBtn.textContent = '▶ Play'; stopSyncLoop(); });
audio.addEventListener('timeupdate', () => {
  syncPlayback();
  if (!Number.isNaN(audio.currentTime) && audio.duration) {
    reportLibraryProgress(activeChapterNum, (audio.currentTime / audio.duration) * 100);
  }
});
document.addEventListener('visibilitychange', () => { if (document.hidden) stopSyncLoop(); else startSyncLoop(); });

function syncPlayback() {
  syncFrameId = null;
  if (!audio.paused) {
    const curTime = audio.currentTime;
    const activeSection = document.querySelector('.chapter-section.active');
    
    if (activeSection) {
      const activeUnit = findSentenceAt(curTime);
      
      if (activeUnit) {
        if (activeUnit.id !== currentPlayingId) {
          currentPlayingId = activeUnit.id;
          localStorage.setItem(STORAGE_PREFIX + 'last_sentence_c' + activeChapterNum, activeUnit.id);
          
          if (autoScrollEnabled) {
            const rect = activeUnit.getBoundingClientRect();
            const inView = rect.top >= 90 && rect.bottom <= (window.innerHeight - 90);
            if (!inView) {
              activeUnit.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
          }
        }
        
        const wordEls = activeUnit.querySelectorAll('.w');
        let foundWord = null;
        for (let w of wordEls) {
          const ws = parseFloat(w.dataset.s);
          const we = parseFloat(w.dataset.e);
          if (ws < we && curTime >= ws && curTime < we) {
            foundWord = w;
            break;
          }
        }
        
        if (foundWord !== currentActiveWordEl) {
          if (currentActiveWordEl) currentActiveWordEl.classList.remove('active-word');
          if (foundWord) foundWord.classList.add('active-word');
          currentActiveWordEl = foundWord;
        }
      } else {
        if (currentActiveWordEl) {
          currentActiveWordEl.classList.remove('active-word');
          currentActiveWordEl = null;
        }
      }
    }
    advanceShadowing();
  }
  startSyncLoop();
}

rebuildSentenceTimeIndex();

// Desktop Keyboard Navigation (Arrow Keys + Spacebar)
window.addEventListener('keydown', (e) => {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
    return;
  }
  
  const activeSection = document.querySelector('.chapter-section.active');
  if (!activeSection) return;
  
  const units = Array.from(activeSection.querySelectorAll('.sentence-unit'));
  if (units.length === 0) return;
  
  const curTime = audio.currentTime;
  
  let activeUnit = activeSection.querySelector('.sentence-unit.active');
  let currentIndex = activeUnit ? units.indexOf(activeUnit) : -1;
  if (currentIndex === -1 && window.__HAS_AUDIO__ && audio && !isNaN(audio.currentTime) && audio.currentTime > 0) {
    const curTime = audio.currentTime;
    currentIndex = units.findIndex(u => {
      const s = parseFloat(u.dataset.start);
      const e = parseFloat(u.dataset.end);
      return curTime >= s && curTime <= e;
    });
    if (currentIndex === -1) {
      for (let i = units.length - 1; i >= 0; i--) {
        if (parseFloat(units[i].dataset.start) <= curTime) {
          currentIndex = i;
          break;
        }
      }
    }
  }
  if (currentIndex === -1) currentIndex = 0;
  
  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
    e.preventDefault();
    const targetIdx = Math.max(0, currentIndex - 1);
    const targetUnit = units[targetIdx];
    if (targetUnit) {
      if (activeUnit) activeUnit.classList.remove('active');
      targetUnit.classList.add('active');
      if (window.__HAS_AUDIO__ && targetUnit.dataset.matched === '1') {
        const st = parseFloat(targetUnit.dataset.start);
        if (!isNaN(st)) {
          audio.currentTime = st;
          audio.play();
          globalPlayBtn.textContent = '⏸ Pause';
        }
      }
      targetUnit.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
    e.preventDefault();
    const targetIdx = Math.min(units.length - 1, currentIndex + 1);
    const targetUnit = units[targetIdx];
    if (targetUnit) {
      if (activeUnit) activeUnit.classList.remove('active');
      targetUnit.classList.add('active');
      if (window.__HAS_AUDIO__ && targetUnit.dataset.matched === '1') {
        const st = parseFloat(targetUnit.dataset.start);
        if (!isNaN(st)) {
          audio.currentTime = st;
          audio.play();
          globalPlayBtn.textContent = '⏸ Pause';
        }
      }
      targetUnit.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  } else if (e.code === 'Space') {
    e.preventDefault();
    const currentUnit = units[currentIndex];
    if (currentUnit) {
      currentUnit.classList.toggle('active');
    }
  }
});
</script>
</body>
</html>
"""
    # The tail is assembled from a mixture of f-string and plain-string
    # fragments. Normalize escaped braces from the plain fragment before
    # writing JavaScript to the generated document.
    html_tail = html_tail.replace("{{", "{").replace("}}", "}")
    atomic_write_text(output_html_path, html_head + html_tail)
        
    print(f"Master multi-chapter interactive reader successfully compiled -> {output_html_path}")
