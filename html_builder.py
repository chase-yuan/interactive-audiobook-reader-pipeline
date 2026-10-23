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
    
    clean_short_title = re.sub(r'[\(\[]\s*unabridged\s*[\)\]]', '', book_title, flags=re.I).strip()
    if len(clean_short_title) > 28 and ':' in clean_short_title:
        clean_short_title = clean_short_title.split(':')[0].strip()

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
    
    <div class="nav-actions">
      <button class="icon-btn primary" id="globalPlayBtn" onclick="toggleGlobalPlay()"{play_btn_attr}>▶ Play</button>
      <button class="icon-btn" id="drawerToggleBtn" onclick="toggleDrawer()">Menu</button>
    </div>
  </div>
  
  <div class="control-drawer" id="controlDrawer">
    <div class="drawer-inner">
      <div class="audio-player-bar" id="audioPlayerBar"{audio_track_attr}>
        <button class="player-speed-btn" id="audioSpeedBtn" onclick="cyclePlaybackRate()" aria-label="Playback speed">1.0×</button>
        <span class="player-time" id="playerCurTime">00:00</span>
        <div class="player-slider-wrap">
          <input type="range" class="player-slider" id="playerScrubber" min="0" max="100" value="0" step="0.1" aria-label="Playback scrubber">
        </div>
        <span class="player-time" id="playerTotalTime">00:00</span>
        <audio id="audioTrack" preload="metadata" src="{html.escape(audio_src)}" class="hidden-audio"{audio_track_attr}></audio>
      </div>
      <div class="drawer-row">
        <div class="drawer-group">
          <button class="pill-btn active" id="chineseLockBtn" onclick="toggleChineseLock()" aria-label="Language mode (Shortcut: T)">Dual</button>
          <button class="pill-btn" onclick="toggleTheme()" aria-label="Switch theme">Theme</button>
        </div>
        <div class="drawer-group"{repeat_group_attr}>
          <button class="pill-btn" id="repeatBtn" onclick="cycleMainRepeat()" aria-label="Sentence repeat loop (Shortcut: R)">Repeat</button>
          <button class="pill-btn" id="focusModeBtn" onclick="toggleFocusMode()" aria-label="Focus mode (Shortcut: P)">Focus</button>
        </div>
        <div class="drawer-group">
          <label class="toggle-pill" aria-label="Auto-scroll to active sentence">
            <input type="checkbox" id="autoScrollCheck" checked onchange="toggleAutoScroll(this.checked)">
            <span class="toggle-badge">Auto-scroll</span>
          </label>
          <button class="pill-btn" id="tipsToggleBtn" onclick="toggleTips()" aria-label="Keyboard & Gesture shortcuts">Shortcuts</button>
        </div>
      </div>
      <div class="drawer-tips" id="drawerTips">
        <div class="tips-columns">
          <div class="tips-section">
            <div class="tips-section-title">Reading & Playback</div>
            <div class="tips-row"><span class="kbd-key">Tap Sentence</span><span>{'Play audio & show breakdown' if has_audio else 'Show translation & vocabulary breakdown'}</span></div>
            <div class="tips-row"><span class="kbd-key">{'Double Tap' if has_audio else 'Tap Active'}</span><span>{'Repeat sentence loop' if has_audio else 'Collapse translation card'}</span></div>
            {f'<div class="tips-row"><span class="kbd-key">Tap Card</span><span>Collapse card</span></div>' if has_audio else ''}
            <div class="tips-row"><span class="kbd-key">Space</span><span>Toggle translation card (peek / hide)</span></div>
            <div class="tips-row"><span class="kbd-key">← / →</span><span>Previous / Next sentence (audio only)</span></div>
            <div class="tips-row"><span class="kbd-key">T</span><span>Toggle Bilingual / English-only mode</span></div>
            {f'<div class="tips-row"><span class="kbd-key">R</span><span>Repeat sentence loop</span></div>' if has_audio else ''}
            {f'<div class="tips-row"><span class="kbd-key">P</span><span>Toggle Focus mode</span></div>' if has_audio else ''}
          </div>
          <div class="tips-section">
            <div class="tips-section-title">Focus Mode (Immersion)</div>
            <div class="tips-row"><span class="kbd-key">Space</span><span>Play / Pause</span></div>
            <div class="tips-row"><span class="kbd-key">← / →</span><span>Previous / Next sentence</span></div>
            <div class="tips-row"><span class="kbd-key">↑</span><span>Replay current sentence</span></div>
            <div class="tips-row"><span class="kbd-key">Swipe L/R</span><span>Previous / Next sentence</span></div>
            <div class="tips-row"><span class="kbd-key">R</span><span>Cycle repeats (1× / 2× / 3× / 5×)</span></div>
            <div class="tips-row"><span class="kbd-key">T</span><span>Toggle Dual / English-only</span></div>
            <div class="tips-row"><span class="kbd-key">H / B</span><span>Audio mode (hide text for listening)</span></div>
            <div class="tips-row"><span class="kbd-key">A / +/-</span><span>Scale English font size</span></div>
            <div class="tips-row"><span class="kbd-key">Double Tap / Esc</span><span>Exit Focus mode</span></div>
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
        safe_heading_label = html.escape(ch_heading_label)
        clean_title = ctitle.strip()
        disp_num = str(ch.get("display_number")) if ch.get("display_number") is not None else ""
        disp_part = rf"|\b(?:Chapter\s+)?{re.escape(disp_num)}(?!\d)\s*[\.\:—–-]\s*" if disp_num else ""
        prefix_pattern = rf"^(?:{re.escape(ch['label'])}\s*[:—–-]?\s*{disp_part})"
        sub_title = re.sub(prefix_pattern, "", clean_title, flags=re.IGNORECASE).strip()
        if not sub_title or clean_title.upper() == ch_heading_label or clean_title.upper() == f"CHAPTER {cnum}":
            title_html = safe_heading_label
        else:
            title_html = f"{safe_heading_label}<br>{html.escape(sub_title)}"
        
        html_head += f"""
  <!-- CHAPTER {cnum} -->
  <section class="chapter-section{active_cls}" id="chapter-{cnum}" data-audio="{html.escape(caudio)}" data-public-audio="{html.escape(cpublic_audio)}" data-ch="{cnum}">
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
            for s in csents:
                start_chk = s.get("audio_start", s.get("start"))
                end_chk = s.get("audio_end", s.get("end"))
                is_valid = isinstance(start_chk, (int, float)) and isinstance(end_chk, (int, float)) and start_chk >= 0 and end_chk >= start_chk
                valid_flags.append(is_valid)

            gap_groups = []
            curr_group = []
            for idx, is_v in enumerate(valid_flags):
                s = csents[idx]
                is_divider = s.get("text", "").strip() in ['* * *', '***', '---', '* * * *', '– – –', '— — —', '… … …', '• • •']
                is_estimated = is_sentence_explicitly_estimated(s)
                if not is_v and not is_divider and not is_estimated:
                    curr_group.append(idx)
                else:
                    if curr_group:
                        gap_groups.append(curr_group)
                        curr_group = []
            if curr_group:
                gap_groups.append(curr_group)

            for group in gap_groups:
                prev_idx = group[0] - 1
                next_idx = group[-1] + 1
                has_prev = prev_idx >= 0 and valid_flags[prev_idx]
                has_next = next_idx < len(csents) and valid_flags[next_idx]
                if not has_prev or not has_next:
                    for g_idx in group:
                        csents[g_idx]["audio_start"] = None
                        csents[g_idx]["audio_end"] = None
                        csents[g_idx]["has_audio_match"] = False
                        csents[g_idx]["word_spans"] = []
                    continue
                t_prev = csents[prev_idx].get("audio_end", csents[prev_idx].get("end"))
                t_next = csents[next_idx].get("audio_start", csents[next_idx].get("start"))
                if not isinstance(t_prev, (int, float)) or not isinstance(t_next, (int, float)) or t_next <= t_prev:
                    # Invariant: No physical acoustic gap exists between surrounding spoken sentences.
                    # Unnarrated footnotes/dividers MUST NOT fabricate artificial timestamps that collide with t_next.
                    for g_idx in group:
                        csents[g_idx]["audio_start"] = None
                        csents[g_idx]["audio_end"] = None
                        csents[g_idx]["has_audio_match"] = False
                        csents[g_idx]["word_spans"] = []
                    continue
                total_duration = t_next - t_prev
                words_per_s = [max(1, len(csents[g_idx].get("text", "").split())) for g_idx in group]
                total_w = sum(words_per_s)
                cum_w = 0
                for g_idx, w_cnt in zip(group, words_per_s):
                    s_t = round(t_prev + total_duration * (cum_w / total_w), 2)
                    cum_w += w_cnt
                    e_t = round(t_prev + total_duration * (cum_w / total_w), 2)
                    if has_next:
                        e_t = min(t_next, e_t)
                    if e_t <= s_t:
                        e_t = round(min(t_next if has_next else s_t + 0.1, s_t + 0.05), 2)
                    csents[g_idx]["audio_start"] = s_t
                    csents[g_idx]["audio_end"] = e_t
                    csents[g_idx]["has_audio_match"] = True
                    raw_words = csents[g_idx].get("text", "").split()
                    c_cnt = max(1, len(raw_words))
                    w_spans = []
                    prev_w_s = -1.0
                    for m_i, rw in enumerate(raw_words):
                        ws = round(s_t + (e_t - s_t) * (m_i / c_cnt), 2)
                        we = round(s_t + (e_t - s_t) * ((m_i + 1) / c_cnt), 2)
                        if ws <= prev_w_s:
                            ws = round(prev_w_s + 0.01, 2)
                        if we <= ws:
                            we = round(ws + 0.01, 2)
                        prev_w_s = ws
                        w_spans.append({"word": rw, "start": ws, "end": we, "timing_source": "interpolated"})
                    csents[g_idx]["word_spans"] = w_spans

        for s in csents:
            if s.get("text", "").strip() in ['* * *', '***', '---', '* * * *', '– – –', '— — —', '… … …', '• • •']:
                div_symbol = html.escape(s.get("text", "").strip())
                html_head += f'      <div class="scene-divider" aria-hidden="true"><span>{div_symbol}</span></div>\n'
                continue

            raw_sid = s["id"]
            sid = f"c{cnum}-{raw_sid}"
            is_h = s.get("is_heading", False)
            start = s.get("audio_start", s.get("start"))
            end = s.get("audio_end", s.get("end"))
            word_spans = s.get("word_spans", [])
            spans_are_observed = all(w.get("timing_source", "observed") in ("observed", "interpolated") for w in word_spans)
            has_match = 1 if s.get("has_audio_match", True) and spans_are_observed and isinstance(start, (int, float)) and isinstance(end, (int, float)) and end >= start else 0
            unmatched_tag = ""
            inspect_unmatched_notice = ""
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
                    ts_attr = f' data-timing-source="{timing_source}"' if timing_source and timing_source != "observed" else ""
                    word_html_list.append(f'<span class="w" data-s="{ws}" data-e="{we}"{ts_attr}>{rw}</span>')
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
            is_reorder = 1 if s.get("alignment_method") in {
                "leading_epigraph_attribution",
                "chapter_heading_numeric_variant",
                "opening_speaker_attribution",
                "dialogue_attribution_reorder",
            } else 0
            reorder_attr = ' data-reorder="1"' if is_reorder else ''
            vocab_attr = f' data-vocab="{html.escape(json.dumps(vocab, ensure_ascii=False))}"' if vocab else ''
            html_head += f"""
      <div class="sentence-unit" id="{sid}" data-start="{start_arg}" data-end="{end_arg}" data-audio-order="{s.get('audio_order', '')}" data-epigraph="{1 if s.get('alignment_method') == 'leading_epigraph_attribution' else 0}"{reorder_attr} data-matched="{has_match}"{vocab_attr}>
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
        <span class="notice-badge">Editor's Note</span>
        <div class="notice-content">
          {html.escape(editorial_notice)}
        </div>
      </div>
"""

        html_head += """    </div>
  </section>
"""

    book_id_json = json.dumps(book_id)
    html_tail = f"""
</main>

<div id="focus-overlay" class="focus-overlay pocket-overlay" onclick="handleFocusOverlayClick(event)" ontouchstart="handleFocusTouchStart(event)" ontouchend="handleFocusTouchEnd(event)">
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
  const p = audioEl.play();
  if (p && typeof p.catch === 'function') {
    p.catch(function(err) {
      if (err && err.name !== 'AbortError') {
        console.warn('[Audio] play error:', err);
      }
    });
  }
}

const SPEED_PRESETS = [1.0, 1.25, 1.5, 1.75, 2.0, 2.25, 2.5, 2.75, 3.0, 0.75];
const SPEED_LABELS = { 1.0: '1.0×', 1.25: '1.25×', 1.5: '1.5×', 1.75: '1.75×', 2.0: '2.0×', 2.25: '2.25×', 2.5: '2.5×', 2.75: '2.75×', 3.0: '3.0×', 0.75: '0.75×' };
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

let lastMediaSessionPositionUpdate = 0;
let lastScrubberRenderPct = -1;

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
let currentActiveWordStart = -1;
let currentActiveWordEnd = -1;
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
}

function toggleAutoScrollPill(btn) {
  toggleAutoScroll(!autoScrollEnabled);
  showToast(autoScrollEnabled ? 'Auto-scroll enabled' : 'Auto-scroll paused');
}
window.toggleAutoScrollPill = toggleAutoScrollPill;

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

function switchChapter(chNum, autoPlay) {
  setUserSeeking(false);
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
      currentActiveSection = sec;
      currentActiveWordStart = -1;
      currentActiveWordEnd = -1;
      const audioSrc = resolveAudioSource(sec);
      if (audio.getAttribute('src') !== audioSrc) {
        const wasPlaying = autoPlay || !audio.paused;
        audio.src = audioSrc;
        try { audio.currentTime = 0; } catch(e) {}
        currentPlayingId = null;
        if (currentActiveWordEl) {
          currentActiveWordEl.classList.remove('active-word');
          currentActiveWordEl = null;
        }
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
      if (shadowState.phase !== 'idle') {
        if (firstSentence) {
          startSentenceShadowing(firstSentence);
        }
      } else if (autoPlay && firstSentence) {
        currentPlayingId = firstSentence.id;
        firstSentence.classList.add('active', 'card-collapsed');
        if (autoScrollEnabled && typeof firstSentence.scrollIntoView === 'function') {
          firstSentence.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
      if (typeof focusModeActive !== 'undefined' && (focusModeActive || pocketModeActive)) {
        shadowState.sentence = firstSentence;
        if (typeof updateFocusSentenceDisplay === 'function') updateFocusSentenceDisplay();
        if (typeof updateFocusStatus === 'function') updateFocusStatus();
        if (typeof showFocusDock === 'function') showFocusDock();
      }
    }
  });
  rebuildSentenceTimeIndex();
  reportLibraryProgress(chNum, 0);
  updateMediaSessionMetadata();
  
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
    showToast('No audio available for this sentence');
    return;
  }
  if (shadowState.timer) clearTimeout(shadowState.timer);
  shadowState.phase = 'playing';
  shadowState.completed = 0;
  shadowState.pauseStartTime = 0;
  shadowState.sentence = sentenceEl;
  const btn = document.getElementById('repeatBtn') || document.getElementById('shadowBtn');
  if (btn) btn.textContent = 'Stop Repeat';
  requestShadowWakeLock();
  showToast('Shadowing loop active');
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
  audio.currentTime = start;
  safePlay(audio);
  globalPlayBtn.textContent = '⏸ Pause';
  sentenceEl.classList.add('active', 'card-collapsed');
}

function handleSentenceClick(event, id, start, end, hasMatch) {
  if (event && event.stopPropagation) event.stopPropagation();
  const el = document.getElementById(id);
  if (!el) return;
  
  const now = Date.now();
  const isDoubleTap = (lastSentenceClickId === id && (now - lastSentenceClickTime) < 350);
  lastSentenceClickTime = now;
  lastSentenceClickId = id;
  
  if (isDoubleTap && window.__HAS_AUDIO__) {
    startSentenceShadowing(el);
    return;
  }

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
    el.classList.add('card-collapsed');
  } else {
    el.classList.remove('card-collapsed');
  }

  currentPlayingId = id;

  // Instant 0ms first word highlight
  if (!el._cachedWords) {
    el._cachedWords = Array.from(el.querySelectorAll('.w'));
  }
  const firstWord = el._cachedWords[0];
  if (currentActiveWordEl && currentActiveWordEl !== firstWord) {
    currentActiveWordEl.classList.remove('active-word');
  }
  if (firstWord) {
    firstWord.classList.add('active-word');
    currentActiveWordEl = firstWord;
    currentActiveWordStart = parseFloat(firstWord.dataset.s) || start;
    currentActiveWordEnd = (el._cachedWords[1] ? parseFloat(el._cachedWords[1].dataset.s) : parseFloat(firstWord.dataset.e)) || (start + 0.3);
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
    audio.currentTime = start;
    safePlay(audio);
    if (globalPlayBtn) globalPlayBtn.textContent = '⏸ Pause';
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
        audio.currentTime = targetTime;
        safePlay(audio);
        if (globalPlayBtn) globalPlayBtn.textContent = '⏸ Pause';
        interpolated = true;
      } else if (prevTime !== null) {
        const dur = (audio && Number.isFinite(audio.duration)) ? audio.duration : Infinity;
        if (prevTime < dur - 3) {
          setUserSeeking(true, prevTime);
          audio.currentTime = prevTime;
          safePlay(audio);
          if (globalPlayBtn) globalPlayBtn.textContent = '⏸ Pause';
          interpolated = true;
        } else {
          showToast('Audio narration concluded; expanded bilingual study breakdown.');
          interpolated = true;
        }
      } else if (nextTime !== null) {
        setUserSeeking(true, 0);
        audio.currentTime = 0;
        safePlay(audio);
        if (globalPlayBtn) globalPlayBtn.textContent = '⏸ Pause';
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

const MAIN_REP_LEVELS = [1, 2, 3, 5];

function setMainRepetitions(n) {
  const nextRep = Math.max(1, parseInt(n, 10) || 1);
  shadowState.repetitions = nextRep;
  try {
    localStorage.setItem(STORAGE_PREFIX + 'repetitions', String(nextRep));
    localStorage.setItem('reader_focus_repetitions', String(nextRep));
  } catch(e) {}
  const repBtn = document.getElementById('repeatBtn') || document.getElementById('shadowBtn');
  if (repBtn) {
    if (nextRep === 1) {
      repBtn.textContent = 'Repeat';
      repBtn.classList.remove('active');
    } else {
      repBtn.textContent = `${nextRep}×`;
      repBtn.classList.add('active');
    }
  }
  const focusRepBtn = document.getElementById('focusRepBtn');
  if (focusRepBtn) {
    focusRepBtn.textContent = `${nextRep}×`;
  }
  if (nextRep === 1) {
    if (shadowState.phase !== 'idle') {
      stopShadowing();
    }
    showToast('Continuous reading mode active');
  } else {
    showToast(`Sentence repeat set to ${nextRep}×`);
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
}

function cycleMainRepeat(e) {
  if (e && e.stopPropagation) e.stopPropagation();
  const cur = shadowState.repetitions || 1;
  const idx = MAIN_REP_LEVELS.indexOf(cur);
  const nextRep = idx !== -1 ? MAIN_REP_LEVELS[(idx + 1) % MAIN_REP_LEVELS.length] : 1;
  setMainRepetitions(nextRep);
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
  const btn = document.getElementById('repeatBtn') || document.getElementById('shadowBtn');
  if (btn) {
    const cur = shadowState.repetitions || 1;
    if (cur === 1) {
      btn.textContent = 'Repeat';
      btn.classList.remove('active');
    } else {
      btn.textContent = `${cur}×`;
      btn.classList.add('active');
    }
  }
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
      currentActiveWordEl = null;
      currentActiveWordStart = -1;
      currentActiveWordEnd = -1;
      nextSentence.classList.add('active', 'card-collapsed');
      updateFocusStatus();
      updateFocusSentenceDisplay();
      if (autoScrollEnabled) {
        const rect = nextSentence.getBoundingClientRect();
        const inView = rect.top >= 90 && rect.bottom <= (window.innerHeight - 90);
        if (!inView) {
          nextSentence.scrollIntoView({ behavior: 'smooth', block: 'center' });
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
      currentActiveWordEl = null;
      currentActiveWordStart = -1;
      currentActiveWordEnd = -1;
      updateFocusStatus();
      updateFocusSentenceDisplay();
      shadowState.phase = 'pause_buffer';
      shadowState.pauseStartTime = Date.now();
      armShadowPauseWatchdog();
      nextSentence.classList.add('active', 'card-collapsed');
      if (autoScrollEnabled) {
        const rect = nextSentence.getBoundingClientRect();
        const inView = rect.top >= 90 && rect.bottom <= (window.innerHeight - 90);
        if (!inView) {
          nextSentence.scrollIntoView({ behavior: 'smooth', block: 'center' });
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
const FOCUS_REP_LEVELS = [1, 3, 5];
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
    const initialRepBtn = document.getElementById('repeatBtn') || document.getElementById('shadowBtn');
    if (initialRepBtn) {
      if (shadowState.repetitions > 1) {
        initialRepBtn.textContent = `${shadowState.repetitions}×`;
        initialRepBtn.classList.add('active');
      } else {
        initialRepBtn.textContent = 'Repeat';
        initialRepBtn.classList.remove('active');
      }
    }
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
  showToast(focusShowTrans ? 'Dual mode' : 'English only');
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
  showToast(`Sentence repeat set to ${nextRep}×`);
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
  currentActiveWordEl = null;
  currentActiveWordStart = -1;
  currentActiveWordEnd = -1;
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
    const rawVocab = el.querySelector('.inspect-vocab-list');
    if (rawVocab && rawVocab.children.length > 0) {
      vocabEl.innerHTML = rawVocab.innerHTML;
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
  showFocusDock();
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
  showFocusDock();
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
  showToast(focusBlindMode ? 'Audio mode ON (tap text to peek)' : 'Audio mode OFF');
}
const togglePocketBlindMode = toggleFocusBlindMode;


function handleFocusSentenceBoxClick(e) {
  if (e && e.stopPropagation) e.stopPropagation();
  showFocusDock();
  const box = document.getElementById('focusSentenceBox') || document.getElementById('pocketSentenceBox');
  if (focusBlindMode && box) {
    box.classList.toggle('revealed');
  } else {
    replayCurrentShadowSentence();
  }
}
const handlePocketSentenceBoxClick = handleFocusSentenceBoxClick;

function handleFocusTouchStart(e) {
  showFocusDock();
  if ((!focusModeActive && !pocketModeActive) || !e.touches || e.touches.length !== 1) return;
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
  if (focusDockHideTimer) {
    clearTimeout(focusDockHideTimer);
    focusDockHideTimer = null;
  }
  const dock = document.getElementById('focusDock');
  if (!dock) return;
  dock.classList.remove('dock-hidden');
  if (focusModeActive && audio && !audio.paused) {
    focusDockHideTimer = setTimeout(() => {
      if (focusModeActive && audio && !audio.paused) {
        dock.classList.add('dock-hidden');
      }
    }, 3000);
  }
}

function showFocusDock() {
  const dock = document.getElementById('focusDock');
  if (dock) dock.classList.remove('dock-hidden');
  scheduleFocusDockHide();
}

function toggleFocusMode(force) {
  const overlay = document.getElementById('focus-overlay') || document.getElementById('pocket-overlay');
  if (!overlay) return;
  
  const target = typeof force === 'boolean' ? force : !focusModeActive;
  focusModeActive = target;
  pocketModeActive = target;
  currentActiveWordEl = null;
  currentActiveWordStart = -1;
  currentActiveWordEnd = -1;
  if (focusSingleTapTimer) {
    clearTimeout(focusSingleTapTimer);
    focusSingleTapTimer = null;
  }
  
  if (focusModeActive) {
    initFocusPreferences();
    showFocusDock();
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

function handleFocusOverlayClick(e) {
  if (e && e.target && (
    e.target.closest('#focusDock') ||
    e.target.closest('.focus-close-icon') || e.target.closest('.pocket-close-icon')
  )) {
    return;
  }
  showFocusDock();
  const now = Date.now();
  if (now - lastFocusTapTime < 450) {
    toggleFocusMode(false);
    lastFocusTapTime = 0;
  } else {
    lastFocusTapTime = now;
  }
}
const handlePocketOverlayClick = handleFocusOverlayClick;

window.toggleFocusMode = toggleFocusMode;
window.togglePocketMode = toggleFocusMode;
window.toggleFocusPlayPause = toggleFocusPlayPause;
window.updateFocusPlayBtn = updateFocusPlayBtn;
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
  if (audio && audio.playbackRate !== currentPlaybackSpeed) {
    audio.playbackRate = currentPlaybackSpeed;
  }
  if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'playing';
  updateMediaSessionMetadata();
  startSyncLoop();
  if (focusModeActive) {
    scheduleFocusDockHide();
  }
});
audio.addEventListener('pause', () => {
  globalPlayBtn.textContent = '▶ Play';
  if ('mediaSession' in navigator) navigator.mediaSession.playbackState = 'paused';
  stopSyncLoop();
  if (focusModeActive) {
    showFocusDock();
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
  if (audio) audio.playbackRate = currentPlaybackSpeed;
  updateAudioPlayerUI();
});
audio.addEventListener('durationchange', updateAudioPlayerUI);
audio.addEventListener('seeked', () => {
  setUserSeeking(false);
});
let audioStallTimer = null;
audio.addEventListener('waiting', () => {
  if (audio && !audio.paused) {
    if (audioStallTimer) clearTimeout(audioStallTimer);
    audioStallTimer = setTimeout(() => {
      if (audio && !audio.paused && audio.readyState < 3) {
        console.warn('[Audio] Buffering stall detected, refreshing buffer...');
        const cur = audio.currentTime;
        audio.currentTime = cur;
        safePlay(audio);
      }
    }, 2500);
  }
});
audio.addEventListener('playing', () => {
  if (audioStallTimer) {
    clearTimeout(audioStallTimer);
    audioStallTimer = null;
  }
});
audio.addEventListener('stalled', () => {
  if (audio && !audio.paused && audio.readyState < 3) {
    if (!audioStallTimer) {
      audioStallTimer = setTimeout(() => {
        if (audio && !audio.paused && audio.readyState < 3) {
          const cur = audio.currentTime;
          audio.currentTime = cur;
          safePlay(audio);
        }
      }, 3000);
    }
  }
});
audio.addEventListener('error', (err) => {
  console.warn('[Audio] Media playback error encountered:', err);
  if (globalPlayBtn) globalPlayBtn.textContent = '▶ Play';
  if (typeof updateFocusPlayBtn === 'function') updateFocusPlayBtn(false);
  showToast('Audio network error. Reconnecting...');
  if (audio.src) {
    const cur = audio.currentTime;
    audio.load();
    audio.currentTime = cur;
  }
});
audio.addEventListener('ended', () => {
  if (focusModeActive) {
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
    if (shadowState.phase !== 'idle' && audio && !audio.paused) {
      const curSentence = findSentenceAt(audio.currentTime);
      if (curSentence && curSentence !== shadowState.sentence) {
        if (shadowState.sentence) shadowState.sentence.classList.remove('active', 'card-collapsed');
        shadowState.sentence = curSentence;
        shadowState.completed = 0;
        shadowState.phase = 'playing';
        curSentence.classList.add('active', 'card-collapsed');
        if (autoScrollEnabled) {
          curSentence.scrollIntoView({ behavior: 'smooth', block: 'center' });
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
    if (now - lastSyncTimestamp >= 25) {
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
            currentActiveWordStart = -1;
            currentActiveWordEnd = -1;
            try { localStorage.setItem(STORAGE_PREFIX + 'last_sentence_c' + activeChapterNum, activeUnit.id); } catch(e) {}
            
            currentActiveSection.querySelectorAll('.sentence-unit.active').forEach(u => {
              if (u !== activeUnit) u.classList.remove('active', 'card-collapsed');
            });
            activeUnit.classList.add('active', 'card-collapsed');

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
                if (!inView && typeof activeUnit.scrollIntoView === 'function') {
                  activeUnit.scrollIntoView({ behavior: 'smooth', block: 'center' });
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
              const we = (i < wordEls.length - 1) ? parseFloat(wordEls[i + 1].dataset.s) : parseFloat(w.dataset.e);
              if (curTime >= ws && curTime < we) {
                foundWord = w;
                foundIndex = i;
                foundStart = ws;
                foundEnd = we;
                break;
              }
            }
            
            if (foundWord !== currentActiveWordEl) {
              if (currentActiveWordEl) currentActiveWordEl.classList.remove('active-word');
              if (foundWord) foundWord.classList.add('active-word');
              currentActiveWordEl = foundWord;
              if (focusModeActive || pocketModeActive) {
                const pText = document.getElementById('focusSentenceText') || document.getElementById('pocketSentenceText');
                if (pText) {
                  const prevW = pText.querySelector('.w.active-word');
                  if (prevW) prevW.classList.remove('active-word');
                  if (foundIndex >= 0) {
                    if (!pText._cachedFocusWords) {
                      pText._cachedFocusWords = Array.from(pText.querySelectorAll('.w'));
                    }
                    const focusWord = pText._cachedFocusWords[foundIndex];
                    if (focusWord && !focusWord.classList.contains('active-word')) {
                      focusWord.classList.add('active-word');
                    }
                  }
                }
              }
            }
            currentActiveWordStart = foundStart;
            currentActiveWordEnd = foundEnd;
          }
        } else {
          if (currentActiveWordEl) {
            currentActiveWordEl.classList.remove('active-word');
            currentActiveWordEl = null;
          }
          currentActiveWordStart = -1;
          currentActiveWordEnd = -1;
          if (focusModeActive || pocketModeActive) {
            const pText = document.getElementById('focusSentenceText') || document.getElementById('pocketSentenceText');
            if (pText) {
              const prevW = pText.querySelector('.w.active-word');
              if (prevW) prevW.classList.remove('active-word');
            }
          }
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

  if (focusModeActive || pocketModeActive) {
    showFocusDock();
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
          safePlay(audio);
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
          safePlay(audio);
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
initMediaSession();
updateMediaSessionMetadata();
const focusOverlayEl = document.getElementById('focus-overlay');
if (focusOverlayEl) {
  focusOverlayEl.addEventListener('dblclick', handleFocusDblClick);
  focusOverlayEl.addEventListener('pointermove', () => {
    if (focusModeActive) scheduleFocusDockHide();
  });
  focusOverlayEl.addEventListener('pointerdown', () => {
    if (focusModeActive) showFocusDock();
  });
}
const focusDockEl = document.getElementById('focusDock');
if (focusDockEl) {
  focusDockEl.addEventListener('pointerdown', () => {
    showFocusDock();
  });
}
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
