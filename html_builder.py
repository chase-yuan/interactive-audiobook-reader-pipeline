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
            'editorial_notice': c.get('editorial_notice'),
            'sentences': sents
        })
        
    has_audio = any(bool(c.get('audio') or c.get('public_audio')) for c in loaded_chapters)
    first_ch_audio = loaded_chapters[0]['audio'] if (loaded_chapters and loaded_chapters[0].get('audio')) else ""
    first_ch_public_audio = loaded_chapters[0].get('public_audio') if loaded_chapters else None
    first_ch_num = loaded_chapters[0]['num'] if loaded_chapters else 0
    first_ch_label = loaded_chapters[0]['label'].replace('Chapter ', 'Ch. ') if loaded_chapters else 'Ch. 1'
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
  if (t && (t === 'sepia' || t === 'light' || t === 'dark' || t === 'night')) {{
    document.documentElement.setAttribute('data-theme', t);
  }}
  var hideCh = localStorage.getItem('reader_' + bId + '_hide_chinese') || localStorage.getItem('audible_hide_chinese');
  if (hideCh === 'true') {{
    document.documentElement.setAttribute('data-hide-chinese', 'true');
  }}
}})();
</script>
<style>
:root {{
  /* --- Typography Tokens --- */
  --font-serif: "Charter", "Iowan Old Style", "Palatino Linotype", "Georgia", "Source Han Serif SC", "PingFang SC", serif;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-size-2xs: 0.70rem;
  --font-size-xs: 0.72rem;
  --font-size-sm: 0.82rem;
  --font-size-ui: 0.86rem;
  --font-size-sub: 0.95rem;
  --font-size-trans: 1.02rem;
  --font-size-h3: 1.05rem;
  --font-size-base: 1.20rem;
  --font-size-h2: 1.35rem;
  --font-size-h1: 2.10rem;

  --line-height-btn: 1.2;
  --line-height-tight: 1.25;
  --line-height-normal: 1.45;
  --line-height-relaxed: 1.72;
  --line-height-base: 1.88;

  /* --- Spacing Scale (4px/8px modular grid) --- */
  --space-3xs: 1px;
  --space-2xs: 2px;
  --space-xs: 4px;
  --space-sm: 6px;
  --space-md: 8px;
  --space-base: 10px;
  --space-lg: 12px;
  --space-xl: 14px;
  --space-2xl: 16px;
  --space-3xl: 20px;
  --space-4xl: 24px;
  --space-5xl: 28px;
  --space-6xl: 32px;
  --space-7xl: 36px;
  --space-bottom-clearance: 140px;

  /* --- Sizing Tokens --- */
  --max-content-width: 740px;
  --dropdown-width: 290px;
  --dropdown-max-height: 420px;
  --audio-track-height: 38px;
  --seg-divider-height: 14px;

  /* --- Radius Scale --- */
  --radius-xs: 3px;
  --radius-sm: 5px;
  --radius-md: 6px;
  --radius-base: 8px;
  --radius-lg: 14px;
  --radius-xl: 16px;
  --radius-pill: 20px;
  --radius-full: 9999px;

  /* --- Elevation & Shadows --- */
  --shadow-subtle: 0 1px 2px rgba(0, 0, 0, 0.03);
  --shadow-kbd: 0 1px 1px rgba(0, 0, 0, 0.06);
  --shadow-nav: 0 1px 12px rgba(0, 0, 0, 0.04);
  --shadow-floating: 0 16px 36px rgba(0, 0, 0, 0.12);
  --shadow-drawer-box: 0 4px 16px rgba(0, 0, 0, 0.03);

  /* --- Z-Indices --- */
  --z-nav: 1000;
  --z-dropdown: 2000;

  /* --- Transitions & Timing --- */
  --transition-fast: 0.15s ease;
  --transition-base: 0.20s ease;
  --transition-smooth: 0.25s ease;
  --transition-drawer: 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  --transition-dropdown: 0.18s ease-out;

  /* --- Backdrop Filters --- */
  --blur-nav: saturate(180%) blur(20px);
  --blur-drawer: saturate(180%) blur(24px);
  --blur-dropdown: blur(20px);

  /* --- Universal Semantic Tokens --- */
  --btn-primary-text: #ffffff;
}}

/* Theme 1: Sepia (Parchment Paper - Warm & Calming) */
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
  --audio-filter: none;
}}

/* Theme 2: Light (Studio Clean Day - High Contrast) */
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
  --audio-filter: none;
}}

/* Theme 3: Dark (Slate Evening - Preserves #12151c Contract) */
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
  --audio-filter: invert(0.88) hue-rotate(180deg) brightness(1.1);
}}

/* Theme 4: Night (True OLED Obsidian Black) */
[data-theme="night"] {{
  --bg-page: #000000;
  --bg-page-glass: rgba(0, 0, 0, 0.92);
  --bg-panel: #0d1117;
  --bg-panel-glass: rgba(13, 17, 23, 0.94);
  --bg-hover: #161b22;
  --text-main: #e6edf3;
  --text-sub: #8b949e;
  --accent: #58a6ff;
  --accent-light: #79c0ff;
  --word-highlight-bg: #1f6feb;
  --word-highlight-text: #ffffff;
  --border: #21262d;
  --border-subtle: rgba(240, 246, 252, 0.1);
  --card-shadow: 0 4px 24px rgba(0, 0, 0, 0.6);
  --audio-filter: invert(0.92) hue-rotate(180deg) brightness(1.1);
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
  font-family: var(--font-serif);
  background-color: var(--bg-page);
  color: var(--text-main);
  font-size: var(--font-size-base);
  line-height: var(--line-height-base);
  padding-bottom: var(--space-bottom-clearance);
  transition: background-color var(--transition-smooth), color var(--transition-smooth);
  -webkit-font-smoothing: antialiased;
}}

/* Top Sticky Navigation Bar */
.top-nav {{
  position: sticky;
  top: 0;
  z-index: var(--z-nav);
  background: var(--bg-page-glass);
  border-bottom: var(--space-3xs) solid var(--border-subtle);
  box-shadow: var(--shadow-nav);
  backdrop-filter: var(--blur-nav);
  -webkit-backdrop-filter: var(--blur-nav);
  transition: background-color var(--transition-smooth), border-color var(--transition-smooth);
}}

.nav-bar {{
  max-width: var(--max-content-width);
  margin: 0 auto;
  padding: var(--space-md) var(--space-2xl);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-lg);
}}

.chapter-nav-wrapper {{
  position: relative;
  flex: 1;
  min-width: 0;
}}

.chapter-btn {{
  display: flex;
  align-items: center;
  gap: var(--space-sm);
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  color: var(--text-main);
  padding: var(--space-sm) var(--space-xl);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--font-size-ui);
  font-weight: 500;
  cursor: pointer;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  box-shadow: var(--shadow-subtle);
  transition: all var(--transition-base);
}}

.chapter-btn:hover {{
  background: var(--bg-hover);
  border-color: var(--accent-light);
}}

.dropdown-arrow {{
  font-size: var(--font-size-xs);
  color: var(--text-sub);
  margin-left: var(--space-2xs);
}}

.chapter-dropdown {{
  display: none;
  position: absolute;
  top: calc(100% + var(--space-md));
  left: 0;
  width: var(--dropdown-width);
  max-height: var(--dropdown-max-height);
  overflow-y: auto;
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-floating);
  padding: var(--space-sm);
  z-index: var(--z-dropdown);
  backdrop-filter: var(--blur-dropdown);
  -webkit-backdrop-filter: var(--blur-dropdown);
}}

.chapter-dropdown.open {{
  display: block;
  animation: dropdownFadeIn var(--transition-dropdown);
}}

@keyframes dropdownFadeIn {{
  from {{ opacity: 0; transform: translateY(-4px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}

.chapter-item {{
  padding: var(--space-md) var(--space-lg);
  border-radius: var(--radius-base);
  font-family: var(--font-sans);
  font-size: var(--font-size-ui);
  color: var(--text-main);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: var(--space-2xs);
  transition: background var(--transition-fast);
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
  font-size: var(--font-size-2xs);
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}}

.nav-actions {{
  display: flex;
  align-items: center;
  gap: var(--space-md);
}}

.icon-btn {{
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  color: var(--text-main);
  padding: var(--space-sm) var(--space-xl);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: var(--radius-sm);
  box-shadow: var(--shadow-subtle);
  transition: all var(--transition-base);
  line-height: var(--line-height-btn);
}}

.icon-btn:hover {{
  background: var(--bg-hover);
  border-color: var(--accent-light);
}}

.icon-btn:active {{
  opacity: 0.85;
}}

.icon-btn.primary {{
  background: var(--accent);
  color: var(--btn-primary-text);
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
  border-bottom: var(--space-3xs) solid var(--border-subtle);
  padding: var(--space-xl) var(--space-3xl);
  max-height: calc(100vh - 60px);
  max-height: calc(100dvh - 60px);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  backdrop-filter: var(--blur-drawer);
  -webkit-backdrop-filter: var(--blur-drawer);
}}

.control-drawer.open {{
  display: block;
  animation: drawerSlideDown var(--transition-drawer);
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
  gap: var(--space-lg);
}}

.hidden-audio {{
  display: none !important;
}}

.audio-player-bar {{
  display: flex;
  align-items: center;
  gap: var(--space-md);
  padding: var(--space-xs) var(--space-lg);
  background: var(--bg-panel);
  border: var(--space-3xs) solid var(--border-subtle);
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-subtle);
  min-height: var(--audio-track-height);
  box-sizing: border-box;
}}

.player-speed-btn {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: var(--space-7xl);
  height: var(--space-5xl);
  padding: 0 var(--space-md);
  border-radius: var(--radius-pill);
  background: var(--bg-page);
  color: var(--text-main);
  border: var(--space-3xs) solid var(--border-subtle);
  cursor: pointer;
  font-family: var(--font-sans);
  font-size: var(--font-size-xs);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  line-height: 1;
  flex-shrink: 0;
  user-select: none;
  box-shadow: var(--shadow-subtle);
  transition: background var(--transition-fast), color var(--transition-fast), border-color var(--transition-fast), opacity var(--transition-fast);
}}

.player-speed-btn:hover {{
  background: var(--accent);
  color: var(--btn-primary-text);
  border-color: var(--accent);
  filter: brightness(1.08);
}}

.player-speed-btn:active {{
  opacity: 0.85;
}}

.player-speed-btn.custom-speed {{
  background: var(--accent);
  color: var(--btn-primary-text);
  border-color: var(--accent);
}}

.player-time {{
  font-family: var(--font-sans);
  font-size: var(--font-size-xs);
  color: var(--text-sub);
  font-variant-numeric: tabular-nums;
  min-width: var(--space-7xl);
  text-align: center;
  flex-shrink: 0;
  user-select: none;
}}

.player-slider-wrap {{
  flex: 1;
  display: flex;
  align-items: center;
  position: relative;
  min-width: 0;
}}

.player-slider {{
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: var(--space-xs);
  background: var(--border);
  border-radius: var(--radius-full);
  outline: none;
  cursor: pointer;
  margin: 0;
}}

.player-slider::-webkit-slider-thumb {{
  -webkit-appearance: none;
  appearance: none;
  width: var(--space-lg);
  height: var(--space-lg);
  border-radius: var(--radius-full);
  background: var(--accent);
  cursor: pointer;
  box-shadow: var(--shadow-kbd);
  transition: filter var(--transition-fast);
}}

.player-slider::-webkit-slider-thumb:hover {{
  filter: brightness(1.15);
}}

.player-slider::-moz-range-thumb {{
  width: var(--space-lg);
  height: var(--space-lg);
  border: none;
  border-radius: var(--radius-full);
  background: var(--accent);
  cursor: pointer;
  box-shadow: var(--shadow-kbd);
  transition: filter var(--transition-fast);
}}

.player-slider::-moz-range-thumb:hover {{
  filter: brightness(1.15);
}}

.drawer-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-base);
}}

.drawer-group {{
  display: flex;
  align-items: center;
  gap: var(--space-md);
}}

.segmented-control {{
  display: inline-flex;
  align-items: center;
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  border-radius: var(--radius-pill);
  padding: var(--space-2xs) var(--space-xs);
  box-shadow: var(--shadow-subtle);
}}

.seg-btn {{
  background: none;
  border: none;
  color: var(--text-main);
  font-family: var(--font-sans);
  font-size: var(--font-size-sm);
  font-weight: 500;
  padding: var(--space-xs) var(--space-base);
  border-radius: var(--radius-xl);
  cursor: pointer;
  transition: all var(--transition-fast);
  line-height: var(--line-height-btn);
}}

.seg-btn:hover {{
  background: var(--bg-hover);
}}

.seg-btn:active {{
  opacity: 0.85;
}}

.seg-btn.active {{
  background: var(--bg-hover);
  color: var(--accent);
  font-weight: 600;
}}

.seg-divider {{
  width: var(--space-3xs);
  height: var(--seg-divider-height);
  background: var(--border-subtle);
  margin: 0 var(--space-3xs);
}}

.seg-select {{
  background: none;
  border: none;
  color: var(--text-main);
  font-family: var(--font-sans);
  font-size: var(--font-size-sm);
  font-weight: 500;
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-xl);
  cursor: pointer;
  outline: none;
}}

.pill-btn {{
  display: inline-flex;
  align-items: center;
  gap: var(--radius-sm);
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  color: var(--text-main);
  padding: var(--radius-sm) var(--space-lg);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  box-shadow: var(--shadow-subtle);
  transition: all var(--transition-fast);
  line-height: var(--line-height-btn);
}}

.pill-btn:hover {{
  background: var(--bg-hover);
  border-color: var(--accent-light);
}}

.pill-btn:active {{
  opacity: 0.85;
}}

.pill-btn.active {{
  background: var(--accent);
  color: var(--btn-primary-text);
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
  gap: var(--radius-sm);
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  color: var(--text-sub);
  padding: var(--radius-sm) var(--space-lg);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--font-size-sm);
  font-weight: 500;
  box-shadow: var(--shadow-subtle);
  transition: all var(--transition-base);
  line-height: var(--line-height-btn);
}}

.toggle-pill input[type="checkbox"]:checked + .toggle-badge {{
  color: var(--text-main);
  border-color: var(--accent-light);
  background: var(--bg-hover);
}}

.toggle-pill input[type="checkbox"]:checked + .toggle-badge::before {{
  content: "";
  display: inline-block;
  width: var(--space-sm);
  height: var(--space-sm);
  border-radius: var(--radius-full);
  background-color: var(--accent);
  margin-right: var(--space-xs);
}}

.drawer-tips {{
  display: none;
  font-family: var(--font-sans);
  font-size: var(--font-size-sm);
  background: var(--bg-page);
  padding: var(--space-2xl) var(--space-3xl);
  border-radius: var(--radius-lg);
  border: var(--space-3xs) solid var(--border-subtle);
  box-shadow: var(--shadow-drawer-box);
  animation: drawerSlideDown var(--transition-base);
}}

.drawer-tips.open {{
  display: block;
}}

.tips-columns {{
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4xl);
}}

@media (max-width: 600px) {{
  .control-drawer {{
    padding: var(--space-base) var(--space-xl);
    max-height: calc(100vh - 54px);
    max-height: calc(100dvh - 54px);
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }}
  .drawer-inner {{
    gap: var(--space-base);
  }}
  .drawer-row {{
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-md);
  }}
  .drawer-group {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-sm);
    width: 100%;
  }}
  .tips-columns {{
    grid-template-columns: 1fr;
    gap: var(--space-xl);
  }}
}}

.tips-section {{
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}}

.tips-section-title {{
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: var(--space-2xs);
  padding-bottom: var(--space-xs);
  border-bottom: var(--space-3xs) solid var(--border-subtle);
}}

.tips-row {{
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-lg);
  font-size: var(--font-size-sm);
  color: var(--text-main);
  line-height: var(--line-height-normal);
}}

.kbd-key {{
  display: inline-block;
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: var(--font-size-xs);
  color: var(--text-main);
  background: var(--bg-panel);
  border: var(--space-3xs) solid var(--border-subtle);
  border-bottom: var(--space-2xs) solid var(--border);
  border-radius: var(--radius-sm);
  padding: var(--space-2xs) var(--space-sm);
  box-shadow: var(--shadow-kbd);
  white-space: nowrap;
}}

/* Main Layout */
.container {{
  max-width: var(--max-content-width);
  margin: var(--space-5xl) auto;
  padding: 0 var(--space-3xl);
}}

.chapter-section {{
  display: none;
}}

.chapter-section.active {{
  display: block;
}}

.book-header {{
  text-align: center;
  margin-bottom: var(--space-7xl);
  padding-bottom: var(--space-3xl);
  border-bottom: var(--space-3xs) solid var(--border);
}}

.book-subtitle {{
  font-family: var(--font-sans);
  font-size: var(--font-size-ui);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--accent);
  margin-bottom: var(--space-md);
}}

.book-title {{
  font-size: var(--font-size-h1);
  font-weight: 700;
  line-height: var(--line-height-tight);
  margin-bottom: var(--space-base);
}}

.book-author {{
  font-family: var(--font-sans);
  font-size: var(--font-size-sub);
  color: var(--text-sub);
}}

/* Sentence Units & Tap Inspection */
.sentence-unit {{
  margin-bottom: var(--space-lg);
  border-radius: var(--radius-base);
  transition: background var(--transition-fast);
}}

.sentence-text {{
  cursor: pointer;
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}}

.sentence-text:hover {{
  background: var(--bg-hover);
}}

.sentence-unit.active .sentence-text {{
  background: var(--bg-panel);
}}

.sentence-unit[data-matched="0"] .sentence-text {{
  opacity: 0.88;
}}

.un-narrated-tag {{
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: var(--radius-xs);
  background: var(--bg-hover);
  color: var(--text-muted);
  border: 1px solid var(--border);
  margin-left: 6px;
  vertical-align: middle;
  cursor: default;
  user-select: none;
}}

.inspect-audio-notice {{
  font-size: 0.82rem;
  color: var(--text-muted);
  margin-bottom: var(--space-xs);
  font-style: italic;
}}

.editorial-notice-box {{
  display: flex;
  align-items: flex-start;
  gap: var(--space-md);
  margin: var(--space-2xl) 0 var(--space-xl) 0;
  padding: var(--space-md) var(--space-lg);
  border-radius: var(--radius-base);
  background: var(--bg-panel);
  border: 1px dashed var(--accent);
  color: var(--text-muted);
  font-size: 0.88rem;
  line-height: 1.6;
}}

.editorial-notice-box .notice-icon {{
  font-size: 1.15rem;
  flex-shrink: 0;
}}

.editorial-notice-box .notice-content {{
  flex: 1;
}}

#reader-toast {{
  position: fixed;
  bottom: calc(var(--player-height, 64px) + var(--space-xl));
  left: 50%;
  transform: translateX(-50%) translateY(var(--space-md));
  background: var(--text-main);
  color: var(--bg-page);
  padding: var(--space-sm) var(--space-xl);
  border-radius: var(--radius-sm);
  font-size: var(--font-size-xs);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  box-shadow: var(--card-shadow);
  pointer-events: none;
  opacity: 0;
  transition: opacity var(--transition-fast), transform var(--transition-fast);
  z-index: 10000;
}}

#reader-toast.show {{
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}}

.w {{
  display: inline;
  border-radius: var(--radius-xs);
  box-decoration-break: clone;
  -webkit-box-decoration-break: clone;
}}

.w.active-word {{
  background-color: var(--word-highlight-bg) !important;
  color: var(--word-highlight-text) !important;
  border-radius: var(--radius-xs);
}}

/* Collapsible Inspection Card */
.inspect-panel {{
  display: none;
  background: var(--bg-panel);
  border-left: var(--space-xs) solid var(--accent);
  border-radius: 0 var(--radius-base) var(--radius-base) 0;
  padding: var(--space-base) var(--space-xl);
  margin: var(--space-sm) 0 var(--space-xl) var(--space-sm);
  box-shadow: var(--card-shadow);
  cursor: pointer;
}}

.sentence-unit.active:not(.card-collapsed) .inspect-panel {{
  display: block;
}}

/* Global Chinese Lock (Pure English Listening Mode) */
[data-hide-chinese="true"] .inspect-panel {{
  display: none !important;
}}


.inspect-trans {{
  font-family: var(--font-serif);
  font-size: var(--font-size-trans);
  line-height: var(--line-height-relaxed);
  color: var(--text-main);
  margin-bottom: var(--space-md);
}}

.inspect-vocab-list {{
  border-top: var(--space-3xs) solid var(--border);
  padding-top: var(--space-sm);
  margin-top: var(--space-sm);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}}

.vocab-row {{
  font-family: var(--font-sans);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-normal);
  display: flex;
  align-items: baseline;
  gap: var(--space-sm);
}}

.v-word {{
  font-weight: 700;
  color: var(--accent);
}}

.v-pos {{
  font-size: var(--font-size-xs);
  color: var(--text-sub);
  font-style: italic;
}}

.v-def {{
  color: var(--text-main);
}}

.chapter-heading-1 {{
  font-size: var(--font-size-h2);
  font-weight: 700;
  margin-top: var(--space-6xl);
  margin-bottom: var(--space-lg);
  color: var(--accent);
  border-bottom: var(--space-3xs) solid var(--border);
  padding-bottom: var(--space-sm);
}}

.chapter-intext-heading {{
  font-family: var(--font-sans);
  font-size: var(--font-size-h3);
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  text-align: center;
  margin: var(--space-4xl) 0 var(--space-2xl);
  padding: var(--space-md) var(--space-lg);
}}

.epigraph-citation {{
  font-style: italic;
  color: var(--text-sub);
  font-size: var(--font-size-sub);
  margin-bottom: var(--space-3xl);
  padding-left: var(--space-2xl);
  border-left: var(--space-2xs) solid var(--accent-light);
}}

/* Mobile Specific Refinements */
@media (max-width: 640px) {{
  :root {{
    --font-size-base: 1.15rem;
    --line-height-base: 1.82;
  }}
  .container {{
    padding: 0 var(--space-xl);
    margin: var(--space-2xl) auto;
  }}
  .book-title {{
    font-size: 1.65rem;
  }}
  .nav-bar {{
    padding: var(--space-sm) var(--space-lg);
  }}
  .icon-btn {{
    padding: var(--space-xs) var(--space-base);
    font-size: 0.78rem;
  }}
  .chapter-btn {{
    font-size: var(--font-size-ui);
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
        <span>{html.escape(book_title)} · <span id="currentChapterLabel">{html.escape(first_ch_label)}</span></span>
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
      <button class="icon-btn" id="drawerToggleBtn" onclick="toggleDrawer()">Menu</button>
    </div>
  </div>
  
  <div class="control-drawer" id="controlDrawer">
    <div class="drawer-inner">
      <div class="audio-player-bar" id="audioPlayerBar"{audio_track_attr}>
        <button class="player-speed-btn" id="audioSpeedBtn" onclick="cyclePlaybackRate()" title="Playback speed / 播放速度" aria-label="Playback speed">1.0×</button>
        <span class="player-time" id="playerCurTime">00:00</span>
        <div class="player-slider-wrap">
          <input type="range" class="player-slider" id="playerScrubber" min="0" max="100" value="0" step="0.1" aria-label="Playback scrubber">
        </div>
        <span class="player-time" id="playerTotalTime">00:00</span>
        <audio id="audioTrack" preload="metadata" src="{html.escape(audio_src)}" class="hidden-audio"{audio_track_attr}></audio>
      </div>
      <div class="drawer-row">
        <div class="drawer-group">
          <div class="segmented-control" role="group" aria-label="Font size">
            <button class="seg-btn" onclick="adjustFontSize(-1)" title="Decrease font size">A−</button>
            <div class="seg-divider"></div>
            <button class="seg-btn" onclick="adjustFontSize(1)" title="Increase font size">A+</button>
          </div>
          <div class="segmented-control" id="chineseLockBtn" role="group" aria-label="Language mode">
            <button class="seg-btn active" id="langModeBilingual" onclick="setLanguageMode('bilingual')" title="双语研读模式（快捷键 T）">双语</button>
            <div class="seg-divider"></div>
            <button class="seg-btn" id="langModeEnglish" onclick="setLanguageMode('english')" title="纯英磨耳朵模式（快捷键 T）">纯英</button>
          </div>
          <button class="pill-btn" onclick="toggleTheme()" title="Switch theme (Sepia / Light / Dark / Night)">Theme</button>
        </div>
        <div class="drawer-group"{repeat_group_attr}>
          <div class="segmented-control">
            <select id="shadowRepeatSelect" class="seg-select" onchange="setShadowRepetitions(this.value)" title="Repetitions">
              <option value="1">1×</option><option value="3" selected>3×</option><option value="5">5×</option>
            </select>
            <div class="seg-divider"></div>
            <button class="seg-btn" id="repeatBtn" onclick="toggleShadowing()" title="Sentence repeat loop (快捷键 R)">Repeat</button>
          </div>
        </div>
        <div class="drawer-group">
          <label class="toggle-pill" title="Auto-scroll to active sentence">
            <input type="checkbox" id="autoScrollCheck" checked onchange="toggleAutoScroll(this.checked)">
            <span class="toggle-badge">Auto-scroll</span>
          </label>
          <button class="pill-btn" id="tipsToggleBtn" onclick="toggleTips()" title="Keyboard & Gesture shortcuts">Shortcuts</button>
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
            <div class="tips-row"><span class="kbd-key">Space</span><span>Toggle translation card (peek / hide)</span></div>
            <div class="tips-row"><span class="kbd-key">← / →</span><span>Previous / Next sentence (audio only)</span></div>
            <div class="tips-row"><span class="kbd-key">T</span><span>Toggle Bilingual / English-only mode</span></div>
            {f'<div class="tips-row"><span class="kbd-key">R</span><span>Repeat sentence loop</span></div>' if has_audio else ''}
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
            unmatched_tag = ""
            inspect_unmatched_notice = ""
            if has_match == 0 and has_audio:
                unmatched_tag = ' <span class="un-narrated-tag" title="有声书原版未录制音频">纯文本</span>'
                inspect_unmatched_notice = '<div class="inspect-audio-notice">（注：原版有声书未录制本句音频，已展开双语释义）</div>'
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
          <span class="s-content">{sentence_text_html}</span>{unmatched_tag}
        </div>
        <div class="inspect-panel" onclick="handleInspectPanelClick(event, '{sid}')">
          {inspect_unmatched_notice}
          <div class="inspect-trans">{trans}</div>
          {vocab_section}
        </div>
      </div>
"""

        editorial_notice = ch.get("editorial_notice")
        if editorial_notice:
            html_head += f"""
      <div class="editorial-notice-box">
        <span class="notice-icon">ℹ️</span>
        <div class="notice-content">
          <strong>编者注：</strong>{html.escape(editorial_notice)}
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
const audioSpeedBtn = document.getElementById('audioSpeedBtn');
const playerCurTime = document.getElementById('playerCurTime');
const playerTotalTime = document.getElementById('playerTotalTime');
const playerScrubber = document.getElementById('playerScrubber');
let isUserScrubbing = false;

const SPEED_PRESETS = [1.0, 1.25, 1.5, 1.75, 2.0, 0.75];
const SPEED_LABELS = { 1.0: '1.0×', 1.25: '1.25×', 1.5: '1.5×', 1.75: '1.75×', 2.0: '2.0×', 0.75: '0.75×' };
let currentPlaybackSpeed = parseFloat(localStorage.getItem(STORAGE_PREFIX + 'playback_speed') || '1.0');
if (!SPEED_PRESETS.includes(currentPlaybackSpeed)) currentPlaybackSpeed = 1.0;

function applyPlaybackRate(rate) {
  currentPlaybackSpeed = rate;
  localStorage.setItem(STORAGE_PREFIX + 'playback_speed', String(rate));
  if (audio) {
    audio.playbackRate = rate;
  }
  if (audioSpeedBtn) {
    audioSpeedBtn.textContent = SPEED_LABELS[rate] || (rate + '×');
    if (rate !== 1.0) {
      audioSpeedBtn.classList.add('custom-speed');
    } else {
      audioSpeedBtn.classList.remove('custom-speed');
    }
  }
}

function cyclePlaybackRate() {
  const curIdx = SPEED_PRESETS.indexOf(currentPlaybackSpeed);
  const nextRate = SPEED_PRESETS[(curIdx >= 0 ? curIdx + 1 : 0) % SPEED_PRESETS.length];
  applyPlaybackRate(nextRate);
}

function formatAudioTime(sec) {
  if (!Number.isFinite(sec) || sec < 0) return '00:00';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return (m < 10 ? '0' + m : m) + ':' + (s < 10 ? '0' + s : s);
}

function updateAudioPlayerUI() {
  if (!audio) return;
  if (audio.playbackRate !== currentPlaybackSpeed) {
    audio.playbackRate = currentPlaybackSpeed;
  }
  const cur = audio.currentTime || 0;
  const dur = audio.duration || 0;
  const pct = dur > 0 ? (cur / dur) * 100 : 0;
  if (!isUserScrubbing && playerScrubber) {
    playerScrubber.value = pct;
    playerScrubber.style.background = `linear-gradient(to right, var(--accent) 0%, var(--accent) ${pct}%, var(--border) ${pct}%, var(--border) 100%)`;
  }
  if (playerCurTime && !isUserScrubbing) {
    playerCurTime.textContent = formatAudioTime(cur);
  }
  if (playerTotalTime) {
    playerTotalTime.textContent = formatAudioTime(dur);
  }
}

if (playerScrubber) {
  playerScrubber.addEventListener('input', () => {
    isUserScrubbing = true;
    const pct = parseFloat(playerScrubber.value) || 0;
    playerScrubber.style.background = `linear-gradient(to right, var(--accent) 0%, var(--accent) ${pct}%, var(--border) ${pct}%, var(--border) 100%)`;
    if (audio && audio.duration) {
      const targetSec = (pct / 100) * audio.duration;
      if (playerCurTime) playerCurTime.textContent = formatAudioTime(targetSec);
    }
  });
  playerScrubber.addEventListener('change', () => {
    if (audio && audio.duration) {
      audio.currentTime = (parseFloat(playerScrubber.value) / 100) * audio.duration;
    }
    isUserScrubbing = false;
  });
}

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
  if (chNum > 2 && typeof window.PasskeyGate !== 'undefined' && !window.PasskeyGate.isUnlocked()) {
    if (audio && !audio.paused) audio.pause();
    if (typeof window.PasskeyGate.openModal === 'function') {
      window.PasskeyGate.openModal(chNum);
    }
    return;
  }
  activeChapterNum = chNum;
  localStorage.setItem(STORAGE_PREFIX + 'active_ch', chNum);
  
  const menuEl = document.getElementById('menu-ch-' + chNum);
  if (menuEl) {
    const tagText = menuEl.querySelector('.chapter-item-tag')?.textContent?.trim();
    currentChapterLabel.textContent = tagText ? tagText.replace(/^Chapter\s*/i, 'Ch. ') : (chNum === 0 ? 'Preface' : 'Ch. ' + chNum);
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
    drawerToggleBtn.innerHTML = 'Menu';
    localStorage.setItem(STORAGE_PREFIX + 'drawer_open', 'false');
  } else {
    controlDrawer.classList.add('open');
    drawerToggleBtn.innerHTML = 'Close';
    localStorage.setItem(STORAGE_PREFIX + 'drawer_open', 'true');
  }
}

const savedDrawerState = localStorage.getItem(STORAGE_PREFIX + 'drawer_open');
if (savedDrawerState === 'true') {
  controlDrawer.classList.add('open');
  drawerToggleBtn.innerHTML = 'Close';
}

const themes = ['sepia', 'light', 'dark', 'night'];

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

function setLanguageMode(mode) {
  const isEnglish = (mode === 'english');
  if (isEnglish) {
    document.documentElement.setAttribute('data-hide-chinese', 'true');
    document.querySelectorAll('.sentence-unit.active').forEach(u => u.classList.add('card-collapsed'));
  } else {
    document.documentElement.removeAttribute('data-hide-chinese');
  }
  localStorage.setItem(STORAGE_PREFIX + 'hide_chinese', String(isEnglish));
  localStorage.setItem('audible_hide_chinese', String(isEnglish));
  updateLanguageModeUI(mode);
}

function updateLanguageModeUI(mode) {
  const isEnglish = (mode === 'english');
  const btnBilingual = document.getElementById('langModeBilingual');
  const btnEnglish = document.getElementById('langModeEnglish');
  if (btnBilingual && btnEnglish) {
    if (isEnglish) {
      btnBilingual.classList.remove('active');
      btnEnglish.classList.add('active');
    } else {
      btnBilingual.classList.add('active');
      btnEnglish.classList.remove('active');
    }
  }
}

function toggleChineseLock() {
  const isEnglish = document.documentElement.getAttribute('data-hide-chinese') === 'true';
  setLanguageMode(isEnglish ? 'bilingual' : 'english');
}

window.setLanguageMode = setLanguageMode;
window.toggleChineseLock = toggleChineseLock;

const savedHideChinese = localStorage.getItem(STORAGE_PREFIX + 'hide_chinese') || localStorage.getItem('audible_hide_chinese');
if (savedHideChinese === 'true') {
  document.documentElement.setAttribute('data-hide-chinese', 'true');
  updateLanguageModeUI('english');
} else {
  updateLanguageModeUI('bilingual');
}

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

function showToast(msg) {
  let toast = document.getElementById('reader-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'reader-toast';
    document.body.appendChild(toast);
  }
  toast.textContent = msg;
  toast.classList.add('show');
  clearTimeout(toast.__timer);
  toast.__timer = setTimeout(() => {
    toast.classList.remove('show');
  }, 2200);
}

let lastSentenceClickTime = 0;
let lastSentenceClickId = null;

function startSentenceShadowing(sentenceEl) {
  if (!sentenceEl) return;
  if (sentenceEl.dataset.matched !== '1') {
    showToast('该句子无音频，无法跟读');
    return;
  }
  if (shadowState.timer) clearTimeout(shadowState.timer);
  shadowState.phase = 'playing';
  shadowState.completed = 0;
  shadowState.sentence = sentenceEl;
  const btn = document.getElementById('repeatBtn') || document.getElementById('shadowBtn');
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

  const isChineseLocked = document.documentElement.getAttribute('data-hide-chinese') === 'true';

  if (el.classList.contains('active') && !isDoubleTap) {{
    if (!el.classList.contains('card-collapsed')) {{
      el.classList.add('card-collapsed');
      return;
    }} else if (!isChineseLocked) {{
      el.classList.remove('card-collapsed');
      return;
    }} else {{
      el.classList.remove('active', 'card-collapsed');
      return;
    }}
  }}
  
  const isMatched = (hasMatch === undefined || hasMatch === null) ? (Number.isFinite(start) && Number.isFinite(end) && end > start && start >= 0) : Boolean(hasMatch);
  localStorage.setItem(STORAGE_PREFIX + 'last_sentence_c' + activeChapterNum, id);
  if (window.__HAS_AUDIO__ && isMatched && Number.isFinite(start) && Number.isFinite(end) && end > start) {{
    audio.currentTime = start;
    audio.play();
    globalPlayBtn.textContent = '⏸ Pause';
  }} else if (window.__HAS_AUDIO__ && (!isMatched || !Number.isFinite(start))) {{
    showToast('原版有声书未录制本句音频，已展开双语释义');
  }}

  document.querySelectorAll('.sentence-unit.active').forEach(u => {{
    if (u !== el) {{
      u.classList.remove('active', 'card-collapsed');
    }}
  }});

  el.classList.add('active');
  if (isChineseLocked) {{
    el.classList.add('card-collapsed');
  }} else {{
    el.classList.remove('card-collapsed');
  }}
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
  const btn = document.getElementById('repeatBtn') || document.getElementById('shadowBtn');
  if (btn) btn.textContent = 'Repeat';
}

function toggleShadowing() {
  if (shadowState.phase !== 'idle') {
    stopShadowing();
    return;
  }
  const activeSection = document.querySelector('.chapter-section.active');
  const sentence = findSentenceAt(audio.currentTime) || 
    (currentPlayingId ? document.getElementById(currentPlayingId) : null) || 
    (activeSection ? activeSection.querySelector('.sentence-unit.active') : null) || 
    (activeSection ? activeSection.querySelector('.sentence-unit') : null);
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

audio.addEventListener('play', () => {
  globalPlayBtn.textContent = '⏸ Pause';
  if (audio && audio.playbackRate !== currentPlaybackSpeed) {
    audio.playbackRate = currentPlaybackSpeed;
  }
  startSyncLoop();
});
audio.addEventListener('pause', () => {
  globalPlayBtn.textContent = '▶ Play';
  stopSyncLoop();
});
audio.addEventListener('timeupdate', () => {
  updateAudioPlayerUI();
  syncPlayback();
  if (!Number.isNaN(audio.currentTime) && audio.duration) {
    reportLibraryProgress(activeChapterNum, (audio.currentTime / audio.duration) * 100);
  }
});
audio.addEventListener('loadedmetadata', () => {
  if (audio) audio.playbackRate = currentPlaybackSpeed;
  updateAudioPlayerUI();
});
audio.addEventListener('durationchange', updateAudioPlayerUI);
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

// Desktop Keyboard Navigation (Arrow Keys, Spacebar, T, R)
window.addEventListener('keydown', (e) => {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
    return;
  }
  if (e.metaKey || e.ctrlKey || e.altKey) {
    return;
  }

  if (e.key === 't' || e.key === 'T' || e.code === 'KeyT') {
    e.preventDefault();
    toggleChineseLock();
    return;
  }

  if (e.key === 'r' || e.key === 'R' || e.code === 'KeyR') {
    e.preventDefault();
    if (window.__HAS_AUDIO__) {
      toggleShadowing();
    }
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
      if (activeUnit) activeUnit.classList.remove('active', 'card-collapsed');
      targetUnit.classList.add('active', 'card-collapsed');
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
      if (activeUnit) activeUnit.classList.remove('active', 'card-collapsed');
      targetUnit.classList.add('active', 'card-collapsed');
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
      const isChineseLocked = document.documentElement.getAttribute('data-hide-chinese') === 'true';
      if (!isChineseLocked) {
        if (currentUnit.classList.contains('card-collapsed')) {
          currentUnit.classList.remove('card-collapsed');
        } else if (currentUnit.classList.contains('active')) {
          currentUnit.classList.add('card-collapsed');
        } else {
          currentUnit.classList.add('active');
          currentUnit.classList.remove('card-collapsed');
        }
      } else {
        toggleGlobalPlay();
      }
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
