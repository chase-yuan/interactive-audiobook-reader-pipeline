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
from reader_theme import get_reader_css
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
            'aligned_json': c.get('aligned_json'),
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
    
    clean_short_title = re.sub(r'[\(\[]\s*(?:unabridged|audiobook|edition|anniversary|deluxe|version)\s*[\)\]]', '', book_title, flags=re.I).strip()
    for sep in [':', ' - ', ' — ', ' – ']:
        if sep in clean_short_title:
            cand = clean_short_title.split(sep)[0].strip()
            if len(cand) >= 3:
                clean_short_title = cand
                break
    if len(clean_short_title) > 16:
        for word_sep in [" Things That ", " How to ", " The Story of ", " Why "]:
            if word_sep.lower() in clean_short_title.lower():
                clean_short_title = re.split(word_sep, clean_short_title, flags=re.IGNORECASE)[0].strip()
                break
    if len(clean_short_title) > 22 and ' ' in clean_short_title:
        words = clean_short_title.split()
        if len(words) >= 2 and len(" ".join(words[:2])) <= 22:
            clean_short_title = " ".join(words[:2])
        elif len(words) > 0:
            clean_short_title = words[0]

    html_head = f"""<!DOCTYPE html>
<html lang="en" data-theme="sepia">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<meta name="reader-release-report-sha256" content="{html.escape(report_sha256)}">
<meta name="reader-build-kind" content="{'experimental-preview' if preview else 'release'}">
<title>{html.escape(('EXPERIMENTAL PREVIEW — ' if preview else '') + book_title)}: {html.escape(book_subtitle)}</title>
<link rel="preconnect" href="https://audio.audiblelibrary.online" crossorigin>
<link rel="dns-prefetch" href="https://audio.audiblelibrary.online">
<script>
(function() {{
  try {{
    var bId = {json.dumps(book_id)};
    var t = localStorage.getItem('audible_theme') || localStorage.getItem('audible_reader_theme') || localStorage.getItem('reader_' + bId + '_theme') || localStorage.getItem(bId + '_theme');
    if (t && (t === 'sepia' || t === 'light' || t === 'dark' || t === 'night')) {{
      document.documentElement.setAttribute('data-theme', t);
    }}
    var hideCh = localStorage.getItem('reader_' + bId + '_hide_chinese') || localStorage.getItem('audible_hide_chinese');
    if (hideCh === 'true') {{
      document.documentElement.setAttribute('data-hide-chinese', 'true');
    }}
  }} catch (e) {{}}
}})();
</script>
<style>
{get_reader_css()}
</style>
</head>
<body onclick="closeDropdowns(event)">

<header class="top-nav">
  <div class="nav-bar">
    <div class="chapter-nav-wrapper">
      <button class="chapter-btn" id="chapterSelectBtn" onclick="toggleChapterDropdown(event)">
        <span><span id="currentChapterLabel">{html.escape(first_ch_label)}</span> · <span class="book-pill-title">{html.escape(clean_short_title)}</span></span>
        <span class="dropdown-arrow">▾</span>
      </button>
      <div class="chapter-dropdown" id="chapterDropdown">
"""

    for ch in loaded_chapters:
        cnum = ch["num"]
        ctitle = ch["title"]
        label = html.escape(ch["label"])
        active_cls = " active" if cnum == first_ch_num else ""
        html_head += f"""        <div class="chapter-item{active_cls}" id="menu-ch-{cnum}" onclick="switchChapter({cnum})">
          <span class="chapter-item-tag">{label}</span>
          <span>{html.escape(ctitle)}</span>
        </div>\n"""

    html_head += f"""      </div>
    </div>
  </div>
</header>

<main class="reader-main">
"""

    for ch in loaded_chapters:
        cnum = ch["num"]
        ctitle = ch["title"]
        caudio = ch["audio"]
        cpublic_audio = ch.get("public_audio") or ""
        csents = ch["sentences"]
        active_cls = " active" if cnum == first_ch_num else ""
        ch_heading_label = ch["label"].upper()
        safe_heading_label = html.escape(ch_heading_label)
        clean_title = ctitle.strip()
        disp_num = str(ch.get("display_number")) if ch.get("display_number") is not None else ""
        disp_part = rf"|\b(?:Chapter\s+)?{re.escape(disp_num)}(?!\d)\s*[\.\:—–-]\s*" if disp_num else ""
        prefix_pattern = rf"^(?:{re.escape(ch['label'])}\s*[:—–-]?\s*{disp_part})"
        sub_title = re.sub(prefix_pattern, "", clean_title, flags=re.IGNORECASE).strip()
        if not sub_title or len(sub_title) <= 2 or clean_title.upper() == ch_heading_label or clean_title.upper() == f"CHAPTER {cnum}":
            title_html = safe_heading_label
        elif safe_heading_label in clean_title.upper() and len(sub_title) < 4:
            title_html = html.escape(clean_title.upper())
        else:
            title_html = f"{safe_heading_label}<br>{html.escape(sub_title)}"
        
        html_head += f"""
  <!-- CHAPTER {cnum} -->
  <section class="chapter-section{active_cls}" id="chapter-{cnum}" data-audio="{html.escape(caudio)}" data-public-audio="{html.escape(cpublic_audio)}" data-ch="{cnum}">
    <div class="chapter-layout">
      <div class="prose-column">
        <header class="book-header">
          <h1 class="book-title">{title_html}</h1>
          <div class="book-author">{html.escape(book_author)}</div>
        </header>

        <div class="book-content">
"""
        if has_audio and csents:
            def is_sentence_explicitly_estimated(sent):
                if sent.get("timing_source") == "estimated":
                    return True
                return any(w.get("timing_source") == "estimated" for w in sent.get("word_spans", []))

            valid_flags = []
            # Resolve canonical metadata if available to preserve EPUB paragraph structure and heading hierarchy
        canonical_path = ch.get('aligned_json', '').replace('_aligned_sentences.json', '_canonical_sentences.json')
        canonical_map = {}
        canonical_headings = set()
        if os.path.exists(canonical_path):
            try:
                with open(canonical_path, 'r', encoding='utf-8') as cf:
                    for item in json.load(cf):
                        if 'id' in item:
                            if 'elem_idx' in item:
                                canonical_map[item['id']] = item['elem_idx']
                            if item.get('is_heading'):
                                canonical_headings.add(item['id'])
            except Exception:
                pass

        prose_blocks = []
        current_p_units = []
        current_elem_idx = None

        for s in csents:
            if s.get("text", "").strip() in ['* * *', '***', '---', '* * * *', '– – –', '— — —', '… … …', '• • •']:
                if current_p_units:
                    prose_blocks.append(f'        <p class="prose-p">{" ".join(current_p_units)}</p>')
                    current_p_units = []
                    current_elem_idx = None
                div_symbol = html.escape(s.get("text", "").strip())
                prose_blocks.append(f'        <div class="scene-divider" aria-hidden="true"><span>{div_symbol}</span></div>')
                continue

            raw_sid = s["id"]
            sid = f"c{cnum}-{raw_sid}"
            is_h = bool(s.get("is_heading")) or (raw_sid in canonical_headings)
            start = s.get("audio_start", s.get("start"))
            end = s.get("audio_end", s.get("end"))
            word_spans = s.get("word_spans", [])
            spans_are_observed = all(w.get("timing_source", "observed") in ("observed", "interpolated") for w in word_spans)
            has_match = 1 if s.get("has_audio_match", True) and spans_are_observed and isinstance(start, (int, float)) and isinstance(end, (int, float)) and end >= start else 0
            unmatched_tag = ""
            inspect_unmatched_notice = ""
            start_arg = "null" if start is None else str(start)
            end_arg = "null" if end is None else str(end)
            raw_trans = s.get("trans", "") or ""
            vocab = s.get("vocab", [])
            raw_text = s.get("text", "")
            
            word_html_list = []
            if word_spans:
                for w in word_spans:
                    rw = html.escape(w["word"])
                    ws = w.get("start")
                    we = w.get("end")
                    timing_source = html.escape(w.get("timing_source", "observed"))
                    ts_attr = f' data-timing-source="{timing_source}"' if timing_source and timing_source != "observed" else ""
                    if isinstance(ws, (int, float)) and isinstance(we, (int, float)):
                        word_html_list.append(f'<span class="w" data-s="{ws}" data-e="{we}"{ts_attr}>{rw}</span>')
                    else:
                        word_html_list.append(f'<span class="w"{ts_attr}>{rw}</span>')
            else:
                c_cnt = max(1, len(s["text"].split()))
                prev_w_s = -1.0
                for m_i, rw in enumerate(s["text"].split()):
                    if isinstance(start, (int, float)) and isinstance(end, (int, float)):
                        ws = round(start + (end - start) * (m_i / c_cnt), 2)
                        we = round(start + (end - start) * ((m_i + 1) / c_cnt), 2)
                        if ws <= prev_w_s:
                            ws = round(prev_w_s + 0.01, 2)
                        if we <= ws:
                            we = round(ws + 0.01, 2)
                        prev_w_s = ws
                        word_html_list.append(f'<span class="w" data-s="{ws}" data-e="{we}">{html.escape(rw)}</span>')
                    else:
                        word_html_list.append(f'<span class="w">{html.escape(rw)}</span>')
            
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
            is_intext_heading = bool(re.match(r"^CHAPTER\s+(ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE|TEN|ELEVEN|TWELVE|THIRTEEN|FOURTEEN|FIFTEEN|SIXTEEN|SEVENTEEN|EIGHTEEN|NINETEEN|TWENTY|[A-Z\-]+|\d+)\s*$", raw_text.strip(), re.IGNORECASE))
            if not is_h and not is_intext_heading:
                rt_s = raw_text.strip()
                if (
                    rt_s.lower() in {"introduction", "acknowledgments", "conclusion", "foreword", "preface", "epilogue", "prologue", "afterword"}
                    or rt_s.startswith("for ")
                    or bool(re.match(r"^\d{4}[\-–—](\d{2,4}|now)$", rt_s, re.I))
                    or bool(re.match(r"^\s*by\s+[A-Z]", rt_s))
                    or (rt_s.isupper() and len(rt_s.split()) <= 4)
                    or rt_s in {
                        "Light", "Temperature", "Meal times", "Exercise", "Foundational", "Behavioral", "Pharmacological",
                        "Animal-Based", "Design", "Marketing", "Sales", "Legal", "The Manhattan Project", "Vaccines", "Antibiotics"
                    }
                ):
                    is_intext_heading = True
            is_citation = raw_text.strip().startswith(("—", "–", "--", "- "))

            if is_h:
                h_class += " chapter-heading-1"
            elif is_intext_heading:
                h_class += " chapter-intext-heading"
            elif is_citation:
                h_class += " epigraph-citation"

            is_reorder = 1 if s.get("alignment_method") in {
                "leading_epigraph_attribution",
                "chapter_heading_numeric_variant",
                "opening_speaker_attribution",
                "dialogue_attribution_reorder",
            } else 0
            reorder_attr = ' data-reorder="1"' if is_reorder else ''
            trans_attr = f' data-trans="{html.escape(raw_trans, quote=True)}"' if raw_trans else ''
            vocab_attr = f' data-vocab="{html.escape(json.dumps(vocab, ensure_ascii=False))}"' if vocab else ''

            s_audio_order = s.get("audio_order", "")
            s_epigraph = 1 if s.get("alignment_method") == "leading_epigraph_attribution" else 0
            click_call = f"handleSentenceClick(event, '{sid}', {start_arg}, {end_arg}, {has_match})"

            unit_markup = (
                f'<span class="sentence-unit s-inline" id="{sid}" data-start="{start_arg}" data-end="{end_arg}" '
                f'data-audio-order="{s_audio_order}" data-epigraph="{s_epigraph}"{reorder_attr} '
                f'data-matched="{has_match}"{trans_attr}{vocab_attr}>'
                f'<span class="sentence-text{h_class}" onclick="{click_call}">'
                f'<span class="s-content">{sentence_text_html}</span>{unmatched_tag}</span>'
                f'</span>'
            )

            is_standalone_block = is_h or is_intext_heading or is_citation

            if is_standalone_block:
                if current_p_units:
                    prose_blocks.append(f'        <p class="prose-p">{" ".join(current_p_units)}</p>')
                    current_p_units = []
                    current_elem_idx = None
                block_cls = "prose-heading-block" if (is_h or is_intext_heading) else "prose-epigraph-block"
                prose_blocks.append(f'        <div class="{block_cls}">{unit_markup}</div>')
                continue

            elem_idx = s.get("elem_idx")
            if elem_idx is None and raw_sid in canonical_map:
                elem_idx = canonical_map[raw_sid]

            if elem_idx is not None:
                if current_p_units and current_elem_idx != elem_idx:
                    prose_blocks.append(f'        <p class="prose-p">{" ".join(current_p_units)}</p>')
                    current_p_units = []
                current_p_units.append(unit_markup)
                current_elem_idx = elem_idx
            else:
                current_p_units.append(unit_markup)
                prose_blocks.append(f'        <p class="prose-p">{" ".join(current_p_units)}</p>')
                current_p_units = []
                current_elem_idx = None

        if current_p_units:
            prose_blocks.append(f'        <p class="prose-p">{" ".join(current_p_units)}</p>')

        html_head += "\n".join(prose_blocks) + "\n"

        editorial_notice = ch.get("editorial_notice")
        if editorial_notice:
            html_head += f"""
        <div class="editorial-notice-box">
          <span class="notice-badge">Editor's Note</span>
          <div class="notice-content">
            {html.escape(editorial_notice)}
          </div>
        </div>
"""

        html_head += f"""      </div>
      </div>
    </div>
  </section>
"""

    book_id_json = json.dumps(book_id)
    html_tail = f"""
  <div class="marginalia-backdrop" id="marginaliaBackdrop" onclick="hideMarginalia(event)" aria-hidden="true"></div>
  <aside class="marginalia-note" id="marginaliaNote" aria-live="polite">
    <div class="marginalia-header">
      <div class="marginalia-drag-pill" onclick="hideMarginalia(event)" aria-label="Dismiss"></div>
    </div>
    <div class="marginalia-content" id="marginaliaContent">
      <div class="marginalia-trans" id="marginaliaTrans"></div>
      <div class="marginalia-vocab" id="marginaliaVocab"></div>
    </div>
  </aside>
</main>

<nav class="bottom-control-dock{' text-only-dock' if not has_audio else ''}" id="bottomControlDock" aria-label="Reader dock">
  <div class="dock-primary-row">
    <button class="dock-play-btn" id="globalPlayBtn" onclick="toggleGlobalPlay()"{play_btn_attr}>▶ Play</button>
    <button class="dock-chip" id="repeatBtn" onclick="cycleMainRepeat()" aria-label="Sentence repeat loop (Shortcut: R)"{repeat_group_attr}><svg class="dock-rep-icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/></svg></button>
    <button class="dock-chip" id="audioSpeedBtn" onclick="cyclePlaybackRate()" aria-label="Playback speed"{audio_track_attr}>1.0×</button>
    <div class="dock-scrubber-wrap"{audio_track_attr}>
      <span class="dock-time" id="playerCurTime">00:00</span>
      <input type="range" class="player-slider" id="playerScrubber" min="0" max="100" value="0" step="0.1" aria-label="Playback scrubber">
      <span class="dock-time" id="playerTotalTime">00:00</span>
    </div>
    <button class="dock-chip" id="drawerToggleBtn" onclick="toggleDrawer(event)" aria-label="Preferences">Menu</button>
  </div>

  <div class="dock-expanded-content control-drawer" id="controlDrawer" onclick="event.stopPropagation()">
    <div class="dock-hairline"></div>
    <div class="dock-expanded-grid">
      <div class="dock-sub-row dock-row-modes">
        <div class="dock-chip-group">
          <button class="pill-btn active" id="chineseLockBtn" onclick="toggleChineseLock()" aria-label="Language mode (Shortcut: T)">Dual</button>
          <button class="dock-chip" id="focusModeBtn" onclick="toggleFocusMode()" aria-label="Focus mode (Shortcut: P)"{repeat_group_attr}>Focus</button>
        </div>
        <label class="toggle-pill" aria-label="Auto-scroll to active sentence">
          <input type="checkbox" id="autoScrollCheck" checked onchange="toggleAutoScroll(this.checked)">
          <span class="toggle-badge">Auto</span>
        </label>
      </div>
      <div class="dock-sub-hairline"></div>
      <div class="dock-sub-row dock-row-theme">
        <div class="dock-theme-group">
          <div class="theme-swatches">
            <button class="theme-dot theme-dot-sepia active" onclick="setTheme('sepia')" aria-label="Sepia"></button>
            <button class="theme-dot theme-dot-light" onclick="setTheme('light')" aria-label="Light"></button>
            <button class="theme-dot theme-dot-dark" onclick="setTheme('dark')" aria-label="Dark"></button>
            <button class="theme-dot theme-dot-night" onclick="setTheme('night')" aria-label="Night"></button>
          </div>
          <button class="dock-text-link" id="tipsToggleBtn" onclick="toggleTips()" aria-label="Keyboard & Gesture shortcuts">Shortcuts</button>
        </div>
      </div>
    </div>
  </div>
  <audio id="audioTrack" playsinline webkit-playsinline preload="auto" src="{html.escape(audio_src)}" class="hidden-audio"{audio_track_attr}></audio>
</nav>

<!-- Shortcuts Centered Raycast Modal -->
<div class="shortcuts-modal-overlay" id="drawerTips" onclick="toggleTips()">
  <div class="shortcuts-modal" onclick="event.stopPropagation()">
    <div class="shortcuts-modal-header">
      <span class="shortcuts-modal-title">Shortcuts</span>
      <button class="shortcuts-modal-close" onclick="toggleTips()" aria-label="Close shortcuts">✕</button>
    </div>
    <div class="shortcuts-table">
      <div class="shortcut-item"><span class="kbd-key">Space</span><span>Play / Pause</span></div>
      <div class="shortcut-item"><span class="kbd-key">← / →</span><span>Previous / Next sentence</span></div>
      <div class="shortcut-item"><span class="kbd-key">[ / ]</span><span>Previous / Next chapter</span></div>
      <div class="shortcut-item"><span class="kbd-key">T</span><span>Toggle Bilingual / English-only mode</span></div>
      <div class="shortcut-item"><span class="kbd-key">R</span><span>Repeat sentence loop</span></div>
      <div class="shortcut-item"><span class="kbd-key">P</span><span>Focus Mode (Immersion)</span></div>
      <div class="shortcut-item"><span class="kbd-key">H / B</span><span>Audio mode (hide text for listening)</span></div>
      <div class="shortcut-item"><span class="kbd-key">Esc</span><span>Dismiss popover / modal</span></div>
    </div>
  </div>
</div>

<div id="focus-overlay" class="focus-overlay pocket-overlay" onclick="handleFocusOverlayClick(event)" ondblclick="handleFocusDblClick(event)" ontouchstart="handleFocusTouchStart(event)" ontouchend="handleFocusTouchEnd(event)">
  <div class="focus-top-bar pocket-header">
    <button class="focus-close-icon pocket-close-icon" id="focusExitBtn" onclick="toggleFocusMode(false)">✕</button>
  </div>
  <div class="focus-sentence-container pocket-sentence-container" id="focusSentenceContainer" onclick="handleFocusSentenceBoxClick(event)">
    <div class="focus-sentence-box pocket-sentence-box" id="focusSentenceBox">
      <div class="focus-sentence-text pocket-sentence-text" id="focusSentenceText"></div>
      <div class="focus-sentence-trans pocket-sentence-trans" id="focusSentenceTrans"></div>
      <div class="focus-sentence-vocab" id="focusSentenceVocab"></div>
    </div>
  </div>
  <div class="focus-dock" id="focusDock">
    <button class="focus-dock-btn" id="focusPrevBtn" onclick="gotoPreviousShadowSentence(event)">◀</button>
    <button class="focus-dock-btn focus-dock-play" id="focusPlayBtn" onclick="toggleFocusPlayPause(event)">⏸</button>
    <button class="focus-dock-btn focus-rep-pill" id="focusRepBtn" onclick="cycleFocusRepetitions(event)">1×</button>
    <button class="focus-dock-btn active" id="focusTransBtn" onclick="toggleFocusTransMode(event)">Dual</button>
    <button class="focus-dock-btn" id="focusBlindBtn" onclick="toggleFocusBlindMode(event)">Audio</button>
    <button class="focus-dock-btn" id="focusFontBtn" onclick="cycleFocusFontSize(event)">A+</button>
    <button class="focus-dock-btn" id="focusNextBtn" onclick="gotoNextShadowSentence(event)">▶</button>
  </div>
</div>

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
let focusModeActive = false;
let pocketModeActive = false;
let isUserSeeking = false;
let targetSeekTime = -1;
let seekWatchdogTimer = null;
let audioRecoveryRetries = 0;
const MAX_AUDIO_RETRIES = 3;
let lastClickedSentenceId = null;
let lastSentenceClickId = null;
let lastSentenceClickTime = 0;

function setUserSeeking(active, targetTime) {
  isUserSeeking = active;
  if (active) {
    targetSeekTime = (typeof targetTime === 'number' && Number.isFinite(targetTime)) ? targetTime : -1;
    if (seekWatchdogTimer) clearTimeout(seekWatchdogTimer);
    seekWatchdogTimer = setTimeout(() => {
      isUserSeeking = false;
      targetSeekTime = -1;
    }, 1000);
  } else {
    if (seekWatchdogTimer) {
      clearTimeout(seekWatchdogTimer);
      seekWatchdogTimer = null;
    }
    targetSeekTime = -1;
  }
}

function safePlay(audioEl) {
  if (!audioEl) return;
  audioRecoveryRetries = 0;
  const p = audioEl.play();
  if (p && typeof p.catch === 'function') {
    p.catch(function(err) {
      if (err && err.name !== 'AbortError') {
        console.warn('[Audio] play error:', err);
      }
    });
  }
}

const SPEED_PRESETS = [1.0, 1.25, 1.5, 2.0];
const SPEED_LABELS = { 1.0: '1.0×', 1.25: '1.25×', 1.5: '1.5×', 2.0: '2.0×' };
let currentPlaybackSpeed = parseFloat(localStorage.getItem(STORAGE_PREFIX + 'playback_speed') || '1.0');
if (!Number.isFinite(currentPlaybackSpeed) || currentPlaybackSpeed <= 0) currentPlaybackSpeed = 1.0;

function applyPlaybackRate(rate) {
  const cleanRate = Math.round(rate * 100) / 100;
  currentPlaybackSpeed = cleanRate;
  try {
    localStorage.setItem(STORAGE_PREFIX + 'playback_speed', String(cleanRate));
  } catch(e) {}
  if (audio && Math.abs(audio.playbackRate - cleanRate) >= 0.01) {
    audio.playbackRate = cleanRate;
  }
  if (audioSpeedBtn) {
    const label = SPEED_LABELS[cleanRate] || ((cleanRate % 1 === 0 ? cleanRate.toFixed(1) : String(cleanRate)) + '×');
    audioSpeedBtn.textContent = label;
    if (Math.abs(cleanRate - 1.0) >= 0.01) {
      audioSpeedBtn.classList.add('custom-speed');
    } else {
      audioSpeedBtn.classList.remove('custom-speed');
    }
  }
}

// Synchronize UI and audio rate with stored preference immediately on startup
applyPlaybackRate(currentPlaybackSpeed);

function cyclePlaybackRate() {
  const curIdx = SPEED_PRESETS.findIndex(r => Math.abs(r - currentPlaybackSpeed) < 0.01);
  let nextRate;
  if (curIdx >= 0) {
    nextRate = SPEED_PRESETS[(curIdx + 1) % SPEED_PRESETS.length];
  } else {
    // If extension set custom speed (e.g. 2.5x, 3.0x, 0.75x):
    // Stepping moves to next preset above it, or loops to 1.0 if >= 2.0
    const nextHigherIdx = SPEED_PRESETS.findIndex(r => r > currentPlaybackSpeed + 0.05);
    nextRate = nextHigherIdx >= 0 ? SPEED_PRESETS[nextHigherIdx] : SPEED_PRESETS[0];
  }
  applyPlaybackRate(nextRate);
  scheduleMainDockHide();
}

function formatAudioTime(sec) {
  if (!Number.isFinite(sec) || sec < 0) return '00:00';
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return (m < 10 ? '0' + m : m) + ':' + (s < 10 ? '0' + s : s);
}

let lastMediaSessionPositionUpdate = 0;
let lastScrubberRenderPct = -1;

function updateAudioPlayerUI() {
  if (!audio) return;
  const cur = audio.currentTime || 0;
  const dur = audio.duration || 0;
  const pct = dur > 0 ? (cur / dur) * 100 : 0;
  if (!isUserScrubbing && playerScrubber) {
    playerScrubber.value = pct;
    if (Math.abs(pct - lastScrubberRenderPct) >= 0.25 || pct === 0 || pct === 100) {
      lastScrubberRenderPct = pct;
      playerScrubber.style.background = `linear-gradient(to right, var(--accent) 0%, var(--accent) ${pct}%, var(--border) ${pct}%, var(--border) 100%)`;
    }
  }
  if (playerCurTime && !isUserScrubbing) {
    playerCurTime.textContent = formatAudioTime(cur);
  }
  if (playerTotalTime) {
    playerTotalTime.textContent = formatAudioTime(dur);
  }
  if ('mediaSession' in navigator && 'setPositionState' in navigator.mediaSession) {
    const now = Date.now();
    if (now - lastMediaSessionPositionUpdate >= 2500 && Number.isFinite(dur) && dur > 0 && Number.isFinite(cur) && cur >= 0) {
      try {
        lastMediaSessionPositionUpdate = now;
        navigator.mediaSession.setPositionState({
          duration: Math.max(0, dur),
          playbackRate: Number.isFinite(audio.playbackRate) && audio.playbackRate > 0 ? audio.playbackRate : 1,
          position: Math.min(Math.max(0, cur), dur)
        });
      } catch(e) {}
    }
  }
}

if (playerScrubber) {
  function commitScrubberChange() {
    if (audio && Number.isFinite(audio.duration) && audio.duration > 0) {
      try {
        audio.currentTime = (parseFloat(playerScrubber.value) / 100) * audio.duration;
      } catch(e) {}
    }
    isUserScrubbing = false;
    scheduleMainDockHide();
  }

  playerScrubber.addEventListener('input', () => {
    isUserScrubbing = true;
    if (dockIdleTimer) {
      clearTimeout(dockIdleTimer);
      dockIdleTimer = null;
    }
    const pct = parseFloat(playerScrubber.value) || 0;
    playerScrubber.style.background = `linear-gradient(to right, var(--accent) 0%, var(--accent) ${pct}%, var(--border) ${pct}%, var(--border) 100%)`;
    if (audio && Number.isFinite(audio.duration) && audio.duration > 0) {
      const targetSec = (pct / 100) * audio.duration;
      if (playerCurTime) playerCurTime.textContent = formatAudioTime(targetSec);
    }
  });
  playerScrubber.addEventListener('change', commitScrubberChange);
  playerScrubber.addEventListener('touchend', commitScrubberChange, { passive: true });
  playerScrubber.addEventListener('touchcancel', () => {
    isUserScrubbing = false;
    scheduleMainDockHide();
  }, { passive: true });
  playerScrubber.addEventListener('pointerup', commitScrubberChange);
  window.addEventListener('pointerup', () => {
    if (isUserScrubbing) {
      commitScrubberChange();
    }
  });
  window.addEventListener('touchend', () => {
    if (isUserScrubbing) {
      commitScrubberChange();
    }
  }, { passive: true });
}

let isProgrammaticAutoScroll = false;
let programmaticScrollTimer = null;
let isKeyboardNavigating = false;
let keyboardNavTimer = null;

function setKeyboardNavigating() {
  isKeyboardNavigating = true;
  if (keyboardNavTimer) clearTimeout(keyboardNavTimer);
  keyboardNavTimer = setTimeout(() => {
    isKeyboardNavigating = false;
  }, 1200);
}

function performAutoScroll(element) {
  if (!element || typeof element.scrollIntoView !== 'function') return;
  isProgrammaticAutoScroll = true;
  if (programmaticScrollTimer) clearTimeout(programmaticScrollTimer);
  programmaticScrollTimer = setTimeout(() => {
    isProgrammaticAutoScroll = false;
  }, 1200);
  element.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

let dockIdleTimer = null;
const DOCK_IDLE_DELAY = 3500;
const DOCK_SILENT_IDLE_DELAY = 4500;

function scheduleMainDockHide() {
  if (dockIdleTimer) {
    clearTimeout(dockIdleTimer);
    dockIdleTimer = null;
  }
  const dock = document.getElementById('bottomControlDock');
  if (!dock || dock.classList.contains('expanded')) return;
  if (typeof controlDrawer !== 'undefined' && controlDrawer && controlDrawer.classList.contains('open')) return;
  if (isUserScrubbing) return;
  if (dock._isMouseOver) return;

  const isAudioActive = audio && (!audio.paused || shadowState.isInternalPause);
  const delay = isAudioActive ? DOCK_IDLE_DELAY : DOCK_SILENT_IDLE_DELAY;

  dockIdleTimer = setTimeout(() => {
    const d = document.getElementById('bottomControlDock');
    if (!d || d.classList.contains('expanded') || isUserScrubbing || d._isMouseOver) return;
    if (typeof controlDrawer !== 'undefined' && controlDrawer && controlDrawer.classList.contains('open')) return;
    d.classList.add('dock-idle-hidden');
  }, delay);
}

function showMainDock() {
  if (focusModeActive || pocketModeActive || isKeyboardNavigating) return;
  const dock = document.getElementById('bottomControlDock');
  if (!dock) return;
  dock.classList.remove('dock-idle-hidden');
  scheduleMainDockHide();
}

function onUserDockActivity() {
  const e = arguments[0];
  if (focusModeActive || pocketModeActive || isKeyboardNavigating) return;
  if (isProgrammaticAutoScroll) return;
  
  if (e) {
    if (e.type === 'scroll') {
      // AP5 Ergonomic Flow: Natural reading page scroll must NEVER pop open player dock
      return;
    }
    if (e.type === 'pointermove') {
      // Reveal dock only when pointer enters the bottom activation strip (bottom 72px) or is over the dock
      const dock = document.getElementById('bottomControlDock');
      const isNearBottom = (typeof e.clientY === 'number') ? (e.clientY >= window.innerHeight - 72) : false;
      if (!isNearBottom && !(dock && dock._isMouseOver)) {
        return;
      }
    }
    if (e.type === 'pointerdown' || e.type === 'touchstart') {
      isProgrammaticAutoScroll = false;
      const dock = document.getElementById('bottomControlDock');
      const clientY = (e.touches && e.touches.length > 0) ? e.touches[0].clientY : e.clientY;
      const isNearBottom = (typeof clientY === 'number') ? (clientY >= window.innerHeight - 72) : false;
      const isTargetOnDock = Boolean(dock && e.target && dock.contains(e.target));
      if (!isNearBottom && !isTargetOnDock) {
        return;
      }
    }
  }
  showMainDock();
}

let activeChapterNum = parseInt(localStorage.getItem(STORAGE_PREFIX + 'active_ch') || String(window.__INITIAL_CHAPTER__), 10);
let autoScrollEnabled = localStorage.getItem(STORAGE_PREFIX + 'autoscroll') !== 'false';
let currentPlayingId = null;
let currentActiveWordEl = null;
let currentActiveWordStart = -1;
let currentActiveWordEnd = -1;

function clearActiveWord() {
  if (currentActiveWordEl) {
    currentActiveWordEl.classList.remove('active-word');
    currentActiveWordEl = null;
  }
  const orphans = document.querySelectorAll('.w.active-word');
  for (let i = 0; i < orphans.length; i++) {
    orphans[i].classList.remove('active-word');
  }
  currentActiveWordStart = -1;
  currentActiveWordEnd = -1;
}

function setActiveWord(wordEl, start, end, wordIndex) {
  if (currentActiveWordEl === wordEl && wordEl && wordEl.classList.contains('active-word')) {
    return;
  }
  clearActiveWord();
  if (wordEl) {
    wordEl.classList.add('active-word');
    currentActiveWordEl = wordEl;
    currentActiveWordStart = Number.isFinite(start) ? start : (parseFloat(wordEl.dataset.s) || -1);
    currentActiveWordEnd = Number.isFinite(end) ? end : (parseFloat(wordEl.dataset.e) || -1);
    
    if (focusModeActive || pocketModeActive) {
      const pText = document.getElementById('focusSentenceText') || document.getElementById('pocketSentenceText');
      if (pText) {
        if (!pText._cachedFocusWords) {
          pText._cachedFocusWords = Array.from(pText.querySelectorAll('.w'));
        }
        const idx = Number.isFinite(wordIndex) && wordIndex >= 0 ? wordIndex : (wordEl.parentElement ? Array.from(wordEl.parentElement.querySelectorAll('.w')).indexOf(wordEl) : -1);
        if (idx >= 0 && idx < pText._cachedFocusWords.length) {
          pText._cachedFocusWords[idx].classList.add('active-word');
        }
      }
    }
  }
}
let currentActiveSection = null;
let sentenceTimeIndex = [];
let syncFrameId = null;
const shadowState = { phase: 'idle', repetitions: 1, completed: 0, sentence: null, timer: null, pauseStartTime: 0 };

let shadowWakeLock = null;
async function requestShadowWakeLock() {
  if (shadowState.phase === 'idle') return;
  try {
    if ('wakeLock' in navigator && (!shadowWakeLock || shadowWakeLock.released)) {
      shadowWakeLock = await navigator.wakeLock.request('screen');
      shadowWakeLock.addEventListener('release', () => { shadowWakeLock = null; });
    }
  } catch(e) {}
}

function releaseShadowWakeLock() {
  if (shadowWakeLock) {
    try { shadowWakeLock.release(); } catch(e) {}
    shadowWakeLock = null;
  }
}

const scrollBtn = document.getElementById('autoScrollBtn');
if (scrollBtn) scrollBtn.classList.toggle('active', autoScrollEnabled);
const scrollCheck = document.getElementById('autoScrollCheck');
if (scrollCheck) scrollCheck.checked = autoScrollEnabled;

function toggleAutoScroll(enabled) {
  autoScrollEnabled = enabled;
  localStorage.setItem(STORAGE_PREFIX + 'autoscroll', enabled ? 'true' : 'false');
  const btn = document.getElementById('autoScrollBtn');
  if (btn) btn.classList.toggle('active', enabled);
  const chk = document.getElementById('autoScrollCheck');
  if (chk) chk.checked = enabled;
  scheduleMainDockHide();
}

function toggleAutoScrollPill(btn) {
  toggleAutoScroll(!autoScrollEnabled);
}
window.toggleAutoScrollPill = toggleAutoScrollPill;

// Chapter Switching
function toggleChapterDropdown(event) {
  if (event && event.stopPropagation) event.stopPropagation();
  hideMarginalia();
  if (controlDrawer) controlDrawer.classList.remove('open');
  const dock = document.getElementById('bottomControlDock');
  if (dock) dock.classList.remove('expanded');
  if (drawerToggleBtn) {
    drawerToggleBtn.innerHTML = 'Menu';
    drawerToggleBtn.classList.remove('active');
  }
  chapterDropdown.classList.toggle('open');
}

function closeDropdowns(event) {
  if (chapterDropdown && chapterDropdown.classList.contains('open')) {
    chapterDropdown.classList.remove('open');
  }
  if (controlDrawer && controlDrawer.classList.contains('open')) {
    const dock = document.getElementById('bottomControlDock');
    if (dock && !dock.contains(event.target)) {
      controlDrawer.classList.remove('open');
      dock.classList.remove('expanded');
      if (drawerToggleBtn) {
        drawerToggleBtn.innerHTML = 'Menu';
        drawerToggleBtn.classList.remove('active');
      }
    }
  }
  const tips = document.getElementById('drawerTips');
  if (tips && tips.classList.contains('open')) {
    if (event.target === tips) {
      tips.classList.remove('open');
      const btn = document.getElementById('tipsToggleBtn');
      if (btn) btn.classList.remove('active');
    }
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
  currentActiveSection = document.querySelector('.chapter-section.active');
  sentenceTimeIndex = currentActiveSection ? Array.from(currentActiveSection.querySelectorAll('.sentence-unit')).map(el => ({
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
  if (!candidate) return null;
  if (time < candidate.end) return candidate.el;
  // Bounded silence gap absorption: absorb inter-sentence gaps up to 1.5s
  if (time - candidate.end <= 1.5) {
    const nextIdx = sentenceTimeIndex.indexOf(candidate) + 1;
    if (nextIdx < sentenceTimeIndex.length) {
      if (time < sentenceTimeIndex[nextIdx].start) {
        return candidate.el;
      }
    } else {
      return candidate.el;
    }
  }
  return null;
}

let currentSeekGen = 0;

function isSameAudioSource(srcA, srcB) {
  if (!srcA || !srcB) return false;
  try {
    const uA = new URL(srcA, window.location.href);
    const uB = new URL(srcB, window.location.href);
    return uA.origin === uB.origin && decodeURIComponent(uA.pathname) === decodeURIComponent(uB.pathname);
  } catch(e) {
    return srcA === srcB;
  }
}

function playSentenceAtTime(start) {
  if (!audio) return;
  const thisGen = ++currentSeekGen;
  
  const activeSec = document.querySelector('.chapter-section.active') || document.querySelector('.chapter-section');
  const targetUrl = activeSec ? resolveAudioSource(activeSec) : audio.getAttribute('src');

  const performPlay = () => {
    try {
      audio.currentTime = start;
    } catch(e) {
      console.warn("[Audio] Seek error:", e);
    }
    const p = audio.play();
    if (p && p.catch) {
      p.catch(function(err) {
        if (err.name !== 'AbortError' && currentSeekGen === thisGen) {
          console.warn('[Audio] Playback error:', err);
          if (globalPlayBtn && audio.paused) globalPlayBtn.textContent = '▶ Play';
        }
      });
    }
    if (globalPlayBtn) globalPlayBtn.textContent = '⏸ Pause';
    startSyncLoop();
  };

  const targetSentence = findSentenceAt(start);
  if (targetSentence) {
    if (!targetSentence._cachedWords) {
      targetSentence._cachedWords = Array.from(targetSentence.querySelectorAll('.w'));
    }
    const firstWord = targetSentence._cachedWords[0];
    if (firstWord) {
      const ws = parseFloat(firstWord.dataset.s) || start;
      const we = (targetSentence._cachedWords[1] ? parseFloat(targetSentence._cachedWords[1].dataset.s) : parseFloat(firstWord.dataset.e)) || (start + 0.3);
      setActiveWord(firstWord, ws, we, 0);
    } else {
      clearActiveWord();
    }
  } else {
    clearActiveWord();
  }

  const isDifferentTrack = targetUrl && (!audio.src || !isSameAudioSource(audio.src, targetUrl));

  if (isDifferentTrack) {
    audio.src = targetUrl;
    if (audio.readyState >= 1) {
      performPlay();
    } else {
      audio.addEventListener('loadedmetadata', function onMeta() {
        if (currentSeekGen === thisGen) {
          performPlay();
        }
      }, { once: true });
      audio.load();
    }
  } else {
    if (audio.readyState >= 1) {
      performPlay();
    } else {
      audio.addEventListener('loadedmetadata', function onMeta() {
        if (currentSeekGen === thisGen) {
          performPlay();
        }
      }, { once: true });
      audio.load();
    }
  }
}
window.playSentenceAtTime = playSentenceAtTime;

let nextAudioPreloader = null;
function preloadNextChapterAudio(nextCh) {
  if (nextCh === null || nextCh === undefined || nextCh < 0) return;
  const nextSec = document.getElementById('chapter-' + nextCh) || document.querySelector('.chapter-section[data-ch="' + nextCh + '"]');
  let rawAudio = null;
  if (nextSec) {
    rawAudio = resolveAudioSource(nextSec);
  }
  if (!rawAudio) {
    const nextMenu = document.getElementById('menu-ch-' + nextCh);
    if (nextMenu && nextMenu.dataset && nextMenu.dataset.audio) {
      rawAudio = nextMenu.dataset.audio;
    }
  }
  if (!rawAudio) return;

  if (!nextAudioPreloader) {
    try {
      if (typeof Audio !== 'undefined') {
        nextAudioPreloader = new Audio();
      } else if (document.createElement) {
        nextAudioPreloader = document.createElement('audio');
      }
    } catch(e) {}
  }
  if (nextAudioPreloader && nextAudioPreloader.src !== rawAudio) {
    try {
      nextAudioPreloader.preload = 'auto';
      nextAudioPreloader.src = rawAudio;
      if (typeof nextAudioPreloader.load === 'function') {
        nextAudioPreloader.load();
      }
    } catch(e) {}
  }
  if (nextAudioPreloader) {
    window.nextAudioPreloader = nextAudioPreloader;
  }
}
window.preloadNextChapterAudio = preloadNextChapterAudio;

function switchChapter(chNum, autoPlay) {
  setUserSeeking(false);
  // Architectural boundary: Client-side PasskeyGate is an interactive preview guard.
  // In production delivery, chapters are physically chunk-sliced and access-controlled by publisher.py.
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
  hideMarginalia();
  
  document.querySelectorAll('.chapter-section').forEach(sec => {
    sec.classList.remove('active');
    if (parseInt(sec.dataset.ch, 10) === chNum) {
      sec.classList.add('active');
      currentActiveSection = sec;
      currentActiveWordStart = -1;
      currentActiveWordEnd = -1;
      const audioSrc = resolveAudioSource(sec);
      if (audio.getAttribute('src') !== audioSrc) {
        const wasPlaying = autoPlay || !audio.paused;
        audio.src = audioSrc;
        try { audio.currentTime = 0; } catch(e) {}
        currentPlayingId = null;
        clearActiveWord();
        if (wasPlaying) {
          try { audio.currentTime = 0; } catch(e) {}
          safePlay(audio);
          if (globalPlayBtn) globalPlayBtn.textContent = '⏸ Pause';
        }
      } else if (autoPlay && audio.paused) {
        try { audio.currentTime = 0; } catch(e) {}
        safePlay(audio);
        if (globalPlayBtn) globalPlayBtn.textContent = '⏸ Pause';
      }
      const firstSentence = sec.querySelector('.sentence-unit[data-matched="1"]') || sec.querySelector('.sentence-unit');
      if (shadowState.phase !== 'idle' || (typeof focusModeActive !== 'undefined' && (focusModeActive || pocketModeActive))) {
        if (firstSentence) {
          shadowState.sentence = firstSentence;
          shadowState.completed = 0;
          currentPlayingId = firstSentence.id;
          firstSentence.classList.add('active', 'card-collapsed');
          if (focusModeActive || pocketModeActive) {
            shadowState.phase = 'playing';
          }
          if (autoPlay) {
            const start = parseFloat(firstSentence.dataset.start);
            if (Number.isFinite(start)) {
              playSentenceAtTime(start);
            } else {
              safePlay(audio);
            }
          }
          if (typeof updateFocusSentenceDisplay === 'function') updateFocusSentenceDisplay();
          if (typeof updateFocusStatus === 'function') updateFocusStatus();
          if (typeof scheduleFocusDockHide === 'function') scheduleFocusDockHide();
          if (typeof updateFocusPlayBtn === 'function') updateFocusPlayBtn(autoPlay);
        }
      } else if (autoPlay && firstSentence) {
        currentPlayingId = firstSentence.id;
        firstSentence.classList.add('active', 'card-collapsed');
        if (autoScrollEnabled && typeof firstSentence.scrollIntoView === 'function') {
          firstSentence.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    }
  });
  rebuildSentenceTimeIndex();
  reportLibraryProgress(chNum, 0);
  updateMediaSessionMetadata();
  preloadNextChapterAudio(chNum + 1);
  
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

switchChapter(activeChapterNum);
preloadNextChapterAudio(activeChapterNum + 1);

function toggleDrawer(event) {
  if (event && event.stopPropagation) event.stopPropagation();
  const dock = document.getElementById('bottomControlDock');
  const isOpen = controlDrawer.classList.contains('open');
  if (isOpen) {
    controlDrawer.classList.remove('open');
    if (dock) dock.classList.remove('expanded');
    if (drawerToggleBtn) {
      drawerToggleBtn.innerHTML = 'Menu';
      drawerToggleBtn.classList.remove('active');
    }
    localStorage.setItem(STORAGE_PREFIX + 'drawer_open', 'false');
    scheduleMainDockHide();
  } else {
    hideMarginalia();
    if (chapterDropdown) chapterDropdown.classList.remove('open');
    const tips = document.getElementById('drawerTips');
    if (tips) tips.classList.remove('open');
    controlDrawer.classList.add('open');
    if (dock) {
      dock.classList.remove('dock-idle-hidden');
      dock.classList.add('expanded');
    }
    if (dockIdleTimer) {
      clearTimeout(dockIdleTimer);
      dockIdleTimer = null;
    }
    if (drawerToggleBtn) {
      drawerToggleBtn.innerHTML = 'Close';
      drawerToggleBtn.classList.add('active');
    }
    localStorage.setItem(STORAGE_PREFIX + 'drawer_open', 'true');
  }
}

const savedDrawerState = localStorage.getItem(STORAGE_PREFIX + 'drawer_open');
// Clean reading canvas invariant: drawers always start closed on load
localStorage.setItem(STORAGE_PREFIX + 'drawer_open', 'false');

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
  document.querySelectorAll('.theme-dot').forEach(dot => {
    dot.classList.toggle('active', dot.classList.contains('theme-dot-' + theme));
  });
  scheduleMainDockHide();
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
    if (typeof hideMarginalia === 'function') hideMarginalia();
  } else {
    document.documentElement.removeAttribute('data-hide-chinese');
  }
  localStorage.setItem(STORAGE_PREFIX + 'hide_chinese', String(isEnglish));
  localStorage.setItem('audible_hide_chinese', String(isEnglish));
  updateLanguageModeUI(mode);
  scheduleMainDockHide();
}

function updateLanguageModeUI(mode) {
  const isEnglish = (mode === 'english');
  const lockBtn = document.getElementById('chineseLockBtn') || document.getElementById('langToggleBtn');
  if (lockBtn && lockBtn.classList.contains('pill-btn')) {
    lockBtn.textContent = isEnglish ? 'EN' : 'Dual';
    lockBtn.classList.toggle('active', !isEnglish);
  }
}

function toggleChineseLock() {
  const isEnglish = document.documentElement.getAttribute('data-hide-chinese') === 'true';
  setLanguageMode(isEnglish ? 'bilingual' : 'english');
}

window.setLanguageMode = setLanguageMode;
window.toggleChineseLock = toggleChineseLock;
window.toggleLanguageMode = toggleChineseLock;

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
  scheduleMainDockHide();
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
    const willOpen = !tipsEl.classList.contains('open');
    tipsEl.classList.toggle('open');
    if (btn) btn.classList.toggle('active', willOpen);
    if (willOpen && controlDrawer && controlDrawer.classList.contains('open')) {
      controlDrawer.classList.remove('open');
      const dock = document.getElementById('bottomControlDock');
      if (dock) dock.classList.remove('expanded');
      if (drawerToggleBtn) {
        drawerToggleBtn.innerHTML = 'Menu';
        drawerToggleBtn.classList.remove('active');
      }
    }
  }
}

function showToast() {}

function startSentenceShadowing(sentenceEl) {
  if (!sentenceEl) return;
  if (sentenceEl.dataset.matched !== '1') {
    return;
  }
  if (shadowState.timer) clearTimeout(shadowState.timer);
  shadowState.phase = 'playing';
  shadowState.completed = 0;
  shadowState.pauseStartTime = 0;
  shadowState.sentence = sentenceEl;
  renderRepeatBtn(shadowState.repetitions || 1);
  requestShadowWakeLock();
  updatePocketStatus();
  updatePocketSentenceDisplay();
  
  const activeSection = document.querySelector('.chapter-section.active') || document.querySelector('.chapter-section');
  if (activeSection) {
    const desiredSrc = resolveAudioSource(activeSection);
    if (desiredSrc && audio.getAttribute('src') !== desiredSrc) {
      audio.src = desiredSrc;
    }
  }
  const start = parseFloat(sentenceEl.dataset.start);
  if (Number.isFinite(start)) {
    playSentenceAtTime(start);
  } else {
    safePlay(audio);
  }
  if (globalPlayBtn) globalPlayBtn.textContent = '⏸ Pause';
  sentenceEl.classList.add('active', 'card-collapsed');
}

function hideMarginalia(event) {
  if (event && event.stopPropagation) event.stopPropagation();
  const note = document.getElementById('marginaliaNote');
  if (note) {
    note.classList.remove('visible');
    note.style.transform = '';
  }
  const backdrop = document.getElementById('marginaliaBackdrop');
  if (backdrop) {
    backdrop.classList.remove('visible');
  }
  lastClickedSentenceId = null;
}

function positionMarginalia(targetEl, noteEl) {
  if (!targetEl || !noteEl) return;
  const mainEl = document.querySelector('.reader-main');
  if (!mainEl) return;
  const mRect = mainEl.getBoundingClientRect();
  const tRect = targetEl.getBoundingClientRect();
  const relTop = Math.max(0, tRect.top - mRect.top);
  noteEl.style.top = Math.round(relTop) + 'px';
}

function showMarginaliaForSentence(sentenceEl, forceShow = false) {
  if (!sentenceEl) return;
  if (chapterDropdown && chapterDropdown.classList.contains('open')) return;
  const isChineseLocked = document.documentElement.getAttribute('data-hide-chinese') === 'true';
  if (isChineseLocked && !forceShow) return;

  const note = document.getElementById('marginaliaNote');
  if (!note) return;

  let transHtml = '';
  let vocabHtml = '';

  const transAttr = sentenceEl.getAttribute('data-trans');
  if (transAttr) {
    transHtml = escapeHtml(transAttr);
  } else {
    const transEl = sentenceEl.querySelector('.inspect-trans');
    if (transEl) transHtml = transEl.innerHTML;
  }

  const vocabRaw = sentenceEl.getAttribute('data-vocab');
  if (vocabRaw) {
    try {
      const vocabList = JSON.parse(vocabRaw);
      if (Array.isArray(vocabList) && vocabList.length > 0) {
        vocabHtml = vocabList.map(v =>
          `<div class="vocab-row"><span class="v-word">${escapeHtml(v.word || '')}</span><span class="v-pos">${escapeHtml(v.pos || '')}</span><span class="v-def">${escapeHtml(v.def || '')}</span></div>`
        ).join('');
      }
    } catch(e) {}
  } else {
    const vocabEl = sentenceEl.querySelector('.inspect-vocab-list');
    if (vocabEl) vocabHtml = vocabEl.innerHTML;
  }

  if (!transHtml && !vocabHtml) {
    hideMarginalia();
    return;
  }

  const transTarget = document.getElementById('marginaliaTrans');
  const vocabTarget = document.getElementById('marginaliaVocab');

  if (transTarget) transTarget.innerHTML = transHtml;
  if (vocabTarget) {
    vocabTarget.innerHTML = vocabHtml;
    vocabTarget.style.display = vocabHtml ? 'flex' : 'none';
  }

  const contentEl = document.getElementById('marginaliaContent');
  if (contentEl) contentEl.scrollTop = 0;

  positionMarginalia(sentenceEl, note);
  note.classList.add('visible');
  const backdrop = document.getElementById('marginaliaBackdrop');
  if (backdrop) {
    backdrop.classList.add('visible');
  }
  lastClickedSentenceId = sentenceEl.id;
}

function escapeHtml(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function updateSentenceInspectors(sentenceEl) {
  // Pure focus playback: quietly fade out marginalia when audio advances to a new sentence
  if (lastClickedSentenceId && sentenceEl && sentenceEl.id !== lastClickedSentenceId) {
    hideMarginalia();
  }
}

document.addEventListener('click', function(e) {
  if (controlDrawer && controlDrawer.classList.contains('open')) {
    const dock = document.getElementById('bottomControlDock');
    if (dock && !dock.contains(e.target)) {
      controlDrawer.classList.remove('open');
      dock.classList.remove('expanded');
      if (drawerToggleBtn) {
        drawerToggleBtn.innerHTML = 'Menu';
        drawerToggleBtn.classList.remove('active');
      }
      scheduleMainDockHide();
    }
  }
  const note = document.getElementById('marginaliaNote');
  if (!note || !note.classList.contains('visible')) return;
  if (note.contains(e.target) || e.target.closest('.sentence-text') || e.target.closest('.sentence-unit')) {
    return;
  }
  hideMarginalia();
});

window.addEventListener('resize', function() {
  if (lastClickedSentenceId) {
    const el = document.getElementById(lastClickedSentenceId);
    const note = document.getElementById('marginaliaNote');
    if (el && note && note.classList.contains('visible')) {
      positionMarginalia(el, note);
    }
  }
});

(function initMarginaliaGestures() {
  const note = document.getElementById('marginaliaNote');
  if (!note) return;
  let startY = 0;
  let currentY = 0;
  let isDragging = false;

  note.addEventListener('touchstart', function(e) {
    if (e.touches.length !== 1) return;
    const content = document.getElementById('marginaliaContent');
    if (content && content.scrollTop > 4) return;
    startY = e.touches[0].clientY;
    currentY = startY;
    isDragging = true;
  }, { passive: true });

  note.addEventListener('touchmove', function(e) {
    if (!isDragging) return;
    currentY = e.touches[0].clientY;
    const dy = currentY - startY;
    if (dy > 0) {
      note.style.transform = 'translateY(' + dy + 'px)';
    }
  }, { passive: true });

  note.addEventListener('touchend', function(e) {
    if (!isDragging) return;
    isDragging = false;
    const dy = currentY - startY;
    note.style.transform = '';
    if (dy > 48) {
      hideMarginalia();
    }
  }, { passive: true });
})();

function handleSentenceClick(event, id, start, end, hasMatch) {
  if (event && event.stopPropagation) event.stopPropagation();
  if (controlDrawer && controlDrawer.classList.contains('open')) {
    controlDrawer.classList.remove('open');
    const dock = document.getElementById('bottomControlDock');
    if (dock) dock.classList.remove('expanded');
    if (drawerToggleBtn) {
      drawerToggleBtn.innerHTML = 'Menu';
      drawerToggleBtn.classList.remove('active');
    }
  }
  if (chapterDropdown && chapterDropdown.classList.contains('open')) {
    chapterDropdown.classList.remove('open');
  }
  audioRecoveryRetries = 0;
  scheduleMainDockHide();
  const el = document.getElementById(id);
  if (!el) return;
  
  const now = Date.now();
  const isDoubleTap = (lastSentenceClickId === id && (now - lastSentenceClickTime) < 400);
  if (isDoubleTap) {
    lastSentenceClickTime = 0;
  } else {
    lastSentenceClickTime = now;
  }
  lastSentenceClickId = id;

  // Cancel any pending shadow repeat timer
  if (shadowState.timer) {
    clearTimeout(shadowState.timer);
    shadowState.timer = null;
  }
  shadowState.pauseStartTime = 0;
  shadowState.isInternalPause = false;
  shadowState.completed = 0;
  shadowState.sentence = el;

  const activeSec = document.querySelector('.chapter-section.active') || document.querySelector('.chapter-section');
  if (activeSec) {
    activeSec.querySelectorAll('.sentence-unit.active').forEach(u => {
      if (u !== el) u.classList.remove('active', 'card-collapsed');
    });
  }

  const isChineseLocked = document.documentElement.getAttribute('data-hide-chinese') === 'true';
  el.classList.add('active');
  if (isChineseLocked) {
    if (isDoubleTap) {
      const note = document.getElementById('marginaliaNote');
      const isAlreadyVisible = note && note.classList.contains('visible') && lastClickedSentenceId === id;
      if (isAlreadyVisible) {
        el.classList.add('card-collapsed');
        hideMarginalia();
      } else {
        el.classList.remove('card-collapsed');
        showMarginaliaForSentence(el, true);
      }
      try { window.getSelection().removeAllRanges(); } catch(e) {}
    } else {
      el.classList.add('card-collapsed');
      hideMarginalia();
    }
  } else {
    if (isDoubleTap) {
      const note = document.getElementById('marginaliaNote');
      const isAlreadyVisible = note && note.classList.contains('visible') && lastClickedSentenceId === id;
      if (isAlreadyVisible) {
        el.classList.add('card-collapsed');
        hideMarginalia();
      } else {
        el.classList.remove('card-collapsed');
        showMarginaliaForSentence(el);
      }
      try { window.getSelection().removeAllRanges(); } catch(e) {}
    } else {
      el.classList.remove('card-collapsed');
      showMarginaliaForSentence(el);
    }
  }

  currentPlayingId = id;

  // Instant 0ms first word highlight
  if (!el._cachedWords) {
    el._cachedWords = Array.from(el.querySelectorAll('.w'));
  }
  const firstWord = el._cachedWords[0];
  if (firstWord) {
    const ws = parseFloat(firstWord.dataset.s) || start;
    const we = (el._cachedWords[1] ? parseFloat(el._cachedWords[1].dataset.s) : parseFloat(firstWord.dataset.e)) || (start + 0.3);
    setActiveWord(firstWord, ws, we, 0);
  } else {
    clearActiveWord();
  }

  if (focusModeActive || pocketModeActive) {
    updateFocusSentenceDisplay();
    updateFocusStatus();
  }

  try {
    localStorage.setItem(STORAGE_PREFIX + 'last_sentence_c' + activeChapterNum, id);
  } catch(e) {}

  const isMatched = (hasMatch === undefined || hasMatch === null) ? (Number.isFinite(start) && Number.isFinite(end) && end > start && start >= 0) : Boolean(hasMatch);

  if (window.__HAS_AUDIO__ && Number.isFinite(start) && start >= 0) {
    setUserSeeking(true, start);
    playSentenceAtTime(start);
    return;
  } else if (window.__HAS_AUDIO__) {
    const units = activeSec ? Array.from(activeSec.querySelectorAll('.sentence-unit')) : [];
    const idx = units.indexOf(el);
    let interpolated = false;
    if (idx !== -1) {
      let prevTime = null, prevIdx = -1;
      for (let i = idx - 1; i >= 0; i--) {
        const u = units[i];
        const eVal = parseFloat(u.dataset.end);
        const sVal = parseFloat(u.dataset.start);
        if (Number.isFinite(eVal) && eVal >= 0) { prevTime = eVal; prevIdx = i; break; }
        if (Number.isFinite(sVal) && sVal >= 0) { prevTime = sVal; prevIdx = i; break; }
      }

      let nextTime = null, nextIdx = -1;
      for (let i = idx + 1; i < units.length; i++) {
        const u = units[i];
        const sVal = parseFloat(u.dataset.start);
        const eVal = parseFloat(u.dataset.end);
        if (Number.isFinite(sVal) && sVal >= 0) { nextTime = sVal; nextIdx = i; break; }
        if (Number.isFinite(eVal) && eVal >= 0) { nextTime = eVal; nextIdx = i; break; }
      }

      if (prevTime !== null && nextTime !== null && nextTime >= prevTime) {
        const gapSteps = nextIdx - prevIdx;
        const stepOffset = idx - prevIdx;
        const targetTime = prevTime + (nextTime - prevTime) * (stepOffset / gapSteps);
        setUserSeeking(true, targetTime);
        playSentenceAtTime(targetTime);
        interpolated = true;
      } else if (prevTime !== null) {
        const dur = (audio && Number.isFinite(audio.duration)) ? audio.duration : Infinity;
        if (prevTime < dur - 3) {
          setUserSeeking(true, prevTime);
          playSentenceAtTime(prevTime);
          interpolated = true;
        } else {
          interpolated = true;
        }
      } else if (nextTime !== null) {
        setUserSeeking(true, 0);
        playSentenceAtTime(0);
        interpolated = true;
      }
    }
  }
}

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
    safePlay(audio);
    globalPlayBtn.textContent = '⏸ Pause';
  } else {
    audio.pause();
    globalPlayBtn.textContent = '▶ Play';
  }
}

audio.preservesPitch = true;
audio.mozPreservesPitch = true;
audio.webkitPreservesPitch = true;

const MAIN_REP_LEVELS = [1, 2, 3];
const REPEAT_ICON_SVG = '<svg class="dock-rep-icon" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/><path d="M21 13v1a4 4 0 0 1-4 4H3"/></svg>';

function renderRepeatBtn(rep) {
  const repBtn = document.getElementById('repeatBtn') || document.getElementById('shadowBtn');
  if (!repBtn) return;
  if (rep > 1) {
    repBtn.innerHTML = `${REPEAT_ICON_SVG}<span class="rep-badge">${rep}</span>`;
    repBtn.classList.add('active');
  } else {
    repBtn.innerHTML = REPEAT_ICON_SVG;
    repBtn.classList.remove('active');
  }
}

function setMainRepetitions(n) {
  const nextRep = Math.max(1, parseInt(n, 10) || 1);
  shadowState.repetitions = nextRep;
  try {
    localStorage.setItem(STORAGE_PREFIX + 'repetitions', String(nextRep));
    localStorage.setItem('reader_focus_repetitions', String(nextRep));
  } catch(e) {}
  renderRepeatBtn(nextRep);
  const focusRepBtn = document.getElementById('focusRepBtn');
  if (focusRepBtn) {
    focusRepBtn.textContent = `${nextRep}×`;
  }
  if (nextRep === 1) {
    if (shadowState.phase !== 'idle') {
      stopShadowing();
    }
  } else {
    if (shadowState.phase === 'idle' && audio && !audio.paused) {
      const activeSection = document.querySelector('.chapter-section.active');
      const sentence = findSentenceAt(audio.currentTime) || 
        (currentPlayingId ? document.getElementById(currentPlayingId) : null) || 
        (activeSection ? activeSection.querySelector('.sentence-unit.active') : null);
      if (sentence) {
        startSentenceShadowing(sentence);
      }
    }
  }
  scheduleMainDockHide();
}

function cycleMainRepeat(e) {
  if (e && e.stopPropagation) e.stopPropagation();
  const cur = shadowState.repetitions || 1;
  const idx = MAIN_REP_LEVELS.indexOf(cur);
  const nextRep = idx !== -1 ? MAIN_REP_LEVELS[(idx + 1) % MAIN_REP_LEVELS.length] : 1;
  setMainRepetitions(nextRep);
  scheduleMainDockHide();
}

function setShadowRepetitions(value) {
  setMainRepetitions(value);
}

function stopShadowing() {
  if (shadowState.timer) {
    clearTimeout(shadowState.timer);
    shadowState.timer = null;
  }
  shadowState.phase = 'idle';
  shadowState.completed = 0;
  shadowState.pauseStartTime = 0;
  if (shadowState.sentence) {
    shadowState.sentence.classList.remove('active');
  }
  shadowState.sentence = null;
  releaseShadowWakeLock();
  clearActiveWord();
  renderRepeatBtn(shadowState.repetitions || 1);
  updatePocketStatus();
}

function toggleShadowing() {
  cycleMainRepeat();
}

function getNextShadowSentence(currentEl) {
  if (!currentEl) return null;
  if (sentenceTimeIndex && sentenceTimeIndex.length) {
    const idx = sentenceTimeIndex.findIndex(item => item.el === currentEl);
    if (idx !== -1) {
      for (let i = idx + 1; i < sentenceTimeIndex.length; i++) {
        const item = sentenceTimeIndex[i];
        if (item.el && item.el.dataset.matched !== '0' && Number.isFinite(item.start) && Number.isFinite(item.end) && item.end > item.start) {
          return item.el;
        }
      }
    }
  }
  const section = currentEl.closest('.chapter-section') || (currentActiveSection && currentActiveSection.classList.contains('active') ? currentActiveSection : document.querySelector('.chapter-section.active'));
  if (!section) return null;
  const allSentences = Array.from(section.querySelectorAll('.sentence-unit'));
  const idx = allSentences.indexOf(currentEl);
  if (idx === -1) return null;
  for (let i = idx + 1; i < allSentences.length; i++) {
    const s = allSentences[i];
    const start = parseFloat(s.dataset.start);
    const end = parseFloat(s.dataset.end);
    if (s.dataset.matched !== '0' && Number.isFinite(start) && Number.isFinite(end) && end > start) {
      return s;
    }
  }
  return null;
}

let shadowBufferWatchdog = null;
function armShadowPauseWatchdog() {
  if (shadowBufferWatchdog) clearTimeout(shadowBufferWatchdog);
  shadowBufferWatchdog = setTimeout(() => {
    if (typeof shadowState !== 'undefined' && shadowState.phase === 'pause_buffer' && shadowState.pauseStartTime > 0) {
      if (Date.now() - shadowState.pauseStartTime >= 700) {
        shadowState.pauseStartTime = 0;
        if (shadowState.timer) clearTimeout(shadowState.timer);
        if (shadowState.phase !== 'idle' && shadowState.sentence) {
          shadowState.phase = 'playing';
          audio.currentTime = parseFloat(shadowState.sentence.dataset.start);
          safePlay(audio);
        }
      } else {
        armShadowPauseWatchdog();
        return;
      }
    }
    shadowBufferWatchdog = null;
  }, 750);
}

function advanceShadowing() {
  if (shadowState.phase === 'idle' || shadowState.phase === 'pause_buffer' || !shadowState.sentence) return;
  const end = parseFloat(shadowState.sentence.dataset.end);
  if (audio.currentTime < end) return;
  
  // Continuous smooth streaming when repetitions <= 1 (Native audio flow, zero stutter, zero seek)
  if (shadowState.repetitions <= 1) {
    const nextSentence = getNextShadowSentence(shadowState.sentence);
    if (nextSentence) {
      if (shadowState.sentence) shadowState.sentence.classList.remove('active', 'card-collapsed');
      shadowState.sentence = nextSentence;
      shadowState.completed = 0;
      clearActiveWord();
      nextSentence.classList.add('active', 'card-collapsed');
      updateFocusStatus();
      updateFocusSentenceDisplay();
      if (autoScrollEnabled && !focusModeActive && !pocketModeActive) {
        const rect = nextSentence.getBoundingClientRect();
        const inView = rect.top >= 90 && rect.bottom <= (window.innerHeight - 90);
        if (!inView) {
          performAutoScroll(nextSentence);
        }
      }
      return;
    } else {
      const nextCh = activeChapterNum + 1;
      const nextOption = document.getElementById('menu-ch-' + nextCh) || 
                         document.querySelector(`.chapter-item[data-chapter="${nextCh}"]`);
      if (nextOption) {
        switchChapter(nextCh, true);
        return;
      } else {
        stopShadowing();
        return;
      }
    }
  }

  // Shadow repeating loop strictly for repetitions > 1
  shadowState.isInternalPause = true;
  audio.pause();
  shadowState.completed += 1;
  updateFocusStatus();
  
  if (shadowState.completed >= shadowState.repetitions) {
    const nextSentence = getNextShadowSentence(shadowState.sentence);
    if (nextSentence) {
      if (shadowState.sentence) shadowState.sentence.classList.remove('active', 'card-collapsed');
      shadowState.sentence = nextSentence;
      shadowState.completed = 0;
      clearActiveWord();
      updateFocusStatus();
      updateFocusSentenceDisplay();
      shadowState.phase = 'pause_buffer';
      shadowState.pauseStartTime = Date.now();
      armShadowPauseWatchdog();
      nextSentence.classList.add('active', 'card-collapsed');
      if (autoScrollEnabled && !focusModeActive && !pocketModeActive) {
        const rect = nextSentence.getBoundingClientRect();
        const inView = rect.top >= 90 && rect.bottom <= (window.innerHeight - 90);
        if (!inView) {
          performAutoScroll(nextSentence);
        }
      }
      if (shadowState.timer) clearTimeout(shadowState.timer);
      shadowState.timer = setTimeout(() => {
        if (shadowState.phase === 'idle' || !shadowState.sentence) return;
        shadowState.pauseStartTime = 0;
        shadowState.phase = 'playing';
        shadowState.isInternalPause = false;
        audio.currentTime = parseFloat(shadowState.sentence.dataset.start);
        safePlay(audio);
        updateFocusPlayBtn(true);
      }, 250);
      return;
    } else {
      const nextCh = activeChapterNum + 1;
      const nextOption = document.getElementById('menu-ch-' + nextCh) || 
                         document.querySelector(`.chapter-item[data-chapter="${nextCh}"]`);
      if (nextOption) {
        shadowState.phase = 'pause_buffer';
        shadowState.completed = 0;
        updateFocusStatus();
        switchChapter(nextCh, true);
        return;
      } else {
        stopShadowing();
        return;
      }
    }
  }
  
  shadowState.phase = 'pause_buffer';
  shadowState.pauseStartTime = Date.now();
  clearActiveWord();
  armShadowPauseWatchdog();
  if (shadowState.timer) clearTimeout(shadowState.timer);
  shadowState.timer = setTimeout(() => {
    if (shadowState.phase === 'idle' || !shadowState.sentence) return;
    shadowState.pauseStartTime = 0;
    shadowState.phase = 'replaying';
    shadowState.isInternalPause = false;
    audio.currentTime = parseFloat(shadowState.sentence.dataset.start);
    safePlay(audio);
    updateFocusPlayBtn(true);
  }, 280);
}

let lastFocusTapTime = 0;
let focusSingleTapTimer = null;
let focusBlindMode = false;
let pocketBlindMode = false;
let focusShowTrans = true;
const FOCUS_REP_LEVELS = [1, 2, 3];
const FOCUS_FONT_SCALES = [1.0, 1.25, 1.55];
let focusFontScaleIndex = 0;
let focusTouchStartY = 0;
let focusTouchStartX = 0;
let focusTouchStartTime = 0;

function applyFocusFontScale(scale) {
  const overlay = document.getElementById('focus-overlay') || document.getElementById('pocket-overlay');
  if (overlay) {
    overlay.style.setProperty('--focus-font-scale', String(scale));
  }
  const btn = document.getElementById('focusFontBtn');
  if (btn) {
    if (scale <= 1.05) {
      btn.textContent = 'A+';
      btn.classList.remove('active');
    } else if (scale <= 1.35) {
      btn.textContent = 'A++';
      btn.classList.add('active');
    } else {
      btn.textContent = 'A+++';
      btn.classList.add('active');
    }
  }
}

function cycleFocusFontSize(e) {
  if (e && e.stopPropagation) e.stopPropagation();
  focusFontScaleIndex = (focusFontScaleIndex + 1) % FOCUS_FONT_SCALES.length;
  const nextScale = FOCUS_FONT_SCALES[focusFontScaleIndex];
  applyFocusFontScale(nextScale);
  try {
    localStorage.setItem('reader_focus_font_scale', String(nextScale));
  } catch (err) {}
  scheduleFocusDockHide();
}

function adjustFocusFontScale(delta) {
  const current = FOCUS_FONT_SCALES[focusFontScaleIndex] || 1.0;
  const next = Math.max(0.85, Math.min(2.0, Math.round((current + delta) * 100) / 100));
  const idx = FOCUS_FONT_SCALES.findIndex(s => Math.abs(s - next) < 0.05);
  if (idx !== -1) {
    focusFontScaleIndex = idx;
  }
  applyFocusFontScale(next);
  try {
    localStorage.setItem('reader_focus_font_scale', String(next));
  } catch (err) {}
  scheduleFocusDockHide();
}

function initFocusPreferences() {
  try {
    const savedTrans = localStorage.getItem('reader_focus_show_trans');
    if (savedTrans !== null) {
      focusShowTrans = savedTrans !== '0';
    }
    const savedRep = localStorage.getItem('reader_focus_repetitions') || localStorage.getItem(STORAGE_PREFIX + 'repetitions');
    if (savedRep !== null) {
      const repNum = parseInt(savedRep, 10);
      if (MAIN_REP_LEVELS.includes(repNum)) {
        shadowState.repetitions = repNum;
      }
    } else {
      shadowState.repetitions = 1;
    }
    renderRepeatBtn(shadowState.repetitions);
    const savedScale = parseFloat(localStorage.getItem('reader_focus_font_scale'));
    if (Number.isFinite(savedScale)) {
      const idx = FOCUS_FONT_SCALES.findIndex(s => Math.abs(s - savedScale) < 0.05);
      if (idx !== -1) {
        focusFontScaleIndex = idx;
      }
      applyFocusFontScale(savedScale);
    } else {
      applyFocusFontScale(FOCUS_FONT_SCALES[focusFontScaleIndex]);
    }
  } catch (e) {}
  applyFocusTransVisibility();
  updateFocusStatus();
}

function applyFocusTransVisibility() {
  const overlay = document.getElementById('focus-overlay') || document.getElementById('pocket-overlay');
  const btn = document.getElementById('focusTransBtn');
  if (overlay) {
    overlay.classList.toggle('hide-trans', !focusShowTrans);
  }
  if (btn) {
    btn.classList.toggle('active', focusShowTrans);
    btn.textContent = focusShowTrans ? 'Dual' : 'EN';
  }
}

function toggleFocusTransMode(e) {
  if (e && e.stopPropagation) e.stopPropagation();
  focusShowTrans = !focusShowTrans;
  try {
    localStorage.setItem('reader_focus_show_trans', focusShowTrans ? '1' : '0');
  } catch (err) {}
  applyFocusTransVisibility();
  scheduleFocusDockHide();
}

function cycleFocusRepetitions(e) {
  if (e && e.stopPropagation) e.stopPropagation();
  const curRep = shadowState.repetitions || 1;
  const idx = FOCUS_REP_LEVELS.indexOf(curRep);
  const nextRep = idx !== -1 ? FOCUS_REP_LEVELS[(idx + 1) % FOCUS_REP_LEVELS.length] : 1;
  shadowState.repetitions = nextRep;
  try {
    localStorage.setItem('reader_focus_repetitions', String(nextRep));
  } catch (err) {}
  const repBtn = document.getElementById('focusRepBtn');
  if (repBtn) repBtn.textContent = `${nextRep}×`;
  updateFocusStatus();
  scheduleFocusDockHide(true);
}

function updateFocusStatus() {
  const repBtn = document.getElementById('focusRepBtn');
  if (repBtn) {
    if (shadowState.repetitions <= 1) {
      repBtn.textContent = '1×';
    } else {
      const cur = Math.min(shadowState.repetitions, shadowState.completed + 1);
      repBtn.textContent = `${cur}/${shadowState.repetitions}`;
    }
  }
  const statusEl = document.getElementById('focusStatus') || document.getElementById('pocketStatus');
  if (statusEl) {
    if (shadowState.repetitions <= 1) {
      statusEl.textContent = '1/1';
    } else {
      const cur = Math.min(shadowState.repetitions, shadowState.completed + 1);
      statusEl.textContent = `${cur}/${shadowState.repetitions}`;
    }
  }
  updateFocusPlayBtn();
}
const updatePocketStatus = updateFocusStatus;

function toggleFocusPlayPause(e) {
  if (e && e.stopPropagation) e.stopPropagation();
  if (!audio) return;
  if (audio.paused) {
    shadowState.isInternalPause = false;
    if (shadowState.phase === 'paused_external') shadowState.phase = 'playing';
    safePlay(audio);
    updateFocusPlayBtn(true);
    scheduleFocusDockHide();
  } else {
    shadowState.isInternalPause = false;
    audio.pause();
    updateFocusPlayBtn(false);
    showFocusDock();
  }
}

function updateFocusPlayBtn(isPlaying) {
  const btn = document.getElementById('focusPlayBtn');
  if (!btn) return;
  const playing = typeof isPlaying === 'boolean' ? isPlaying : (audio && !audio.paused);
  btn.textContent = playing ? '⏸' : '▶';
}

function updateFocusSentenceDisplay() {
  const textEl = document.getElementById('focusSentenceText') || document.getElementById('pocketSentenceText');
  const transEl = document.getElementById('focusSentenceTrans') || document.getElementById('pocketSentenceTrans');
  const box = document.getElementById('focusSentenceBox') || document.getElementById('pocketSentenceBox');
  if (!textEl) return;
  
  if (!shadowState.sentence) {
    const activeSec = document.querySelector('.chapter-section.active') || document.querySelector('.chapter-section');
    const cur = findSentenceAt((audio && Number.isFinite(audio.currentTime)) ? audio.currentTime : 0) || 
      (currentPlayingId ? document.getElementById(currentPlayingId) : null) || 
      (activeSec ? activeSec.querySelector('.sentence-unit.active') : null) || 
      (sentenceTimeIndex[0] && sentenceTimeIndex[0].el) || 
      (activeSec ? activeSec.querySelector('.sentence-unit') : null) || 
      document.querySelector('.sentence-unit');
    if (cur) shadowState.sentence = cur;
  }
  
  if (!shadowState.sentence) {
    textEl.textContent = 'Select a sentence to begin immersion';
    if (transEl) transEl.textContent = '';
    return;
  }
  
  const el = shadowState.sentence;
  clearActiveWord();
  const contentEl = el.querySelector('.s-content') || el.querySelector('.sentence-text');
  if (contentEl) {
    textEl.innerHTML = contentEl.innerHTML;
  } else {
    textEl.textContent = el.textContent;
  }
  textEl._cachedFocusWords = Array.from(textEl.querySelectorAll('.w'));
  
  if (transEl) {
    const trans = el.dataset.trans || el.querySelector('.inspect-trans')?.textContent || '';
    transEl.textContent = trans;
  }
  
  const vocabEl = document.getElementById('focusSentenceVocab');
  if (vocabEl) {
    let vocabHtml = '';
    const vocabRaw = el.dataset.vocab;
    if (vocabRaw) {
      try {
        const vocabList = JSON.parse(vocabRaw);
        if (Array.isArray(vocabList) && vocabList.length > 0) {
          vocabHtml = vocabList.map(v =>
            `<div class="vocab-row"><span class="v-word">${escapeHtml(v.word || '')}</span><span class="v-pos">${escapeHtml(v.pos || '')}</span><span class="v-def">${escapeHtml(v.def || '')}</span></div>`
          ).join('');
        }
      } catch(e) {}
    } else {
      const rawVocab = el.querySelector('.inspect-vocab-list');
      if (rawVocab) vocabHtml = rawVocab.innerHTML;
    }
    if (vocabHtml) {
      vocabEl.innerHTML = vocabHtml;
      vocabEl.style.display = 'flex';
    } else {
      vocabEl.innerHTML = '';
      vocabEl.style.display = 'none';
    }
  }
  
  if (box) {
    box.classList.remove('revealed');
  }
}
const updatePocketSentenceDisplay = updateFocusSentenceDisplay;

function gotoNextShadowSentence() {
  if (!sentenceTimeIndex || !sentenceTimeIndex.length) return;
  scheduleFocusDockHide();
  let curIdx = shadowState.sentence ? sentenceTimeIndex.findIndex(item => item.el === shadowState.sentence) : -1;
  if (curIdx === -1) {
    const curSentence = findSentenceAt(audio.currentTime);
    curIdx = curSentence ? sentenceTimeIndex.findIndex(item => item.el === curSentence) : -1;
  }
  if (curIdx >= sentenceTimeIndex.length - 1) {
    const nextCh = activeChapterNum + 1;
    const nextOption = document.getElementById('menu-ch-' + nextCh) || 
                       document.querySelector(`.chapter-item[data-chapter="${nextCh}"]`);
    if (nextOption) {
      switchChapter(nextCh, true);
      return;
    }
  }
  const nextIdx = Math.min(sentenceTimeIndex.length - 1, Math.max(0, curIdx + 1));
  const target = sentenceTimeIndex[nextIdx];
  if (target && target.el) {
    startSentenceShadowing(target.el);
    updateFocusSentenceDisplay();
  }
}

function gotoPreviousShadowSentence() {
  if (!sentenceTimeIndex || !sentenceTimeIndex.length) return;
  scheduleFocusDockHide();
  let curIdx = shadowState.sentence ? sentenceTimeIndex.findIndex(item => item.el === shadowState.sentence) : -1;
  if (curIdx === -1) {
    const curSentence = findSentenceAt(audio.currentTime);
    curIdx = curSentence ? sentenceTimeIndex.findIndex(item => item.el === curSentence) : -1;
  }
  const prevIdx = (curIdx > 0) ? curIdx - 1 : 0;
  const target = sentenceTimeIndex[prevIdx];
  if (target && target.el) {
    startSentenceShadowing(target.el);
    updateFocusSentenceDisplay();
  }
}

function replayCurrentShadowSentence() {
  if (!shadowState.sentence) {
    const curSentence = findSentenceAt(audio.currentTime) || (sentenceTimeIndex[0] && sentenceTimeIndex[0].el);
    if (curSentence) startSentenceShadowing(curSentence);
  }
  if (shadowState.sentence) {
    shadowState.completed = 0;
    shadowState.phase = 'playing';
    shadowState.pauseStartTime = 0;
    const start = parseFloat(shadowState.sentence.dataset.start);
    if (Number.isFinite(start)) {
      if (typeof playSentenceAtTime === 'function') {
        playSentenceAtTime(start);
      } else {
        audio.currentTime = start;
        safePlay(audio);
      }
    }
    updateFocusPlayBtn(true);
    updateFocusStatus();
    updateFocusSentenceDisplay();
  }
}

function toggleFocusBlindMode(e) {
  if (e && e.stopPropagation) e.stopPropagation();
  focusBlindMode = !focusBlindMode;
  pocketBlindMode = focusBlindMode;
  const overlay = document.getElementById('focus-overlay') || document.getElementById('pocket-overlay');
  const btn = document.getElementById('focusBlindBtn') || document.getElementById('pocketBlindBtn');
  if (overlay) {
    overlay.classList.toggle('blind-mode', focusBlindMode);
  }
  if (btn) {
    btn.textContent = 'Audio';
    btn.classList.toggle('active', focusBlindMode);
  }
  scheduleFocusDockHide();
}
const togglePocketBlindMode = toggleFocusBlindMode;


function handleFocusDblClick(e) {
  if (e && e.stopPropagation) e.stopPropagation();
  toggleFocusMode(false);
}

function handleFocusSentenceBoxClick(e) {
  if (e && e.target && (
    e.target.closest('#focusDock') ||
    e.target.closest('.focus-close-icon') || e.target.closest('.pocket-close-icon')
  )) {
    return;
  }
  const box = document.getElementById('focusSentenceBox') || document.getElementById('pocketSentenceBox');
  if (focusBlindMode && box && !box.classList.contains('revealed')) {
    box.classList.add('revealed');
  }
  replayCurrentShadowSentence();
}
const handlePocketSentenceBoxClick = handleFocusSentenceBoxClick;

function handleFocusTouchStart(e) {
  if ((!focusModeActive && !pocketModeActive) || !e.touches || e.touches.length !== 1) return;
  const isNearBottom = (typeof e.touches[0].clientY === 'number') && (e.touches[0].clientY >= window.innerHeight - 64);
  if (isNearBottom) showFocusDock();
  focusTouchStartY = e.touches[0].clientY;
  focusTouchStartX = e.touches[0].clientX;
  focusTouchStartTime = Date.now();
}
const handlePocketTouchStart = handleFocusTouchStart;

function handleFocusTouchEnd(e) {
  if ((!focusModeActive && !pocketModeActive) || !e.changedTouches || e.changedTouches.length !== 1) return;
  const deltaY = e.changedTouches[0].clientY - focusTouchStartY;
  const deltaX = e.changedTouches[0].clientX - focusTouchStartX;
  const deltaTime = Date.now() - focusTouchStartTime;

  // Horizontal swipe only for switching sentences (Left swipe = Next, Right swipe = Previous)
  // Vertical scrolling is 100% reserved for native document scrolling of long sentences
  if (Math.abs(deltaX) > 48 && Math.abs(deltaX) > Math.abs(deltaY) * 1.4 && deltaTime < 600) {
    if (deltaX < 0) {
      gotoNextShadowSentence();
    } else {
      gotoPreviousShadowSentence();
    }
  }
}
const handlePocketTouchEnd = handleFocusTouchEnd;

let focusDockHideTimer = null;

function scheduleFocusDockHide() {
  const forceReset = arguments[0];
  const dock = document.getElementById('focusDock');
  if (!dock) return;
  if (dock.classList.contains('dock-hidden')) return;
  if (forceReset && focusDockHideTimer) {
    clearTimeout(focusDockHideTimer);
    focusDockHideTimer = null;
  }
  if (focusDockHideTimer) return;

  const isAudioActive = audio && (!audio.paused || shadowState.isInternalPause);
  const delay = isAudioActive ? 2800 : 3500;

  if (focusModeActive) {
    focusDockHideTimer = setTimeout(() => {
      focusDockHideTimer = null;
      const d = document.getElementById('focusDock');
      if (d && focusModeActive) {
        d.classList.add('dock-hidden');
      }
    }, delay);
  }
}

function showFocusDock() {
  if (isKeyboardNavigating) {
    scheduleFocusDockHide();
    return;
  }
  const dock = document.getElementById('focusDock');
  if (dock) dock.classList.remove('dock-hidden');
  if (focusDockHideTimer) {
    clearTimeout(focusDockHideTimer);
    focusDockHideTimer = null;
  }
  scheduleFocusDockHide();
}

function toggleFocusMode(force) {
  const overlay = document.getElementById('focus-overlay') || document.getElementById('pocket-overlay');
  if (!overlay) return;
  
  const target = typeof force === 'boolean' ? force : !focusModeActive;
  focusModeActive = target;
  pocketModeActive = target;
  clearActiveWord();
  hideMarginalia();
  if (focusSingleTapTimer) {
    clearTimeout(focusSingleTapTimer);
    focusSingleTapTimer = null;
  }
  
  if (focusModeActive) {
    const bottomDock = document.getElementById('bottomControlDock');
    if (bottomDock) bottomDock.classList.add('dock-idle-hidden');
    initFocusPreferences();
    const fDock = document.getElementById('focusDock');
    if (fDock) fDock.classList.remove('dock-hidden');
    scheduleFocusDockHide(true);
    const activeSec = document.querySelector('.chapter-section.active') || document.querySelector('.chapter-section');
    const curTime = (audio && Number.isFinite(audio.currentTime)) ? audio.currentTime : 0;
    const cur = findSentenceAt(curTime);
    const fallback = (activeSec ? activeSec.querySelector('.sentence-unit.active') : null) || 
                     (currentPlayingId ? document.getElementById(currentPlayingId) : null) || 
                     (sentenceTimeIndex[0] && sentenceTimeIndex[0].el) || 
                     (activeSec ? activeSec.querySelector('.sentence-unit') : null) || 
                     document.querySelector('.sentence-unit');
    shadowState.sentence = cur || fallback;
    if (shadowState.phase === 'idle') {
      shadowState.phase = 'playing';
      shadowState.completed = 0;
    }
    if (audio && audio.paused) {
      if (shadowState.sentence) {
        const start = parseFloat(shadowState.sentence.dataset.start);
        if (Number.isFinite(start)) {
          if (typeof playSentenceAtTime === 'function') {
            playSentenceAtTime(start);
          } else {
            audio.currentTime = start;
            safePlay(audio);
          }
        }
      } else {
        safePlay(audio);
      }
    }
    requestShadowWakeLock();
    overlay.style.display = 'flex';
    document.body.style.overflow = 'hidden';
    const btn = document.getElementById('focusModeBtn') || document.getElementById('pocketModeBtn');
    if (btn) btn.classList.add('active');
    updateFocusStatus();
    updateFocusSentenceDisplay();
  } else {
    if (focusDockHideTimer) {
      clearTimeout(focusDockHideTimer);
      focusDockHideTimer = null;
    }
    const dock = document.getElementById('focusDock');
    if (dock) dock.classList.remove('dock-hidden');
    releaseShadowWakeLock();
    overlay.style.display = 'none';
    document.body.style.overflow = '';
    const btn = document.getElementById('focusModeBtn') || document.getElementById('pocketModeBtn');
    if (btn) btn.classList.remove('active');
    if (autoScrollEnabled && shadowState.sentence && typeof shadowState.sentence.scrollIntoView === 'function') {
      shadowState.sentence.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }
}
const togglePocketMode = toggleFocusMode;

let lastFocusOverlayTapTime = 0;
function handleFocusOverlayClick(e) {
  if (e && e.target && (
    e.target.closest('#focusDock') ||
    e.target.closest('.focus-close-icon') || e.target.closest('.pocket-close-icon')
  )) {
    return;
  }
  const now = Date.now();
  if (now - lastFocusOverlayTapTime < 350) {
    lastFocusOverlayTapTime = 0;
    toggleFocusMode(false);
    return;
  }
  lastFocusOverlayTapTime = now;
  if (typeof e.clientY === 'number' && e.clientY >= window.innerHeight - 64) {
    showFocusDock();
  }
}
const handlePocketOverlayClick = handleFocusOverlayClick;

window.toggleFocusMode = toggleFocusMode;
window.togglePocketMode = toggleFocusMode;
window.toggleFocusPlayPause = toggleFocusPlayPause;
window.updateFocusPlayBtn = updateFocusPlayBtn;
window.handleFocusDblClick = handleFocusDblClick;
window.handleFocusOverlayClick = handleFocusOverlayClick;
window.handlePocketOverlayClick = handleFocusOverlayClick;
window.handleFocusTouchStart = handleFocusTouchStart;
window.handlePocketTouchStart = handleFocusTouchStart;
window.handleFocusTouchEnd = handleFocusTouchEnd;
window.handlePocketTouchEnd = handleFocusTouchEnd;
window.handleFocusSentenceBoxClick = handleFocusSentenceBoxClick;
window.handlePocketSentenceBoxClick = handleFocusSentenceBoxClick;
window.toggleFocusBlindMode = toggleFocusBlindMode;
window.togglePocketBlindMode = toggleFocusBlindMode;
window.toggleFocusTransMode = toggleFocusTransMode;
window.cycleFocusRepetitions = cycleFocusRepetitions;
window.cycleMainRepeat = cycleMainRepeat;
window.setMainRepetitions = setMainRepetitions;
window.toggleAutoScrollPill = toggleAutoScrollPill;
window.cycleFocusFontSize = cycleFocusFontSize;
window.applyFocusFontScale = applyFocusFontScale;
window.adjustFocusFontScale = adjustFocusFontScale;
window.updateFocusStatus = updateFocusStatus;
window.updatePocketStatus = updateFocusStatus;
window.updateFocusSentenceDisplay = updateFocusSentenceDisplay;
window.updatePocketSentenceDisplay = updateFocusSentenceDisplay;
window.gotoNextShadowSentence = gotoNextShadowSentence;
window.gotoPreviousShadowSentence = gotoPreviousShadowSentence;
window.replayCurrentShadowSentence = replayCurrentShadowSentence;
window.scheduleFocusDockHide = scheduleFocusDockHide;
window.showFocusDock = showFocusDock;

function startSyncLoop() {
  if (syncFrameId === null && !audio.paused && !document.hidden) syncFrameId = requestAnimationFrame(syncPlayback);
}

function stopSyncLoop() {
  if (syncFrameId !== null) cancelAnimationFrame(syncFrameId);
  syncFrameId = null;
}

function updateMediaSessionMetadata() {
  if (!('mediaSession' in navigator)) return;
  try {
    const activeSec = document.querySelector('.chapter-section.active') || document.querySelector('.chapter-section');
    const chTitle = activeSec?.querySelector('.book-title')?.textContent?.trim() || ('Chapter ' + activeChapterNum);
    const bookTitle = document.querySelector('.book-pill-title')?.textContent?.trim() || document.querySelector('#chapterSelectBtn span')?.textContent?.split('·')?.[1]?.trim() || document.querySelector('#chapterSelectBtn span')?.textContent?.split('·')?.[0]?.trim() || document.title || 'Audiobook';
    const author = document.querySelector('.book-author')?.textContent?.trim() || 'Audible';
    navigator.mediaSession.metadata = new MediaMetadata({
      title: chTitle,
      artist: author,
      album: bookTitle,
      artwork: [
        { src: '../../assets/icon-192.png', sizes: '192x192', type: 'image/png' },
        { src: '../../assets/icon-512.png', sizes: '512x512', type: 'image/png' }
      ]
    });
  } catch(e) {}
}

function initMediaSession() {
  if (!('mediaSession' in navigator)) return;
  try {
    navigator.mediaSession.setActionHandler('play', () => {
      if (audio && audio.paused) toggleGlobalPlay();
    });
    navigator.mediaSession.setActionHandler('pause', () => {
      if (audio && !audio.paused) toggleGlobalPlay();
    });
    navigator.mediaSession.setActionHandler('seekbackward', (details) => {
      const skip = details.seekOffset || 10;
      if (audio) audio.currentTime = Math.max(0, audio.currentTime - skip);
    });
    navigator.mediaSession.setActionHandler('seekforward', (details) => {
      const skip = details.seekOffset || 10;
      if (audio && audio.duration) audio.currentTime = Math.min(audio.duration, audio.currentTime + skip);
    });
    navigator.mediaSession.setActionHandler('seekto', (details) => {
      if (audio && Number.isFinite(details.seekTime)) {
        if (details.fastSeek && 'fastSeek' in audio) {
          audio.fastSeek(details.seekTime);
        } else {
          audio.currentTime = details.seekTime;
        }
        updateAudioPlayerUI();
      }
    });
    navigator.mediaSession.setActionHandler('previoustrack', () => {
      const prevCh = Math.max(0, activeChapterNum - 1);
      if (prevCh !== activeChapterNum) switchChapter(prevCh, true);
    });
    navigator.mediaSession.setActionHandler('nexttrack', () => {
      switchChapter(activeChapterNum + 1, true);
    });
  } catch(e) {}
}

audio.addEventListener('play', () => {
  globalPlayBtn.textContent = '⏸ Pause';
  if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
  updateMediaSessionMetadata();
  startSyncLoop();
  scheduleMainDockHide();
  if (focusModeActive) {
    scheduleFocusDockHide();
  }
});
audio.addEventListener('pause', () => {
  if (shadowState.isInternalPause) {
    // Internal shadow iteration pause: audio will resume in ~250ms, do NOT disrupt user immersion!
    return;
  }
  globalPlayBtn.textContent = '▶ Play';
  if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'paused';
  stopSyncLoop();
  scheduleMainDockHide();
  if (focusModeActive) {
    scheduleFocusDockHide();
  }
});
audio.addEventListener('error', (e) => {
  setUserSeeking(false);
  console.warn('[Audio] Playback error encountered:', audio.error || e);
  if (globalPlayBtn) globalPlayBtn.textContent = '▶ Play';
  if (typeof updateFocusPlayBtn === 'function') updateFocusPlayBtn(false);
  const curSrc = audio.src;
  if (curSrc && !audio.paused) {
    const curTime = audio.currentTime;
    setTimeout(() => {
      try {
        audio.load();
        audio.currentTime = curTime;
        safePlay(audio);
      } catch(err) {}
    }, 1000);
  }
});
audio.addEventListener('stalled', () => {
  console.warn('[Audio] Media data transfer stalled.');
});
let lastProgressReportTime = 0;
audio.addEventListener('timeupdate', () => {
  updateAudioPlayerUI();
  const now = Date.now();
  if (now - lastProgressReportTime >= 3000 && !Number.isNaN(audio.currentTime) && audio.duration) {
    lastProgressReportTime = now;
    reportLibraryProgress(activeChapterNum, (audio.currentTime / audio.duration) * 100);
  }
});
audio.addEventListener('loadedmetadata', () => {
  if (audio && currentPlaybackSpeed) audio.playbackRate = currentPlaybackSpeed;
  updateAudioPlayerUI();
});
audio.addEventListener('ratechange', () => {
  if (!audio) return;
  const newRate = Math.round(audio.playbackRate * 100) / 100;
  if (!Number.isFinite(newRate) || newRate <= 0) return;
  if (Math.abs(currentPlaybackSpeed - newRate) >= 0.01) {
    applyPlaybackRate(newRate);
  }
});
audio.addEventListener('durationchange', updateAudioPlayerUI);
audio.addEventListener('seeked', () => {
  setUserSeeking(false);
});

audio.addEventListener('playing', () => {
  audioRecoveryRetries = 0;
});

audio.addEventListener('waiting', () => {
  // Allow native TCP/HTTP Range buffering to proceed cleanly without issuing abort seeks
});

audio.addEventListener('stalled', () => {
  console.warn('[Audio] Media data transfer stalled; waiting for network pipeline...');
});

audio.addEventListener('error', (err) => {
  console.warn('[Audio] Media playback error encountered:', err);
  if (globalPlayBtn) globalPlayBtn.textContent = '▶ Play';
  if (typeof updateFocusPlayBtn === 'function') updateFocusPlayBtn(false);

  // Exponential backoff network recovery (clean native stream reconnect without death spiral)
  if (audioRecoveryRetries < MAX_AUDIO_RETRIES && audio && audio.src) {
    audioRecoveryRetries++;
    const retrySec = (Number.isFinite(audio.currentTime) && audio.currentTime >= 0) ? audio.currentTime : 0;
    const backoffMs = Math.min(1000 * Math.pow(2, audioRecoveryRetries - 1), 4000);
    console.warn(`[Audio] Retrying connection attempt ${audioRecoveryRetries}/${MAX_AUDIO_RETRIES} in ${backoffMs}ms...`);
    setTimeout(() => {
      if (audio) {
        audio.load();
        if (audio.readyState >= 1) {
          try { audio.currentTime = retrySec; } catch(e) {}
          safePlay(audio);
        } else {
          audio.addEventListener('loadedmetadata', function onRetryMeta() {
            try { audio.currentTime = retrySec; } catch(e) {}
            safePlay(audio);
          }, { once: true });
        }
      }
    }, backoffMs);
  }
});
audio.addEventListener('ended', () => {
  if (focusModeActive && shadowState.phase === 'idle') {
    showFocusDock();
  }
  if (shadowState.phase !== 'idle') {
    advanceShadowing();
    return;
  }
  const nextCh = activeChapterNum + 1;
  const nextOption = document.getElementById('menu-ch-' + nextCh) || 
                     document.querySelector(`.chapter-item[data-chapter="${nextCh}"]`);
  if (nextOption) {
    switchChapter(nextCh, true);
  } else {
    const firstOpt = document.getElementById('menu-ch-0') || 
                     document.querySelector('.chapter-item');
    if (firstOpt) {
      switchChapter(0, true);
    }
  }
});

document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    stopSyncLoop();
  } else {
    if (audio && !audio.paused) {
      const curSentence = findSentenceAt(audio.currentTime);
      if (curSentence) {
        if (shadowState.phase !== 'idle') {
          if (curSentence !== shadowState.sentence) {
            if (shadowState.sentence) shadowState.sentence.classList.remove('active', 'card-collapsed');
            shadowState.sentence = curSentence;
            shadowState.completed = 0;
            shadowState.phase = 'playing';
            curSentence.classList.add('active', 'card-collapsed');
            if (autoScrollEnabled) {
              performAutoScroll(curSentence);
            }
          }
        } else {
          if (curSentence.id !== currentPlayingId) {
            const oldUnit = currentPlayingId ? document.getElementById(currentPlayingId) : null;
            if (oldUnit) oldUnit.classList.remove('active');
            currentPlayingId = curSentence.id;
            curSentence.classList.add('active');
            if (autoScrollEnabled) {
              performAutoScroll(curSentence);
            }
          }
        }
      }
    }
    requestShadowWakeLock();
    startSyncLoop();
  }
});

let lastSyncTimestamp = 0;
let lastAutoScrollTimestamp = 0;

function syncPlayback() {
  syncFrameId = null;
  if (!audio.paused) {
    if (audio.seeking || isUserSeeking) {
      startSyncLoop();
      return;
    }
    const now = performance.now();
    if (now - lastSyncTimestamp >= 12) {
      lastSyncTimestamp = now;
      const curTime = audio.currentTime;
      if (!currentActiveSection || !currentActiveSection.classList.contains('active')) {
        currentActiveSection = document.querySelector('.chapter-section.active');
      }
      
      if (currentActiveSection) {
        const activeUnit = findSentenceAt(curTime);
        
        if (activeUnit) {
          if (activeUnit.id !== currentPlayingId) {
            currentPlayingId = activeUnit.id;
            clearActiveWord();
            try { localStorage.setItem(STORAGE_PREFIX + 'last_sentence_c' + activeChapterNum, activeUnit.id); } catch(e) {}
            
            currentActiveSection.querySelectorAll('.sentence-unit.active').forEach(u => {
              if (u !== activeUnit) u.classList.remove('active', 'card-collapsed');
            });
            activeUnit.classList.add('active', 'card-collapsed');
            updateSentenceInspectors(activeUnit);

            if (focusModeActive || pocketModeActive) {
              shadowState.sentence = activeUnit;
              updateFocusSentenceDisplay();
              updateFocusStatus();
            }

            if (!pocketModeActive && !focusModeActive && autoScrollEnabled) {
              requestAnimationFrame(() => {
                if (pocketModeActive || focusModeActive || !autoScrollEnabled) return;
                const rect = activeUnit.getBoundingClientRect();
                const inView = rect.top >= 90 && rect.bottom <= (window.innerHeight - 90);
                if (!inView) {
                  performAutoScroll(activeUnit);
                }
              });
            }
          }
          
          if (currentActiveWordEl && curTime >= currentActiveWordStart && curTime < currentActiveWordEnd) {
            // Short-circuit: still within active word time window
          } else {
            if (!activeUnit._cachedWords) {
              activeUnit._cachedWords = Array.from(activeUnit.querySelectorAll('.w'));
            }
            const wordEls = activeUnit._cachedWords;
            let foundWord = null;
            let foundIndex = -1;
            let foundStart = -1;
            let foundEnd = -1;
            for (let i = 0; i < wordEls.length; i++) {
              const w = wordEls[i];
              const ws = parseFloat(w.dataset.s);
              const wEnd = parseFloat(w.dataset.e);
              const nextStart = (i < wordEls.length - 1) ? parseFloat(wordEls[i + 1].dataset.s) : wEnd;
              const we = (nextStart > wEnd && nextStart - wEnd <= 0.10) ? nextStart : (wEnd + 0.06);
              if (curTime >= ws && curTime < we) {
                foundWord = w;
                foundIndex = i;
                foundStart = ws;
                foundEnd = we;
                break;
              }
            }
            
            if (foundWord !== currentActiveWordEl) {
              if (foundWord) {
                setActiveWord(foundWord, foundStart, foundEnd, foundIndex);
              } else {
                clearActiveWord();
              }
            }
          }
        } else {
          clearActiveWord();
        }
      }
      advanceShadowing();
    }
  }
  startSyncLoop();
}

rebuildSentenceTimeIndex();

// Desktop Keyboard Navigation (Arrow Keys, Spacebar, T, R, P)
window.addEventListener('keydown', (e) => {
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
    return;
  }
  if (e.metaKey || e.ctrlKey || e.altKey) {
    return;
  }
  setKeyboardNavigating();
  isProgrammaticAutoScroll = true;
  if (programmaticScrollTimer) clearTimeout(programmaticScrollTimer);
  programmaticScrollTimer = setTimeout(() => {
    isProgrammaticAutoScroll = false;
  }, 1200);

  if (focusModeActive || pocketModeActive) {
    if (e.key === 'Escape') {
      e.preventDefault();
      toggleFocusMode(false);
      return;
    }
    if (e.code === 'Space' || e.key === ' ') {
      e.preventDefault();
      toggleFocusPlayPause();
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      replayCurrentShadowSentence();
      return;
    }
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      gotoPreviousShadowSentence();
      return;
    }
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      gotoNextShadowSentence();
      return;
    }
    if (e.key === 't' || e.key === 'T' || e.code === 'KeyT') {
      e.preventDefault();
      toggleFocusTransMode();
      return;
    }
    if (e.key === 'r' || e.key === 'R' || e.code === 'KeyR') {
      e.preventDefault();
      cycleFocusRepetitions();
      return;
    }
    if (e.key === 'h' || e.key === 'H' || e.key === 'b' || e.key === 'B' || e.code === 'KeyB') {
      e.preventDefault();
      toggleFocusBlindMode();
      return;
    }
    if (e.key === 'a' || e.key === 'A' || e.code === 'KeyA') {
      e.preventDefault();
      cycleFocusFontSize();
      return;
    }
    if (e.key === '+' || e.key === '=') {
      e.preventDefault();
      adjustFocusFontScale(0.15);
      return;
    }
    if (e.key === '-' || e.key === '_') {
      e.preventDefault();
      adjustFocusFontScale(-0.15);
      return;
    }
    if (e.key === '0') {
      e.preventDefault();
      focusFontScaleIndex = 0;
      applyFocusFontScale(1.0);
      try {
        localStorage.setItem('reader_focus_font_scale', '1.0');
      } catch (err) {}
      return;
    }
  }

  if (e.key === 't' || e.key === 'T' || e.code === 'KeyT') {
    e.preventDefault();
    toggleChineseLock();
    return;
  }

  if ((e.key === 'p' || e.key === 'P' || e.code === 'KeyP') && !e.target.matches('input, textarea, select')) {
    e.preventDefault();
    toggleFocusMode();
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
  
  if (e.key === '[' || e.code === 'BracketLeft') {
    e.preventDefault();
    const prevCh = Math.max(0, activeChapterNum - 1);
    if (prevCh !== activeChapterNum) switchChapter(prevCh, true);
    return;
  }
  if (e.key === ']' || e.code === 'BracketRight') {
    e.preventDefault();
    const nextCh = activeChapterNum + 1;
    const nextOption = document.getElementById('menu-ch-' + nextCh) || 
                       document.querySelector(`.chapter-item[data-chapter="${nextCh}"]`);
    if (nextOption) switchChapter(nextCh, true);
    return;
  }

  if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
    e.preventDefault();
    if (currentIndex === 0 && e.key === 'ArrowLeft') {
      const prevCh = Math.max(0, activeChapterNum - 1);
      if (prevCh !== activeChapterNum) {
        switchChapter(prevCh, true);
        return;
      }
    }
    const targetIdx = Math.max(0, currentIndex - 1);
    const targetUnit = units[targetIdx];
    if (targetUnit) {
      if (activeUnit) activeUnit.classList.remove('active', 'card-collapsed');
      targetUnit.classList.add('active', 'card-collapsed');
      if (window.__HAS_AUDIO__ && targetUnit.dataset.matched === '1') {
        const st = parseFloat(targetUnit.dataset.start);
        if (!isNaN(st)) {
          audio.currentTime = st;
          safePlay(audio);
          globalPlayBtn.textContent = '⏸ Pause';
        }
      }
      targetUnit.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
    e.preventDefault();
    if (currentIndex === units.length - 1 && e.key === 'ArrowRight') {
      const nextCh = activeChapterNum + 1;
      const nextOption = document.getElementById('menu-ch-' + nextCh) || 
                         document.querySelector(`.chapter-item[data-chapter="${nextCh}"]`);
      if (nextOption) {
        switchChapter(nextCh, true);
        return;
      }
    }
    const targetIdx = Math.min(units.length - 1, currentIndex + 1);
    const targetUnit = units[targetIdx];
    if (targetUnit) {
      if (activeUnit) activeUnit.classList.remove('active', 'card-collapsed');
      targetUnit.classList.add('active', 'card-collapsed');
      if (window.__HAS_AUDIO__ && targetUnit.dataset.matched === '1') {
        const st = parseFloat(targetUnit.dataset.start);
        if (!isNaN(st)) {
          audio.currentTime = st;
          safePlay(audio);
          globalPlayBtn.textContent = '⏸ Pause';
        }
      }
      targetUnit.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  } else if (e.key === 'Escape') {
    hideMarginalia();
    const tips = document.getElementById('drawerTips');
    if (tips && tips.classList.contains('open')) {
      tips.classList.remove('open');
      const btn = document.getElementById('tipsToggleBtn');
      if (btn) btn.classList.remove('active');
    }
    if (controlDrawer && controlDrawer.classList.contains('open')) {
      controlDrawer.classList.remove('open');
      const dock = document.getElementById('bottomControlDock');
      if (dock) dock.classList.remove('expanded');
      if (drawerToggleBtn) {
        drawerToggleBtn.innerHTML = 'Menu';
        drawerToggleBtn.classList.remove('active');
      }
    }
    if (chapterDropdown && chapterDropdown.classList.contains('open')) {
      chapterDropdown.classList.remove('open');
    }
  } else if (e.code === 'Space') {
    e.preventDefault();
    toggleGlobalPlay();
  }
});
initMediaSession();
updateMediaSessionMetadata();
const focusOverlayEl = document.getElementById('focus-overlay');
if (focusOverlayEl) {
  focusOverlayEl.addEventListener('dblclick', handleFocusDblClick);
  focusOverlayEl.addEventListener('pointermove', (e) => {
    if (focusModeActive && typeof e.clientY === 'number' && e.clientY >= window.innerHeight - 64) {
      showFocusDock();
    }
  });
  focusOverlayEl.addEventListener('pointerdown', (e) => {
    if (focusModeActive && typeof e.clientY === 'number' && e.clientY >= window.innerHeight - 64) {
      showFocusDock();
    }
  });
}
const focusDockEl = document.getElementById('focusDock');
if (focusDockEl) {
  focusDockEl.addEventListener('pointerdown', (e) => {
    if (e && e.stopPropagation) e.stopPropagation();
    showFocusDock();
  });
}
document.addEventListener('pointermove', onUserDockActivity);
document.addEventListener('pointerdown', onUserDockActivity);
document.addEventListener('touchstart', onUserDockActivity, { passive: true });
window.addEventListener('scroll', onUserDockActivity, { passive: true });
const bottomControlDock = document.getElementById('bottomControlDock');
if (bottomControlDock) {
  bottomControlDock.addEventListener('mouseenter', () => {
    bottomControlDock._isMouseOver = true;
    if (dockIdleTimer) { clearTimeout(dockIdleTimer); dockIdleTimer = null; }
  });
  bottomControlDock.addEventListener('mouseleave', () => {
    bottomControlDock._isMouseOver = false;
    scheduleMainDockHide();
  });
}
scheduleMainDockHide();
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
