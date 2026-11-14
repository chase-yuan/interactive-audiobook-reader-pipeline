import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

sound_samples_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs', 'sound_samples.json')
if os.path.exists(sound_samples_file):
    with open(sound_samples_file, 'r', encoding='utf-8') as sf:
        sound_samples_json = sf.read()
else:
    sound_samples_json = "{}"

proto_code = f"""
<!-- PROTOTYPE V15: Big-Tech Global Declarative Projection, Studio Mechanical Audio, Zero Visual Pollution -->
<style>
/* 1. Global Typing Sandbox Isolation - Kill all background highlights, blue boxes & grey bars (AP1 & AP4) */
body.typing-mode-active .sentence-unit,
body.typing-mode-active .sentence-unit.active,
body.typing-mode-active .sentence-unit.card-collapsed,
body.typing-mode-active .sentence-unit .w,
body.typing-mode-active .sentence-unit .w.active-word,
body.typing-mode-active .sentence-unit .w.active,
body.typing-mode-active .sentence-text {{
  background: transparent !important;
  background-color: transparent !important;
  box-shadow: none !important;
  border-radius: 0 !important;
}}

/* Top Chapter Progress Bar - Tokenized (AP2) */
#typingChapterProgressBar {{
  position: fixed;
  top: 0;
  left: 0;
  height: 2.5px;
  background: var(--accent);
  z-index: 10001;
  transition: width var(--transition-base);
  width: 0%;
  pointer-events: none;
}}

/* Bottom Control Dock - Slide-Down Tuck in Typing Mode (Zero Collision) */
.bottom-control-dock.dock-typing-hidden {{
  transform: translateY(140%) !important;
  opacity: 0 !important;
  pointer-events: none !important;
  transition: transform 0.35s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.25s ease !important;
}}

/* Bottom Floating Status Bar - Seamless Tokenized Glassmorphic Pill (AP1) */
.in-situ-hud {{
  position: fixed;
  bottom: calc(var(--space-base, 16px) + env(safe-area-inset-bottom, 16px));
  left: 50%;
  transform: translateX(-50%) translateY(0);
  z-index: 9999;
  background: var(--bg-panel-glass, rgba(255, 255, 255, 0.92));
  color: var(--text-main, #1a1a1a);
  border: 1px solid var(--border-subtle, rgba(0, 0, 0, 0.08));
  border-radius: var(--radius-pill, 24px);
  padding: 4px 14px;
  font-size: var(--font-size-xs, 0.72rem);
  font-family: var(--font-sans);
  font-weight: 500;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.24);
  display: none;
  align-items: center;
  justify-content: center;
  gap: 6px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  user-select: none;
  max-width: min(var(--dock-max-width, 676px), calc(100vw - 32px));
  white-space: nowrap;
  transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1),
              opacity 0.28s cubic-bezier(0.16, 1, 0.3, 1);
}}
.in-situ-hud.visible {{
  display: flex;
}}
.in-situ-hud.hud-idle-hidden {{
  transform: translateX(-50%) translateY(calc(100% + 36px));
  opacity: 0;
  pointer-events: none;
}}

/* CapsLock Indicator - Clean Micro-Badge (AP0 & AP3) */
#capsLockBadge {{
  display: none;
  background: var(--text-sub, #666666);
  color: var(--bg-page, #ffffff);
  font-size: 10px;
  font-weight: 700;
  padding: 1px 5px;
  border-radius: var(--radius-xs, 3px);
  letter-spacing: 0.5px;
}}

/* Progress Tag */
.hud-progress-tag {{
  color: var(--accent);
  font-size: var(--font-size-xs, 0.72rem);
  font-weight: 700;
  padding: 0 4px;
}}

/* Metrics Tag */
#hudMetrics {{
  color: var(--text-sub, #666666);
  font-size: var(--font-size-xs, 0.72rem);
  font-variant-numeric: tabular-nums;
  padding: 0 4px;
}}

/* Buttons in HUD - Seamless Tokenized (AP2 & AP3) */
.hud-btn {{
  background: transparent;
  color: var(--text-main, #1a1a1a);
  border: 1px solid var(--border-subtle, rgba(0, 0, 0, 0.08));
  border-radius: var(--radius-pill, 20px);
  padding: 2px 10px;
  font-size: var(--font-size-xs, 0.72rem);
  font-family: var(--font-sans);
  cursor: pointer;
  font-weight: 600;
  transition: all var(--transition-fast);
  display: inline-flex;
  align-items: center;
}}
.hud-btn:hover {{
  background: var(--bg-hover);
  border-color: var(--border);
}}
.hud-btn.active-toggle {{
  background: rgba(88, 166, 255, 0.14) !important;
  color: var(--accent) !important;
  border-color: rgba(88, 166, 255, 0.35) !important;
  font-weight: 600;
}}
[data-theme="light"] .hud-btn.active-toggle,
[data-theme="sepia"] .hud-btn.active-toggle {{
  background: rgba(9, 105, 218, 0.09) !important;
  color: var(--accent) !important;
  border-color: rgba(9, 105, 218, 0.28) !important;
}}
.hud-btn.active-toggle:hover {{
  background: rgba(88, 166, 255, 0.24) !important;
}}
[data-theme="light"] .hud-btn.active-toggle:hover,
[data-theme="sepia"] .hud-btn.active-toggle:hover {{
  background: rgba(9, 105, 218, 0.15) !important;
}}

/* Zero-Layout-Shift (ZLS) Word & Typography Guard (AP0 & AP4) */
body.typing-mode-active .sentence-unit .w {{
  display: inline;
  white-space: nowrap !important;
  font-kerning: normal;
  letter-spacing: normal;
}}

/* Character-Level Feedback - Big Tech Zero-Displacement Standard */
/* 1. Completed characters & words: Pure Radiant Emerald Green */
.twc-correct {{
  color: #10b981 !important;
  display: inline;
  font-family: inherit;
  font-size: inherit;
  font-weight: inherit;
  line-height: inherit;
  margin: 0;
  padding: 0;
  border: none;
}}

/* 2. Active sentence pending characters & words: 100% stable font weight & color */
.twc-active-pending {{
  color: var(--text-main, #ffffff) !important;
  display: inline;
  font-family: inherit;
  font-size: inherit;
  font-weight: inherit;
  line-height: inherit;
  margin: 0;
  padding: 0;
  border: none;
}}

/* 3. Unstarted sentences: Natural book typography */
.twc-unstarted {{
  color: inherit;
  display: inline;
}}

/* 4. Active Typing Caret / Cursor - Strictly Inline, GPU Painted, Zero Layout Shift */
.twc-cursor {{
  position: relative;
  display: inline;
  color: var(--text-main, #ffffff) !important;
  box-shadow: inset 0 -2.5px 0 0 var(--accent);
  font-family: inherit;
  font-size: inherit;
  font-weight: inherit;
  line-height: inherit;
  margin: 0;
  padding: 0;
  border: none;
}}

/* Vertical Bar Caret (Monkeytype / Apple Standard) */
.twc-cursor::before {{
  content: "";
  position: absolute;
  left: -1px;
  top: 10%;
  bottom: 10%;
  width: 2px;
  background-color: var(--accent);
  border-radius: 1px;
  animation: twc-caret-blink 1.05s ease-in-out infinite;
  pointer-events: none;
  z-index: 2;
}}

/* Trailing Caret when waiting for Spacebar */
.twc-caret-space {{
  position: relative;
  display: inline;
}}
.twc-caret-space::after {{
  content: "";
  position: absolute;
  right: -2px;
  top: 10%;
  bottom: 10%;
  width: 2px;
  background-color: var(--accent);
  border-radius: 1px;
  animation: twc-caret-blink 1.05s ease-in-out infinite;
  pointer-events: none;
  z-index: 2;
}}

@keyframes twc-caret-blink {{
  0%, 45% {{ opacity: 1; }}
  50%, 95% {{ opacity: 0; }}
  100% {{ opacity: 1; }}
}}

/* Masked Dictation Characters (Zero Layout Shift) */
.twc-masked {{
  position: relative;
  display: inline;
  padding: 0 1px;
  box-shadow: inset 0 -2px 0 0 var(--border-subtle, rgba(255,255,255,0.25));
  color: transparent !important;
  user-select: none;
}}
.twc-masked-cursor {{
  position: relative;
  display: inline;
  padding: 0 1px;
  box-shadow: inset 0 -2.5px 0 0 var(--accent);
  background: rgba(88, 166, 255, 0.16);
  color: transparent !important;
}}
.twc-masked-cursor::before {{
  content: "";
  position: absolute;
  left: 0;
  top: 10%;
  bottom: 10%;
  width: 2px;
  background-color: var(--accent);
  border-radius: 1px;
  animation: twc-caret-blink 1.05s ease-in-out infinite;
  pointer-events: none;
  z-index: 2;
}}

/* Cloze Mode: Underline Slot (Zero Layout Shift) */
.twc-cloze-slot-char {{
  position: relative;
  display: inline;
  padding: 0 2px;
  box-shadow: inset 0 -2px 0 0 var(--border-subtle, rgba(255,255,255,0.3));
  color: transparent !important;
  user-select: none;
}}
.twc-cloze-cursor-char {{
  position: relative;
  display: inline;
  padding: 0 2px;
  box-shadow: inset 0 -2.5px 0 0 var(--accent);
  background: rgba(88, 166, 255, 0.16);
  color: transparent !important;
}}
.twc-cloze-cursor-char::before {{
  content: "";
  position: absolute;
  left: 0;
  top: 10%;
  bottom: 10%;
  width: 2px;
  background-color: var(--accent);
  border-radius: 1px;
  animation: twc-caret-blink 1.05s ease-in-out infinite;
  pointer-events: none;
  z-index: 2;
}}

/* Error Feedback: Crimson Inset Glow (AP4 Compliant, Zero Disruption) */
.twc-error-shake {{
  color: var(--btn-danger-bg, #ef4444) !important;
  box-shadow: inset 0 -2.5px 0 0 var(--btn-danger-bg, #ef4444) !important;
  transition: color 0.05s ease;
}}

/* Hint Flash Glow */
.twc-hint-glow {{
  color: var(--accent) !important;
  box-shadow: inset 0 -2.5px 0 0 var(--accent) !important;
  transition: color 0.2s ease;
}}

/* Hidden Input for Mobile / Tablet Virtual Keyboard */
.twc-hidden-input {{
  position: fixed;
  top: -9999px;
  left: -9999px;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
  border: none;
  outline: none;
  background: transparent;
  z-index: -1;
}}

/* Cloze Target Vocab Highlight in Marginalia */
.vocab-row.target-active-vocab {{
  border-left: 3px solid var(--accent, #3b82f6) !important;
  background: var(--bg-hover, rgba(59, 130, 246, 0.08)) !important;
  padding-left: 8px !important;
  border-radius: 4px !important;
  transition: all 0.2s ease !important;
}}

/* Chapter Complete Modal */
.typing-complete-overlay {{
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  z-index: 10002;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s ease;
}}
.typing-complete-overlay.visible {{
  opacity: 1;
  pointer-events: auto;
}}
.typing-complete-card {{
  background: var(--bg-card, #ffffff);
  border: 1px solid var(--border, #e2e8f0);
  border-radius: 18px;
  padding: 32px 36px;
  max-width: 440px;
  width: 90%;
  text-align: center;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.28);
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 0.3s ease, transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
}}
.typing-complete-overlay.visible .typing-complete-card {{
  opacity: 1;
  transform: translateY(0);
}}
.tc-badge {{
  display: inline-block;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  margin-bottom: 12px;
}}
.tc-title {{
  margin: 0 0 4px 0;
  font-size: 24px;
  font-weight: 700;
  color: var(--text-main, #1e293b);
  letter-spacing: -0.02em;
}}
.tc-subtitle {{
  margin: 0 0 24px 0;
  font-size: 14px;
  color: var(--text-secondary, #64748b);
}}
.tc-stats-grid {{
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}}
.tc-stat-box {{
  background: var(--bg-hover, rgba(148, 163, 184, 0.08));
  border-radius: 12px;
  padding: 14px 10px;
}}
.tc-stat-val {{
  display: block;
  font-size: 22px;
  font-weight: 800;
  color: var(--text-main, #1e293b);
  line-height: 1.2;
}}
.tc-stat-label {{
  display: block;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-secondary, #64748b);
  margin-top: 4px;
}}
.tc-actions {{
  display: flex;
  flex-direction: column;
  gap: 10px;
}}
.tc-btn {{
  width: 100%;
  padding: 12px 18px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s ease;
  border: none;
}}
.tc-btn-primary {{
  background: var(--accent, #3b82f6);
  color: #ffffff;
}}
.tc-btn-primary:hover {{
  opacity: 0.9;
  transform: translateY(-1px);
}}
.tc-btn-secondary {{
  background: transparent;
  color: var(--text-secondary, #64748b);
  border: 1px solid var(--border, #e2e8f0);
}}
.tc-btn-secondary:hover {{
  background: var(--bg-hover, rgba(148, 163, 184, 0.08));
  color: var(--text-main, #1e293b);
}}
</style>

<!-- Top Chapter Progress Bar -->
<div id="typingChapterProgressBar"></div>

<!-- Virtual Keyboard Input Bridge (Mobile/iPad Seamless Soft-Keyboard Summon) -->
<input type="text" id="typingHiddenInput" class="twc-hidden-input" autocomplete="off" autocapitalize="none" spellcheck="false" autocorrect="off" aria-hidden="true" tabindex="-1">

<!-- Chapter Complete Celebration Modal -->
<div id="typingCompleteModal" class="typing-complete-overlay" onclick="closeChapterCompleteModal()">
  <div class="typing-complete-card" onclick="event.stopPropagation()">
    <div class="tc-badge">Chapter Complete</div>
    <h2 class="tc-title">Practice Finished</h2>
    <p class="tc-subtitle">Misbehaving · Chapter 1</p>
    <div class="tc-stats-grid">
      <div class="tc-stat-box">
        <span class="tc-stat-val" id="tcFinalWpm">0</span>
        <span class="tc-stat-label">WPM</span>
      </div>
      <div class="tc-stat-box">
        <span class="tc-stat-val" id="tcFinalAcc">100%</span>
        <span class="tc-stat-label">Accuracy</span>
      </div>
      <div class="tc-stat-box">
        <span class="tc-stat-val" id="tcFinalTime">0:00</span>
        <span class="tc-stat-label">Time</span>
      </div>
      <div class="tc-stat-box">
        <span class="tc-stat-val" id="tcFinalSentences">0 / 0</span>
        <span class="tc-stat-label">Sentences</span>
      </div>
    </div>
    <div class="tc-actions">
      <button class="tc-btn tc-btn-primary" onclick="restartChapterTyping()">Practice Again</button>
      <button class="tc-btn tc-btn-secondary" onclick="closeChapterCompleteModal(true)">Return to Reading</button>
    </div>
  </div>
</div>

<!-- Bottom Minimal HUD (Streamlined 1-Row Layout, Auto-Align & Auto-Hide) -->
<div id="inSituHud" class="in-situ-hud">
  <button id="typingSubModeBtn" class="hud-btn active-toggle" onclick="cycleTypingSubMode()" title="Cycle mode: Type / Blind / Cloze">Mode: Type</button>
  <span id="capsLockBadge">CAPS</span>
  <span id="hudProgressTag" class="hud-progress-tag">1 / --</span>
  <span id="hudMetrics">0 WPM · 100% ACC</span>
  
  <button id="hudPlayPauseBtn" class="hud-btn" onclick="toggleTypingAudioPlayPause()" title="Play / Pause active sentence audio [Tab]">Pause</button>
  <button id="hudLoopBtn" class="hud-btn" onclick="cycleMainRepeat()" title="Cycle sentence repeat: Off / 2× / 3× / ∞ [Ctrl+L]">Loop: Off</button>
  <button id="soundProfileBtn" class="hud-btn" onclick="cycleSoundProfile()" title="Cycle keyboard sound profiles with preview">Sound: Thock</button>
  <button id="transToggleBtn" class="hud-btn active-toggle" onclick="toggleTranslationVisibility()" title="Toggle marginalia translation side notes [T]">Trans: On</button>
  <button class="hud-btn" onclick="setTypingMode('off')" title="Exit typing mode [Esc]">Exit</button>
</div>

<script>
(function() {{
  // Default is Companion / Reading mode!
  window.__TYPING_MODE__ = 'off';

  // Sub-modes: In-situ Type, Blind Dictation, Hard-word Cloze
  const SUB_MODES = [
    {{ id: 'insitu', label: 'Mode: Type' }},
    {{ id: 'dictation', label: 'Mode: Blind' }},
    {{ id: 'cloze', label: 'Mode: Cloze' }}
  ];
  let currentSubModeIdx = 0;
  const savedSubMode = localStorage.getItem('typing_sub_mode') || 'insitu';
  const foundSubIdx = SUB_MODES.findIndex(m => m.id === savedSubMode);
  if (foundSubIdx !== -1) currentSubModeIdx = foundSubIdx;

  // 1. Studio Acoustic Sound Engine: Authentic Sampled Mechanical Switches (Monkeytype Standard)
  const __SOUND_SAMPLES__ = {sound_samples_json};

  const SOUND_PROFILES = [
    {{ id: 'thock', name: 'Thock (NK Creams)' }},
    {{ id: 'clicky', name: 'Clicky (MX Blue)' }},
    {{ id: 'typewriter', name: 'Typewriter' }},
    {{ id: 'laptop', name: 'Laptop' }},
    {{ id: 'pop', name: 'Bubble Pop' }},
    {{ id: 'mute', name: 'Mute' }}
  ];

  let currentSoundProfileIdx = 0;
  const savedProfile = localStorage.getItem('typing_sound_profile') || 'thock';
  const foundIdx = SOUND_PROFILES.findIndex(p => p.id === savedProfile);
  if (foundIdx !== -1) currentSoundProfileIdx = foundIdx;

  const SoundEngine = {{
    ctx: null,
    decodedBuffers: {{}},
    init() {{
      if (!this.ctx) {{
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) this.ctx = new AudioCtx();
      }}
      if (this.ctx && this.ctx.state === 'suspended') {{
        this.ctx.resume();
      }}
    }},
    async getBuffer(profileId, index) {{
      this.init();
      if (!this.ctx) return null;
      const key = `${{profileId}}_${{index}}`;
      if (this.decodedBuffers[key]) return this.decodedBuffers[key];
      const samples = (typeof __SOUND_SAMPLES__ !== 'undefined') ? __SOUND_SAMPLES__[profileId] : null;
      if (!samples || !samples[index]) return null;
      try {{
        const b64 = samples[index];
        const binary = atob(b64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
        const audioBuffer = await this.ctx.decodeAudioData(bytes.buffer);
        this.decodedBuffers[key] = audioBuffer;
        return audioBuffer;
      }} catch (err) {{
        return null;
      }}
    }},
    async preloadProfile(profileId) {{
      if (profileId === 'mute') return;
      this.init();
      if (!this.ctx) return;
      const samples = (typeof __SOUND_SAMPLES__ !== 'undefined') ? __SOUND_SAMPLES__[profileId] : null;
      if (!samples) return;
      for (let i = 0; i < samples.length; i++) {{
        this.getBuffer(profileId, i).catch(() => {{}});
      }}
    }},
    async playKeystroke(profileId, isSpace) {{
      if (profileId === 'mute') return;
      this.init();
      if (!this.ctx) return;
      const samples = (typeof __SOUND_SAMPLES__ !== 'undefined') ? __SOUND_SAMPLES__[profileId] : null;
      if (!samples || samples.length === 0) return;
      const idx = Math.floor(Math.random() * samples.length);
      const buffer = await this.getBuffer(profileId, idx);
      if (!buffer) return;
      const source = this.ctx.createBufferSource();
      source.buffer = buffer;
      const baseRate = isSpace ? 0.84 : 1.0;
      source.playbackRate.value = baseRate * (0.97 + Math.random() * 0.06);
      
      const gain = this.ctx.createGain();
      gain.gain.value = isSpace ? 0.95 : 0.82;
      source.connect(gain);
      gain.connect(this.ctx.destination);
      source.start(0);
    }},
    play(isSpace = false) {{
      const profile = SOUND_PROFILES[currentSoundProfileIdx];
      if (!profile || profile.id === 'mute') return;
      this.playKeystroke(profile.id, isSpace);
    }},
    preview(profileId) {{
      this.playKeystroke(profileId, false);
    }},
    error() {{
      const profile = SOUND_PROFILES[currentSoundProfileIdx];
      if (profile && profile.id === 'mute') return;
      this.init();
      if (!this.ctx) return;
      const t = this.ctx.currentTime;
      const osc = this.ctx.createOscillator();
      const gain = this.ctx.createGain();
      osc.type = 'sine';
      osc.frequency.setValueAtTime(140, t);
      osc.frequency.exponentialRampToValueAtTime(60, t + 0.08);
      gain.gain.setValueAtTime(0.2, t);
      gain.gain.exponentialRampToValueAtTime(0.001, t + 0.08);
      osc.connect(gain);
      gain.connect(this.ctx.destination);
      osc.start(t);
      osc.stop(t + 0.08);
    }},
    chime() {{
      const profile = SOUND_PROFILES[currentSoundProfileIdx];
      if (profile && profile.id === 'mute') return;
      this.init();
      if (!this.ctx) return;
      const notes = [523.25, 659.25, 783.99]; // C5, E5, G5
      notes.forEach((freq, idx) => {{
        const t = this.ctx.currentTime + idx * 0.055;
        const osc = this.ctx.createOscillator();
        const gain = this.ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(freq, t);
        gain.gain.setValueAtTime(0.09, t);
        gain.gain.exponentialRampToValueAtTime(0.001, t + 0.16);
        osc.connect(gain);
        gain.connect(this.ctx.destination);
        osc.start(t);
        osc.stop(t + 0.16);
      }});
    }}
  }};

  // Play / Pause Toggle for Typing Mode Audio
  window.toggleTypingAudioPlayPause = function() {{
    if (!audio) return;
    if (audio.paused) {{
      if (activeSentenceEl) {{
        const start = parseFloat(activeSentenceEl.dataset.start);
        const end = parseFloat(activeSentenceEl.dataset.end);
        if (isNaN(audio.currentTime) || audio.currentTime >= end || audio.currentTime < start) {{
          audio.currentTime = start;
        }}
      }}
      audio.play().catch(() => {{}});
    }} else {{
      audio.pause();
    }}
    window.updateHudPlayPauseBtn();
  }};

  window.updateHudPlayPauseBtn = function() {{
    const btn = document.getElementById('hudPlayPauseBtn');
    if (!btn) return;
    const isPlaying = audio && !audio.paused;
    btn.textContent = isPlaying ? 'Pause' : 'Play';
    btn.classList.toggle('active-toggle', isPlaying);
  }};

  if (audio) {{
    audio.addEventListener('play', () => {{
      if (typeof window.updateHudPlayPauseBtn === 'function') window.updateHudPlayPauseBtn();
    }});
    audio.addEventListener('pause', () => {{
      if (typeof window.updateHudPlayPauseBtn === 'function') window.updateHudPlayPauseBtn();
    }});
  }}

  // 2. Marginalia Side Note Translation State & Targeted Cloze Glossing
  let showTranslation = localStorage.getItem('typing_show_trans') !== 'false';

  function updateMarginaliaState() {{
    if (window.__TYPING_MODE__ === 'off') return;
    if (showTranslation && activeSentenceEl) {{
      if (typeof showMarginaliaForSentence === 'function') {{
        showMarginaliaForSentence(activeSentenceEl, true);

        // Targeted Glossing: Highlight active vocabulary target in Cloze mode
        if (window.__TYPING_MODE__ === 'cloze' && currentWordIdx < wordItems.length) {{
          const item = wordItems[currentWordIdx];
          const vocabRows = document.querySelectorAll('#marginaliaVocab .vocab-row');
          if (item && item.isClozeTarget) {{
            vocabRows.forEach(row => {{
              const wordSpan = row.querySelector('.v-word');
              const vText = wordSpan ? wordSpan.textContent.trim().toLowerCase() : '';
              if (vText && (isVocabMatch(item.cleanWord, vText) || vText.includes(item.cleanWord.toLowerCase()))) {{
                row.classList.add('target-active-vocab');
              }} else {{
                row.classList.remove('target-active-vocab');
              }}
            }});
          }} else {{
            vocabRows.forEach(row => row.classList.remove('target-active-vocab'));
          }}
        }}
      }}
    }} else {{
      if (typeof hideMarginalia === 'function') {{
        hideMarginalia();
      }}
    }}
  }}

  // =========================================================================
  // TYPING HUD AUTO-HIDE ENGINE (Pure Focus & Ergonomic Bottom Strip Hover)
  // Automatically conceals HUD while typing, reveals smoothly when hovering near bottom
  // =========================================================================
  let typingHudIdleTimer = null;
  const TYPING_HUD_IDLE_DELAY = 2400;

  function scheduleTypingHudHide(immediate = false) {{
    if (typingHudIdleTimer) {{
      clearTimeout(typingHudIdleTimer);
      typingHudIdleTimer = null;
    }}
    const hud = document.getElementById('inSituHud');
    if (!hud || window.__TYPING_MODE__ === 'off') return;
    if (hud._isMouseOver) return;

    if (immediate) {{
      hud.classList.add('hud-idle-hidden');
      return;
    }}

    typingHudIdleTimer = setTimeout(() => {{
      const h = document.getElementById('inSituHud');
      if (!h || window.__TYPING_MODE__ === 'off' || h._isMouseOver) return;
      h.classList.add('hud-idle-hidden');
    }}, TYPING_HUD_IDLE_DELAY);
  }}

  function showTypingHud() {{
    if (window.__TYPING_MODE__ === 'off') return;
    const hud = document.getElementById('inSituHud');
    if (!hud) return;
    hud.classList.remove('hud-idle-hidden');
    scheduleTypingHudHide(false);
  }}

  // Pointer move near bottom activation strip (bottom 80px) reveals HUD
  document.addEventListener('pointermove', function(e) {{
    if (window.__TYPING_MODE__ === 'off') return;
    const isNearBottom = (typeof e.clientY === 'number') && (e.clientY >= window.innerHeight - 80);
    const hud = document.getElementById('inSituHud');
    const isOverHud = Boolean(hud && hud._isMouseOver);
    if (isNearBottom || isOverHud) {{
      showTypingHud();
    }}
  }});

  const hudEl = document.getElementById('inSituHud');
  if (hudEl) {{
    hudEl.addEventListener('mouseenter', () => {{
      hudEl._isMouseOver = true;
      if (typingHudIdleTimer) {{
        clearTimeout(typingHudIdleTimer);
        typingHudIdleTimer = null;
      }}
      hudEl.classList.remove('hud-idle-hidden');
    }});
    hudEl.addEventListener('mouseleave', () => {{
      hudEl._isMouseOver = false;
      scheduleTypingHudHide(false);
    }});
  }}

  // 3. Zero-Jitter Smart Scroll: Only scrolls if the sentence is truly outside comfortable reading bounds!
  function smartScrollIntoView(el) {{
    if (!el) return;
    const rect = el.getBoundingClientRect();
    // Comfortable reading zone: 100px from top, 140px above bottom dock
    const isComfortablyVisible = (rect.top >= 100 && rect.bottom <= (window.innerHeight - 140));
    if (!isComfortablyVisible) {{
      el.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}
  }}

  // Intercept background performAutoScroll to eliminate double-bounce jitter in Typing Mode
  const originalPerformAutoScroll = window.performAutoScroll;
  window.performAutoScroll = function(element) {{
    if (window.__TYPING_MODE__ && window.__TYPING_MODE__ !== 'off') {{
      return; // Absolute zero jitter: typing engine manages viewport via smartScrollIntoView exclusively
    }}
    if (typeof originalPerformAutoScroll === 'function') {{
      return originalPerformAutoScroll.apply(this, arguments);
    }}
  }};

  window.cycleTypingSubMode = function() {{
    currentSubModeIdx = (currentSubModeIdx + 1) % SUB_MODES.length;
    const subMode = SUB_MODES[currentSubModeIdx];
    localStorage.setItem('typing_sub_mode', subMode.id);
    
    const btn = document.getElementById('typingSubModeBtn');
    if (btn) btn.textContent = subMode.label;

    window.__TYPING_MODE__ = subMode.id;
    if (activeSentenceEl) {{
      buildWordItems(activeSentenceEl);
      if (window.__TYPING_MODE__ === 'cloze') {{
        ensureValidClozeIndex();
        saveSentenceState(activeSentenceEl.id);
      }}
    }}
    projectDocumentTypingState();
  }};

  function ensureValidClozeIndex() {{
    if (window.__TYPING_MODE__ !== 'cloze') return;
    const hasAnyTarget = wordItems.some(w => w.isClozeTarget);
    if (!hasAnyTarget) {{
      currentWordIdx = wordItems.length;
      inWordCharIdx = 0;
      waitingForSpace = false;
      return;
    }}
    const state = activeSentenceEl ? sentenceProgressLedger.get(activeSentenceEl.id) : null;
    if (state && state.completed && currentWordIdx >= wordItems.length) {{
      return;
    }}
    if (currentWordIdx >= wordItems.length || !wordItems[currentWordIdx]?.isClozeTarget) {{
      const nextTarget = wordItems.findIndex((w, idx) => idx >= currentWordIdx && w.isClozeTarget);
      if (nextTarget !== -1) {{
        currentWordIdx = nextTarget;
      }} else {{
        const firstTarget = wordItems.findIndex(w => w.isClozeTarget);
        currentWordIdx = firstTarget !== -1 ? firstTarget : 0;
      }}
      inWordCharIdx = 0;
      waitingForSpace = false;
    }}
  }}

  window.cycleSoundProfile = function() {{
    currentSoundProfileIdx = (currentSoundProfileIdx + 1) % SOUND_PROFILES.length;
    const profile = SOUND_PROFILES[currentSoundProfileIdx];
    localStorage.setItem('typing_sound_profile', profile.id);
    
    const btn = document.getElementById('soundProfileBtn');
    if (btn) {{
      btn.textContent = (profile.id === 'mute') ? 'Sound: Mute' : `Sound: ${{profile.name}}`;
      btn.classList.toggle('active-toggle', profile.id !== 'mute');
    }}

    if (profile.id !== 'mute') {{
      SoundEngine.preview(profile.id);
    }}
  }};

  window.toggleTranslationVisibility = function() {{
    showTranslation = !showTranslation;
    localStorage.setItem('typing_show_trans', showTranslation ? 'true' : 'false');
    
    const btn = document.getElementById('transToggleBtn');
    if (btn) {{
      btn.textContent = showTranslation ? 'Trans: On' : 'Trans: Off';
      btn.classList.toggle('active-toggle', showTranslation);
    }}

    updateMarginaliaState();
  }};

  // Common high-frequency English stopwords that must NEVER be treated as cloze targets
  const STOPWORDS = new Set([
    'a', 'an', 'the', 'and', 'or', 'but', 'nor', 'for', 'yet', 'so',
    'in', 'on', 'at', 'to', 'from', 'by', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'under',
    'is', 'am', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'shall', 'should', 'can', 'could', 'may', 'might', 'must',
    'it', 'its', 'this', 'that', 'these', 'those', 'there', 'here', 'what', 'which', 'who', 'whom', 'whose', 'when', 'where', 'why', 'how',
    'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'not', 'only', 'own', 'same', 'than', 'too', 'very',
    'i', 'you', 'he', 'she', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs'
  ]);

  function isVocabMatch(w, vw) {{
    if (!w || !vw) return false;
    const lower = w.toLowerCase();
    const target = vw.toLowerCase();
    if (lower === target) return true;
    
    // Plural / prefix matches (mentors -> mentor, hints -> hint)
    if (lower.startsWith(target) && (lower.length - target.length) <= 3) return true;
    if (target.startsWith(lower) && (target.length - lower.length) <= 3) return true;

    // Stemming (striving -> strive, assassinated -> assassinate, recovering -> recover)
    const stem = s => {{
      for (const suf of ['ing', 'ed', 'es', 's', 'e']) {{
        if (s.endsWith(suf) && (s.length - suf.length) >= 3) {{
          return s.slice(0, -suf.length);
        }}
      }}
      return s;
    }};
    if (stem(lower) === stem(target)) return true;

    return false;
  }}

  // 4. Persistence Ledger for All Sentences in Active Chapter
  const STORAGE_KEY = 'typing_ledger_c' + (typeof activeChapterNum !== 'undefined' ? activeChapterNum : '1');
  const sentenceProgressLedger = new Map();

  function loadSavedLedger() {{
    try {{
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {{
        const parsed = JSON.parse(raw);
        for (const [k, v] of Object.entries(parsed)) {{
          sentenceProgressLedger.set(k, v);
        }}
      }}
    }} catch(e) {{}}
  }}
  loadSavedLedger();

  function persistLedgerToStorage() {{
    try {{
      const obj = {{}};
      sentenceProgressLedger.forEach((v, k) => {{
        obj[k] = v;
      }});
      localStorage.setItem(STORAGE_KEY, JSON.stringify(obj));
    }} catch(e) {{}}
  }}

  let activeSentenceEl = null;
  let wordItems = [];
  let currentWordIdx = 0;
  let inWordCharIdx = 0;
  let waitingForSpace = false;
  let consecutiveErrors = 0;
  let correctCount = 0;
  let errorCount = 0;
  let startTime = null;

  // Smart keyboard normalization for punctuation and typography
  function isCharMatch(input, expected) {{
    if (!input || !expected) return false;
    if (input === expected) return true;
    if (input.toLowerCase() === expected.toLowerCase()) return true;

    // Single quotes, apostrophes: ' matches ’ ‘ ` ʼ
    if (input === "'" && ("’‘`ʼ'".indexOf(expected) !== -1)) return true;
    // Double quotes: " matches “ ” « »
    if (input === '"' && ("“”«»\\"".indexOf(expected) !== -1)) return true;
    // Hyphens and dashes: - matches — – − ‐
    if (input === '-' && ("—–−‐-".indexOf(expected) !== -1)) return true;
    // Ellipsis: . matches …
    if (input === '.' && expected === '…') return true;

    return false;
  }}

  window.playActiveSentenceOnce = function() {{
    if (!activeSentenceEl || !audio) return;
    const start = parseFloat(activeSentenceEl.dataset.start);
    if (!isNaN(start)) {{
      if (typeof shadowState !== 'undefined') {{
        shadowState.completed = 0;
        shadowState.sentence = activeSentenceEl;
        if (shadowState.repetitions > 1 || shadowState.repetitions === Infinity) {{
          shadowState.phase = 'playing';
        }}
      }}
      audio.currentTime = start;
      audio.play().catch(() => {{}});
    }}
  }};

  window.updateHudLoopBtn = function() {{
    const btn = document.getElementById('hudLoopBtn');
    if (!btn) return;
    const rep = (typeof shadowState !== 'undefined' && shadowState.repetitions) ? shadowState.repetitions : 1;
    if (rep === Infinity || rep === 'Infinity' || rep === '∞') {{
      btn.textContent = 'Loop: ∞';
      btn.classList.add('active-toggle');
    }} else if (rep > 1) {{
      btn.textContent = `Loop: ${{rep}}×`;
      btn.classList.add('active-toggle');
    }} else {{
      btn.textContent = 'Loop: Off';
      btn.classList.remove('active-toggle');
    }}
  }};

  window.restartCurrentSentence = function() {{
    if (!activeSentenceEl) return;
    currentWordIdx = 0;
    inWordCharIdx = 0;
    waitingForSpace = false;
    consecutiveErrors = 0;
    ensureValidClozeIndex();
    saveSentenceState(activeSentenceEl.id);
    projectDocumentTypingState();
    window.playActiveSentenceOnce();
    updateHUDMetrics();
    updateMarginaliaState();
    const hi = document.getElementById('typingHiddenInput');
    if (hi) hi.focus({{ preventScroll: true }});
  }};

  window.gotoPreviousTypingSentence = function() {{
    if (!activeSentenceEl) return;
    const all = Array.from(document.querySelectorAll('.sentence-unit'));
    const idx = all.indexOf(activeSentenceEl);
    if (idx > 0) {{
      saveSentenceState(activeSentenceEl.id);
      lockSentence(all[idx - 1]);
    }}
  }};

  window.gotoNextTypingSentence = function() {{
    if (!activeSentenceEl) return;
    const all = Array.from(document.querySelectorAll('.sentence-unit'));
    const idx = all.indexOf(activeSentenceEl);
    if (idx < all.length - 1) {{
      saveSentenceState(activeSentenceEl.id);
      lockSentence(all[idx + 1]);
    }}
  }};

  window.toggleTypingMode = function(force) {{
    const shouldOpen = (typeof force === 'boolean') ? force : (window.__TYPING_MODE__ === 'off');
    if (shouldOpen) {{
      const subMode = SUB_MODES[currentSubModeIdx];
      setTypingMode(subMode.id);
    }} else {{
      setTypingMode('off');
    }}
  }};

  window.setTypingMode = function(mode) {{
    window.__TYPING_MODE__ = mode;

    const typingChip = document.getElementById('typingModeBtn');
    const hud = document.getElementById('inSituHud');
    const progressBar = document.getElementById('typingChapterProgressBar');
    const bottomDock = document.getElementById('bottomControlDock');

    if (mode === 'off') {{
      document.body.classList.remove('typing-mode-active');
      if (bottomDock) bottomDock.classList.remove('dock-typing-hidden');
      if (typingChip) typingChip.classList.remove('active');
      if (hud) {{
        hud.classList.remove('visible', 'hud-idle-hidden');
        if (typingHudIdleTimer) {{
          clearTimeout(typingHudIdleTimer);
          typingHudIdleTimer = null;
        }}
      }}
      if (progressBar) progressBar.style.width = '0%';
      if (typeof closeChapterCompleteModal === 'function') closeChapterCompleteModal();
      
      // Restore clean reader DOM
      document.querySelectorAll('.sentence-unit').forEach(el => {{
        el.classList.remove('typing-active-target');
        el.querySelectorAll('.w').forEach(w => {{
          if (w._originalHTML !== undefined) w.innerHTML = w._originalHTML;
        }});
      }});
      activeSentenceEl = null;
      if (audio && !audio.paused) {{
        audio.pause();
      }}
      if (typeof updateFocusPlayBtn === 'function') {{
        updateFocusPlayBtn();
      }}
      if (typeof renderGlobalPlayBtn === 'function') {{
        renderGlobalPlayBtn();
      }}
      window.removeEventListener('keydown', handleKeyInput, true);
      window.removeEventListener('keyup', handleKeyUp, true);
      if (typeof hideMarginalia === 'function') hideMarginalia();
      return;
    }}

    SoundEngine.preloadProfile(SOUND_PROFILES[currentSoundProfileIdx].id);

    if (typeof closeChapterCompleteModal === 'function') closeChapterCompleteModal();
    const hiddenBridge = document.getElementById('typingHiddenInput');
    if (hiddenBridge) {{
      hiddenBridge.value = '';
      hiddenBridge.focus({{ preventScroll: true }});
    }}

    // Activate typing isolation sandbox
    document.body.classList.add('typing-mode-active');

    // Hide bottom control dock in typing mode to eliminate overlapping collision
    if (bottomDock) bottomDock.classList.add('dock-typing-hidden');

    if (typingChip) typingChip.classList.add('active');

    // Close bottom dock menu drawer if open
    const drawer = document.getElementById('controlDrawer');
    const drawerBtn = document.getElementById('drawerToggleBtn');
    if (drawer && drawer.classList.contains('open')) {{
      drawer.classList.remove('open');
      if (drawerBtn) drawerBtn.classList.remove('active');
    }}

    if (hud) {{
      hud.classList.add('visible');
      hud.classList.remove('hud-idle-hidden');
      scheduleTypingHudHide(false);
      if (typeof window.updateHudLoopBtn === 'function') window.updateHudLoopBtn();
      if (typeof window.updateHudPlayPauseBtn === 'function') window.updateHudPlayPauseBtn();
      
      const subModeBtn = document.getElementById('typingSubModeBtn');
      if (subModeBtn) {{
        const current = SUB_MODES.find(m => m.id === mode) || SUB_MODES[0];
        subModeBtn.textContent = current.label;
      }}

      const profile = SOUND_PROFILES[currentSoundProfileIdx];
      const soundBtn = document.getElementById('soundProfileBtn');
      if (soundBtn) {{
        soundBtn.textContent = (profile.id === 'mute') ? 'Sound: Mute' : `Sound: ${{profile.name}}`;
        soundBtn.classList.toggle('active-toggle', profile.id !== 'mute');
      }}

      const transBtn = document.getElementById('transToggleBtn');
      if (transBtn) {{
        transBtn.textContent = showTranslation ? 'Trans: On' : 'Trans: Off';
        transBtn.classList.toggle('active-toggle', showTranslation);
      }}
    }}

    window.removeEventListener('keydown', handleKeyInput, true);
    window.addEventListener('keydown', handleKeyInput, true);
    window.removeEventListener('keyup', handleKeyUp, true);
    window.addEventListener('keyup', handleKeyUp, true);

    // Big-Tech Global Declarative Projection: Find resume sentence
    const allSentences = Array.from(document.querySelectorAll('.sentence-unit'));
    let resumeTarget = null;
    
    // 1. Try first uncompleted sentence
    for (let i = 0; i < allSentences.length; i++) {{
      const st = sentenceProgressLedger.get(allSentences[i].id);
      if (!st || !st.completed) {{
        resumeTarget = allSentences[i];
        break;
      }}
    }}
    // 2. If all completed or none found, fallback to active or first
    if (!resumeTarget) {{
      resumeTarget = (currentPlayingId ? document.getElementById(currentPlayingId) : null) || 
                     document.querySelector('.sentence-unit.active') || 
                     allSentences[0];
    }}

    if (resumeTarget) {{
      lockSentence(resumeTarget, false);
    }} else {{
      projectDocumentTypingState();
    }}
  }};

  function lockSentence(sentenceEl, forceReset = false) {{
    if (!sentenceEl) return;

    if (activeSentenceEl && activeSentenceEl !== sentenceEl) {{
      saveSentenceState(activeSentenceEl.id);
      activeSentenceEl.classList.remove('typing-active-target');
    }}

    activeSentenceEl = sentenceEl;
    sentenceEl.classList.add('typing-active-target');
    
    // Sync shadowing state for loop repeat
    if (typeof shadowState !== 'undefined') {{
      shadowState.completed = 0;
      shadowState.sentence = sentenceEl;
      if (shadowState.repetitions > 1 || shadowState.repetitions === Infinity) {{
        shadowState.phase = 'playing';
      }}
    }}

    // Smart scroll: zero jitter if sentence is already comfortably visible!
    smartScrollIntoView(sentenceEl);

    buildWordItems(sentenceEl);

    const saved = sentenceProgressLedger.get(sentenceEl.id);
    if (saved && !forceReset) {{
      currentWordIdx = saved.wordIdx;
      inWordCharIdx = saved.charIdx;
      waitingForSpace = saved.waitingForSpace;
    }} else {{
      currentWordIdx = 0;
      inWordCharIdx = 0;
      waitingForSpace = false;
      saveSentenceState(sentenceEl.id);
    }}
    if (window.__TYPING_MODE__ === 'cloze') {{
      ensureValidClozeIndex();
    }}

    consecutiveErrors = 0;
    if (!startTime) startTime = performance.now();

    projectDocumentTypingState();
    window.playActiveSentenceOnce();
    updateHUDMetrics();
    updateChapterProgressBar();
    updateMarginaliaState();

    const hi = document.getElementById('typingHiddenInput');
    if (hi) hi.focus({{ preventScroll: true }});
  }}

  function updateChapterProgressBar() {{
    const allSentences = Array.from(document.querySelectorAll('.sentence-unit'));
    if (allSentences.length === 0 || !activeSentenceEl) return;
    
    let completedCount = 0;
    allSentences.forEach(s => {{
      const st = sentenceProgressLedger.get(s.id);
      if (st && st.completed) completedCount++;
    }});

    const currentIdx = allSentences.indexOf(activeSentenceEl) + 1;
    const pct = Math.round((completedCount / allSentences.length) * 100);

    const bar = document.getElementById('typingChapterProgressBar');
    if (bar) bar.style.width = `${{pct}}%`;

    const tag = document.getElementById('hudProgressTag');
    if (tag) tag.textContent = `${{completedCount}} / ${{allSentences.length}} Done`;
  }}

  function saveSentenceState(sentenceId, forceCompleted = false) {{
    if (!sentenceId) return;
    const existing = sentenceProgressLedger.get(sentenceId) || {{}};
    const isCompleted = forceCompleted || existing.completed || (currentWordIdx >= wordItems.length);
    sentenceProgressLedger.set(sentenceId, {{
      wordIdx: currentWordIdx,
      charIdx: inWordCharIdx,
      waitingForSpace: waitingForSpace,
      completed: isCompleted
    }});
    persistLedgerToStorage();
  }}

  function buildWordItems(sentenceEl) {{
    if (!sentenceEl) return;
    const wSpans = Array.from(sentenceEl.querySelectorAll('.w'));
    
    let vocabWords = [];
    try {{
      const rawVocab = sentenceEl.getAttribute('data-vocab');
      if (rawVocab) {{
        const vArr = JSON.parse(rawVocab);
        vArr.forEach(v => {{
          if (!v || !v.word) return;
          const fullClean = v.word.toLowerCase().replace(/[^a-zA-Z0-9]/g, '');
          if (fullClean.length >= 3 && !STOPWORDS.has(fullClean)) {{
            vocabWords.push(fullClean);
          }}
          const parts = v.word.toLowerCase().replace(/[^a-zA-Z0-9\\s]/g, ' ').split(/\\s+/);
          parts.forEach(p => {{
            if (p.length >= 3 && !STOPWORDS.has(p)) {{
              vocabWords.push(p);
            }}
          }});
        }});
      }}
    }} catch(e) {{}}

    wordItems = wSpans.map((el, idx) => {{
      if (el._originalHTML === undefined) {{
        el._originalHTML = el.innerHTML;
      }}
      const rawText = el._originalHTML.trim();
      const cleanWord = rawText.replace(/[^a-zA-Z0-9]/g, '');
      const lower = cleanWord.toLowerCase();
      const subwords = rawText.split(/[^a-zA-Z0-9]+/).filter(Boolean).map(s => s.toLowerCase());
      
      const isTarget = vocabWords.length > 0 && (
        (!STOPWORDS.has(lower) && vocabWords.some(vw => isVocabMatch(lower, vw))) ||
        subwords.some(sw => !STOPWORDS.has(sw) && vocabWords.some(vw => isVocabMatch(sw, vw)))
      );

      return {{
        el,
        idx,
        rawText,
        cleanWord,
        isClozeTarget: isTarget
      }};
    }});
  }}

  // =========================================================================
  // BIG-TECH DECLARATIVE PROJECTION: Declarative Single Source of Truth
  // Eliminates all dirty grey spans, flickering unrendered sentences, and ad-hoc mutations!
  // =========================================================================
  // High-Speed Localized Projection: Renders ONLY the active sentence on keystrokes (O(1), <0.05ms)
  function projectActiveSentenceOnly() {{
    if (!activeSentenceEl || window.__TYPING_MODE__ === 'off') return;
    const mode = window.__TYPING_MODE__;
    const wSpans = Array.from(activeSentenceEl.querySelectorAll('.w'));
    const targetWordIdx = currentWordIdx;
    const targetCharIdx = inWordCharIdx;
    const isWaitingSpace = waitingForSpace;

    wSpans.forEach((el, wIdx) => {{
      if (el._originalHTML === undefined) el._originalHTML = el.innerHTML;
      const raw = el._originalHTML.trim();
      const item = wordItems[wIdx];

      // Cloze Mode in Active Sentence
      if (mode === 'cloze') {{
        const isClozeTarget = item ? item.isClozeTarget : false;
        if (!isClozeTarget) {{
          el.innerHTML = el._originalHTML;
          return;
        }}

        const clean = item.cleanWord;
        if (wIdx < targetWordIdx) {{
          el.innerHTML = `<span class="twc-correct">${{raw}}</span>`;
          return;
        }}
        if (wIdx > targetWordIdx) {{
          let html = '';
          for (let i = 0; i < clean.length; i++) {{
            html += `<span class="twc-cloze-slot-char">&nbsp;</span>`;
          }}
          const trailingPunct = raw.slice(clean.length);
          if (trailingPunct) html += trailingPunct;
          el.innerHTML = html;
          return;
        }}

        // Active cloze target word
        let html = '';
        for (let i = 0; i < clean.length; i++) {{
          const char = clean[i];
          if (i < targetCharIdx) {{
            html += `<span class="twc-correct">${{char}}</span>`;
          }} else if (i === targetCharIdx && !isWaitingSpace) {{
            html += `<span class="twc-cloze-cursor-char">&nbsp;</span>`;
          }} else if (i === clean.length - 1 && isWaitingSpace) {{
            html += `<span class="twc-correct twc-caret-space">${{char}}</span>`;
          }} else {{
            html += `<span class="twc-cloze-slot-char">&nbsp;</span>`;
          }}
        }}
        const trailingPunct = raw.slice(clean.length);
        if (trailingPunct) html += trailingPunct;
        el.innerHTML = html;
        return;
      }}

      // Dictation (Blind) Mode in Active Sentence
      if (mode === 'dictation') {{
        if (wIdx < targetWordIdx) {{
          el.innerHTML = `<span class="twc-correct">${{raw}}</span>`;
          return;
        }}
        if (wIdx > targetWordIdx) {{
          let html = '';
          for (let i = 0; i < raw.length; i++) {{
            const char = raw[i];
            const isPunct = !/^[a-zA-Z0-9]$/.test(char);
            html += isPunct ? char : `<span class="twc-masked">&nbsp;</span>`;
          }}
          el.innerHTML = html;
          return;
        }}

        let html = '';
        for (let i = 0; i < raw.length; i++) {{
          const char = raw[i];
          const isPunct = !/^[a-zA-Z0-9]$/.test(char);
          if (i < targetCharIdx) {{
            html += `<span class="twc-correct">${{char}}</span>`;
          }} else if (i === targetCharIdx && !isWaitingSpace) {{
            html += isPunct ? `<span class="twc-cursor">${{char}}</span>` : `<span class="twc-masked-cursor">&nbsp;</span>`;
          }} else if (i === raw.length - 1 && isWaitingSpace) {{
            html += `<span class="twc-correct twc-caret-space">${{char}}</span>`;
          }} else {{
            html += isPunct ? char : `<span class="twc-masked">&nbsp;</span>`;
          }}
        }}
        el.innerHTML = html;
        return;
      }}

      // In-situ (Type) Mode in Active Sentence - ZERO LAYOUT SHIFT ARCHITECTURE
      if (wIdx < targetWordIdx) {{
        el.innerHTML = `<span class="twc-correct">${{raw}}</span>`;
        return;
      }}
      if (wIdx > targetWordIdx) {{
        el.innerHTML = `<span class="twc-active-pending">${{raw}}</span>`;
        return;
      }}
      let html = '';
      for (let i = 0; i < raw.length; i++) {{
        const char = raw[i];
        if (i < targetCharIdx) {{
          html += `<span class="twc-correct">${{char}}</span>`;
        }} else if (i === targetCharIdx && !isWaitingSpace) {{
          html += `<span class="twc-cursor">${{char}}</span>`;
        }} else if (i === raw.length - 1 && isWaitingSpace) {{
          html += `<span class="twc-correct twc-caret-space">${{char}}</span>`;
        }} else {{
          html += `<span class="twc-active-pending">${{char}}</span>`;
        }}
      }}
      el.innerHTML = html;
    }});
  }}

  function projectDocumentTypingState() {{
    const mode = window.__TYPING_MODE__;
    if (mode === 'off') return;

    const allSentences = document.querySelectorAll('.sentence-unit');
    allSentences.forEach(sentenceEl => {{
      const isCurrentActive = (sentenceEl === activeSentenceEl);
      const state = sentenceProgressLedger.get(sentenceEl.id);
      const isCompleted = state ? state.completed : false;
      const wSpans = Array.from(sentenceEl.querySelectorAll('.w'));

      // 1. COMPLETED SENTENCE: In cloze mode, only target words stay green; in full modes, all typed words stay green
      if (isCompleted && !isCurrentActive) {{
        if (mode === 'cloze') {{
          let sentenceVocab = [];
          try {{
            const rawV = sentenceEl.getAttribute('data-vocab');
            if (rawV) {{
              const vArr = JSON.parse(rawV);
              vArr.forEach(v => {{
                if (!v || !v.word) return;
                const fullClean = v.word.toLowerCase().replace(/[^a-zA-Z0-9]/g, '');
                if (fullClean.length >= 3 && !STOPWORDS.has(fullClean)) sentenceVocab.push(fullClean);
                v.word.toLowerCase().replace(/[^a-zA-Z0-9\\s]/g, ' ').split(/\\s+/).forEach(p => {{
                  if (p.length >= 3 && !STOPWORDS.has(p)) sentenceVocab.push(p);
                }});
              }});
            }}
          }} catch(e) {{}}

          wSpans.forEach(el => {{
            if (el._originalHTML === undefined) el._originalHTML = el.innerHTML;
            const raw = el._originalHTML.trim();
            const clean = raw.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
            const subwords = raw.split(/[^a-zA-Z0-9]+/).filter(Boolean).map(s => s.toLowerCase());
            const isTarget = sentenceVocab.length > 0 && (
              (!STOPWORDS.has(clean) && sentenceVocab.some(vw => isVocabMatch(clean, vw))) ||
              subwords.some(sw => !STOPWORDS.has(sw) && sentenceVocab.some(vw => isVocabMatch(sw, vw)))
            );
            if (isTarget) {{
              el.innerHTML = `<span class="twc-correct">${{raw}}</span>`;
            }} else {{
              el.innerHTML = el._originalHTML;
            }}
          }});
          return;
        }}

        wSpans.forEach(el => {{
          if (el._originalHTML === undefined) el._originalHTML = el.innerHTML;
          const raw = el._originalHTML.trim();
          el.innerHTML = `<span class="twc-correct">${{raw}}</span>`;
        }});
        return;
      }}

      // 2. UNSTARTED SENTENCE: Pure, Natural Reader Book Typography (ZERO DIRTY GREY!)
      if (!state && !isCurrentActive) {{
        wSpans.forEach(el => {{
          if (el._originalHTML !== undefined) {{
            el.innerHTML = el._originalHTML;
          }}
        }});
        return;
      }}

      // 3. CURRENT ACTIVE SENTENCE: Delegated to high-speed localized projection
      if (isCurrentActive) {{
        projectActiveSentenceOnly();
        return;
      }}

      // 4. PARTIALLY COMPLETED (NON-ACTIVE) SENTENCE: Typed words stay green, untyped stay natural
      if (state && !isCurrentActive) {{
        if (mode === 'cloze') {{
          let sentenceVocab = [];
          try {{
            const rawV = sentenceEl.getAttribute('data-vocab');
            if (rawV) {{
              const vArr = JSON.parse(rawV);
              vArr.forEach(v => {{
                if (!v || !v.word) return;
                const fullClean = v.word.toLowerCase().replace(/[^a-zA-Z0-9]/g, '');
                if (fullClean.length >= 3 && !STOPWORDS.has(fullClean)) sentenceVocab.push(fullClean);
                v.word.toLowerCase().replace(/[^a-zA-Z0-9\\s]/g, ' ').split(/\\s+/).forEach(p => {{
                  if (p.length >= 3 && !STOPWORDS.has(p)) sentenceVocab.push(p);
                }});
              }});
            }}
          }} catch(e) {{}}

          wSpans.forEach((el, wIdx) => {{
            if (el._originalHTML === undefined) el._originalHTML = el.innerHTML;
            const raw = el._originalHTML.trim();
            const clean = raw.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
            const subwords = raw.split(/[^a-zA-Z0-9]+/).filter(Boolean).map(s => s.toLowerCase());
            const isTarget = sentenceVocab.length > 0 && (
              (!STOPWORDS.has(clean) && sentenceVocab.some(vw => isVocabMatch(clean, vw))) ||
              subwords.some(sw => !STOPWORDS.has(sw) && sentenceVocab.some(vw => isVocabMatch(sw, vw)))
            );
            if (isTarget && wIdx < state.wordIdx) {{
              el.innerHTML = `<span class="twc-correct">${{raw}}</span>`;
            }} else {{
              el.innerHTML = el._originalHTML;
            }}
          }});
          return;
        }}

        wSpans.forEach((el, wIdx) => {{
          if (el._originalHTML === undefined) el._originalHTML = el.innerHTML;
          const raw = el._originalHTML.trim();
          if (wIdx < state.wordIdx) {{
            el.innerHTML = `<span class="twc-correct">${{raw}}</span>`;
          }} else {{
            el.innerHTML = el._originalHTML;
          }}
        }});
      }}
    }});
  }}

  function handleKeyUp(e) {{
    if (window.__TYPING_MODE__ === 'off') return;
    const capsBadge = document.getElementById('capsLockBadge');
    if (capsBadge && e.getModifierState) {{
      capsBadge.style.display = e.getModifierState('CapsLock') ? 'inline-block' : 'none';
    }}
  }}

  function handleKeyInput(e) {{
    if (window.__TYPING_MODE__ === 'off') return;

    // CapsLock dynamic badge check
    const capsBadge = document.getElementById('capsLockBadge');
    if (capsBadge && e.getModifierState) {{
      capsBadge.style.display = e.getModifierState('CapsLock') ? 'inline-block' : 'none';
    }}

    // Auto-hide HUD on typing keypress for pure focus and zero screen obstruction
    if (!['Tab', 'Escape'].includes(e.key)) {{
      scheduleTypingHudHide(true);
    }}

    e.stopImmediatePropagation();

    // Hotkey: Esc -> Exit back to Read mode
    if (e.key === 'Escape') {{
      e.preventDefault();
      setTypingMode('off');
      return;
    }}

    // Hotkey: Tab -> Play / Pause Audio; Shift+Tab -> Restart sentence from beginning
    if (e.key === 'Tab') {{
      e.preventDefault();
      if (e.shiftKey) {{
        window.restartCurrentSentence();
      }} else {{
        window.toggleTypingAudioPlayPause();
      }}
      return;
    }}

    // Hotkey: ArrowLeft or ArrowUp -> Navigate to previous sentence
    if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {{
      e.preventDefault();
      window.gotoPreviousTypingSentence();
      return;
    }}

    // Hotkey: ArrowRight or ArrowDown -> Navigate to next sentence
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {{
      e.preventDefault();
      window.gotoNextTypingSentence();
      return;
    }}

    // Hotkey: Ctrl+H or Alt+H -> Hint
    if ((e.ctrlKey || e.altKey) && (e.key === 'h' || e.key === 'H')) {{
      e.preventDefault();
      window.triggerHint();
      return;
    }}

    // Hotkey: Cmd+R / Ctrl+R / Alt+R -> Restart current sentence (Intercept Mac reload to protect session state)
    if ((e.metaKey || e.ctrlKey || e.altKey) && (e.key === 'r' || e.key === 'R')) {{
      e.preventDefault();
      window.restartCurrentSentence();
      return;
    }}

    // Hotkey: Ctrl+L or Alt+L -> Cycle repeat loop (Off / 2× / 3× / ∞)
    if ((e.ctrlKey || e.altKey) && (e.key === 'l' || e.key === 'L')) {{
      e.preventDefault();
      cycleMainRepeat();
      return;
    }}

    // Hotkey: Ctrl+Enter or Alt+Enter -> Skip to next sentence
    if ((e.ctrlKey || e.altKey) && e.key === 'Enter') {{
      e.preventDefault();
      window.gotoNextTypingSentence();
      return;
    }}

    // Hotkey: Cmd+T / Ctrl+T / Alt+T -> Toggle Translation
    if ((e.metaKey || e.ctrlKey || e.altKey) && (e.key === 't' || e.key === 'T')) {{
      e.preventDefault();
      window.toggleTranslationVisibility();
      return;
    }}

    // Ignore pure modifier presses
    if (['Shift', 'Control', 'Alt', 'Meta', 'CapsLock'].includes(e.key)) return;

    if (window.__TYPING_MODE__ === 'cloze') {{
      ensureValidClozeIndex();
    }}

    if (currentWordIdx >= wordItems.length) {{
      if (window.__TYPING_MODE__ === 'cloze' && (e.key === ' ' || e.code === 'Space' || e.key === 'Enter')) {{
        e.preventDefault();
        saveSentenceState(activeSentenceEl?.id, true);
        finishSentenceAndAdvance(false);
        return;
      }}
      return;
    }}
    const currentItem = wordItems[currentWordIdx];
    const isCloze = (window.__TYPING_MODE__ === 'cloze');
    const targetWord = isCloze ? currentItem.cleanWord : currentItem.rawText;

    // Word-Level Backspace: Ctrl+Backspace or Alt+Backspace
    if (e.key === 'Backspace' && (e.ctrlKey || e.altKey)) {{
      e.preventDefault();
      inWordCharIdx = 0;
      waitingForSpace = false;
      consecutiveErrors = 0;
      saveSentenceState(activeSentenceEl?.id);
      projectActiveSentenceOnly();
      SoundEngine.play(false);
      return;
    }}

    // Single Backspace
    if (e.key === 'Backspace') {{
      e.preventDefault();
      consecutiveErrors = 0;
      if (waitingForSpace) {{
        waitingForSpace = false;
        inWordCharIdx = Math.max(0, targetWord.length - 1);
      }} else if (inWordCharIdx > 0) {{
        inWordCharIdx--;
      }} else if (currentWordIdx > 0) {{
        if (isCloze) {{
          for (let p = currentWordIdx - 1; p >= 0; p--) {{
            if (wordItems[p].isClozeTarget) {{
              currentWordIdx = p;
              inWordCharIdx = wordItems[p].cleanWord.length;
              waitingForSpace = true;
              break;
            }}
          }}
        }} else {{
          currentWordIdx--;
          inWordCharIdx = wordItems[currentWordIdx].rawText.length;
          waitingForSpace = true;
        }}
      }}
      saveSentenceState(activeSentenceEl?.id);
      projectActiveSentenceOnly();
      SoundEngine.play(false);
      return;
    }}

    // Prevent default browser scrolling/selection
    e.preventDefault();

    // Spacebar advances to next word
    if (e.key === ' ' || e.code === 'Space' || (isCloze && e.key === 'Enter')) {{
      if (waitingForSpace || inWordCharIdx >= targetWord.length) {{
        waitingForSpace = false;
        consecutiveErrors = 0;
        SoundEngine.play(true);
        advanceToNextWord();
      }} else {{
        errorCount++;
        triggerErrorEffect(currentItem.el);
        SoundEngine.error();
        updateHUDMetrics();
      }}
      return;
    }}

    // ANY single character typed: Letters, numbers, punctuation
    if (e.key.length === 1 && e.key !== ' ') {{
      if (waitingForSpace) {{
        if (isCloze && (e.key === ',' || e.key === '.' || e.key === ':' || e.key === ';')) {{
          waitingForSpace = false;
          consecutiveErrors = 0;
          SoundEngine.play(false);
          advanceToNextWord();
          return;
        }}
        triggerErrorEffect(currentItem.el);
        SoundEngine.error();
        return;
      }}

      const inputChar = e.key;
      const expectedChar = targetWord[inWordCharIdx];

      // Smart Opening Quote/Bracket Tolerance
      if (inWordCharIdx === 0 && /^[\(\"“‘\[]/.test(expectedChar) && targetWord.length > 1) {{
        if (isCharMatch(inputChar, targetWord[1])) {{
          correctCount += 2;
          inWordCharIdx = 2;
          consecutiveErrors = 0;
          SoundEngine.play(false);
          checkCompletion();
          saveSentenceState(activeSentenceEl?.id);
          projectActiveSentenceOnly();
          updateHUDMetrics();
          return;
        }}
      }}

      if (isCharMatch(inputChar, expectedChar)) {{
        correctCount++;
        inWordCharIdx++;
        consecutiveErrors = 0;
        SoundEngine.play(false);
        checkCompletion();
        saveSentenceState(activeSentenceEl?.id);
        projectActiveSentenceOnly();
      }} else {{
        errorCount++;
        consecutiveErrors++;
        triggerErrorEffect(currentItem.el);
        SoundEngine.error();

        if (consecutiveErrors >= 3) {{
          window.triggerHint();
        }}
      }}
      updateHUDMetrics();
    }}

    function checkCompletion() {{
      if (inWordCharIdx >= targetWord.length) {{
        const isLastWord = (currentWordIdx === wordItems.length - 1);

        // Typing all characters of the last word completes sentence immediately!
        if (!isCloze && isLastWord) {{
          currentWordIdx = wordItems.length;
          inWordCharIdx = 0;
          waitingForSpace = false;
          saveSentenceState(activeSentenceEl?.id, true);
          projectDocumentTypingState();
          finishSentenceAndAdvance(false);
          return;
        }}

        // In Cloze mode: if this was the last cloze target in sentence, complete immediately!
        if (isCloze) {{
          let hasMoreTargets = false;
          for (let i = currentWordIdx + 1; i < wordItems.length; i++) {{
            if (wordItems[i].isClozeTarget) {{
              hasMoreTargets = true;
              break;
            }}
          }}
          if (!hasMoreTargets) {{
            currentWordIdx = wordItems.length;
            inWordCharIdx = 0;
            waitingForSpace = false;
            saveSentenceState(activeSentenceEl?.id, true);
            projectDocumentTypingState();
            finishSentenceAndAdvance(false);
            return;
          }} else {{
            // Auto-advance directly to the next cloze target slot! Zero friction!
            advanceToNextWord();
            return;
          }}
        }}

        waitingForSpace = true;
      }}
    }}
  }}

  function advanceToNextWord() {{
    inWordCharIdx = 0;
    waitingForSpace = false;
    consecutiveErrors = 0;
    const mode = window.__TYPING_MODE__;

    if (mode === 'cloze') {{
      let nextIdx = -1;
      for (let i = currentWordIdx + 1; i < wordItems.length; i++) {{
        if (wordItems[i].isClozeTarget) {{
          nextIdx = i;
          break;
        }}
      }}
      if (nextIdx !== -1) {{
        currentWordIdx = nextIdx;
        saveSentenceState(activeSentenceEl?.id);
        projectActiveSentenceOnly();
      }} else {{
        currentWordIdx = wordItems.length;
        saveSentenceState(activeSentenceEl?.id, true);
        projectDocumentTypingState();
        finishSentenceAndAdvance(false);
      }}
    }} else {{
      currentWordIdx++;
      if (currentWordIdx >= wordItems.length) {{
        saveSentenceState(activeSentenceEl?.id, true);
        projectDocumentTypingState();
        finishSentenceAndAdvance(false);
      }} else {{
        saveSentenceState(activeSentenceEl?.id);
        projectActiveSentenceOnly();
      }}
    }}
  }}

  function triggerErrorEffect(el) {{
    if (!el) return;
    const activeSpan = el.querySelector('.twc-cursor, .twc-masked-cursor, .twc-cloze-cursor-char') || el;
    activeSpan.classList.add('twc-error-shake');
    setTimeout(() => activeSpan.classList.remove('twc-error-shake'), 180);
  }}

  function updateHUDMetrics() {{
    const metricsEl = document.getElementById('hudMetrics');
    if (!metricsEl) return;
    const elapsedMin = (performance.now() - (startTime || performance.now())) / 60000;
    const wpm = elapsedMin > 0 ? Math.round((correctCount / 5) / elapsedMin) : 0;
    const total = correctCount + errorCount;
    const acc = total > 0 ? Math.round((correctCount / total) * 100) : 100;
    metricsEl.textContent = `${{wpm}} WPM · ${{acc}}% ACC`;
  }}

  function finishSentenceAndAdvance(isSkip = false) {{
    if (!isSkip) {{
      SoundEngine.chime();
    }}
    const metricsEl = document.getElementById('hudMetrics');
    if (metricsEl) metricsEl.textContent = isSkip ? 'Skipped' : 'Complete';

    const finishedSentenceEl = activeSentenceEl;
    if (!finishedSentenceEl) return;

    currentWordIdx = wordItems.length;
    inWordCharIdx = 0;
    waitingForSpace = false;
    saveSentenceState(finishedSentenceEl.id, true);
    projectDocumentTypingState();

    setTimeout(() => {{
      saveSentenceState(finishedSentenceEl.id, true);
      finishedSentenceEl.classList.remove('typing-active-target');

      const all = Array.from(document.querySelectorAll('.sentence-unit'));
      const curIdx = all.indexOf(finishedSentenceEl);
      if (curIdx >= 0 && curIdx < all.length - 1) {{
        const next = all[curIdx + 1];
        lockSentence(next, false);
      }} else {{
        if (metricsEl) metricsEl.textContent = 'Chapter Complete';
        if (typeof window.showChapterCompleteModal === 'function') {{
          window.showChapterCompleteModal();
        }}
      }}
    }}, isSkip ? 100 : 180);
  }}

  window.triggerHint = function() {{
    if (!activeSentenceEl || currentWordIdx >= wordItems.length) return;
    const currentItem = wordItems[currentWordIdx];
    const isCloze = (window.__TYPING_MODE__ === 'cloze');
    const targetWord = isCloze ? currentItem.cleanWord : currentItem.rawText;
    
    const el = currentItem.el;
    const cursorSpan = el.querySelector('.twc-cursor, .twc-masked-cursor, .twc-cloze-cursor-char') || el;
    const expectedChar = targetWord[inWordCharIdx] || ' ';
    
    cursorSpan.textContent = expectedChar;
    cursorSpan.classList.add('twc-hint-glow');
    setTimeout(() => {{
      cursorSpan.classList.remove('twc-hint-glow');
    }}, 400);
  }};

  // Audio Barrier handler (Suppresses playback bleed in typing mode, supports 2×/3×/∞ loop)
  if (audio) {{
    audio.addEventListener('timeupdate', () => {{
      if (window.__TYPING_MODE__ !== 'off' && activeSentenceEl) {{
        const end = parseFloat(activeSentenceEl.dataset.end);
        if (!isNaN(end) && audio.currentTime >= end) {{
          const rep = (typeof shadowState !== 'undefined' && shadowState.repetitions) ? shadowState.repetitions : 1;
          if (rep === Infinity || (rep > 1 && (shadowState.completed + 1) < rep)) {{
            shadowState.completed = (shadowState.completed || 0) + 1;
            const start = parseFloat(activeSentenceEl.dataset.start);
            if (!isNaN(start)) {{
              audio.currentTime = start;
              audio.play().catch(() => {{}});
              return;
            }}
          }}
          audio.pause();
          if (typeof shadowState !== 'undefined') shadowState.completed = 0;

          // In Cloze mode: if active sentence has NO cloze targets, auto-advance on playback completion
          if (window.__TYPING_MODE__ === 'cloze') {{
            const hasAnyTarget = wordItems.some(w => w.isClozeTarget);
            if (!hasAnyTarget) {{
              saveSentenceState(activeSentenceEl.id, true);
              finishSentenceAndAdvance(false);
            }}
          }}
        }}
      }}
    }});
  }}

  // Global Keyboard Shortcut: 'K' triggers Typing Mode when in reading view
  window.addEventListener('keydown', function(e) {{
    if (window.__TYPING_MODE__ === 'off' && (e.key === 'k' || e.key === 'K' || e.code === 'KeyK') && !e.target.matches('input, textarea, select')) {{
      e.preventDefault();
      window.toggleTypingMode();
    }}
  }});

  // Mouse Click Handler: Seamless non-destructive sentence switching in Typing Mode
  const prevHandleClick = window.handleSentenceClick;
  window.handleSentenceClick = function(event, id, start, end, hasMatch) {{
    if (window.__TYPING_MODE__ === 'off') {{
      if (prevHandleClick) return prevHandleClick(event, id, start, end, hasMatch);
      return;
    }}

    if (event && event.stopPropagation) event.stopPropagation();

    const sentence = document.getElementById(id);
    if (!sentence) return;

    if (activeSentenceEl === sentence) {{
      window.playActiveSentenceOnce();
      updateMarginaliaState();
    }} else {{
      lockSentence(sentence, false);
    }}
  }};

  // =========================================================================
  // CHAPTER COMPLETE CELEBRATION MODAL
  // =========================================================================
  window.showChapterCompleteModal = function() {{
    const modal = document.getElementById('typingCompleteModal');
    if (!modal) return;

    const elapsedMin = (performance.now() - (startTime || performance.now())) / 60000;
    const totalSec = Math.round((performance.now() - (startTime || performance.now())) / 1000);
    const mins = Math.floor(totalSec / 60);
    const secs = totalSec % 60;
    const timeStr = `${{mins}}:${{secs < 10 ? '0' : ''}}${{secs}}`;

    const wpm = elapsedMin > 0 ? Math.round((correctCount / 5) / elapsedMin) : 0;
    const total = correctCount + errorCount;
    const acc = total > 0 ? Math.round((correctCount / total) * 100) : 100;

    const allSentences = Array.from(document.querySelectorAll('.sentence-unit'));
    let completedCount = 0;
    allSentences.forEach(s => {{
      const st = sentenceProgressLedger.get(s.id);
      if (st && st.completed) completedCount++;
    }});

    const wpmEl = document.getElementById('tcFinalWpm');
    if (wpmEl) wpmEl.textContent = wpm;
    const accEl = document.getElementById('tcFinalAcc');
    if (accEl) accEl.textContent = `${{acc}}%`;
    const timeEl = document.getElementById('tcFinalTime');
    if (timeEl) timeEl.textContent = timeStr;
    const sentEl = document.getElementById('tcFinalSentences');
    if (sentEl) sentEl.textContent = `${{completedCount}} / ${{allSentences.length}}`;

    modal.classList.add('visible');
  }};

  window.closeChapterCompleteModal = function(returnToReading = false) {{
    const modal = document.getElementById('typingCompleteModal');
    if (modal) modal.classList.remove('visible');
    if (returnToReading) {{
      window.setTypingMode('off');
    }}
  }};

  window.restartChapterTyping = function() {{
    window.closeChapterCompleteModal(false);
    sentenceProgressLedger.clear();
    try {{
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem('typing_sentence_ledger_v2');
    }} catch(e) {{}}
    correctCount = 0;
    errorCount = 0;
    startTime = performance.now();
    const allSentences = Array.from(document.querySelectorAll('.sentence-unit'));
    if (allSentences.length > 0) {{
      lockSentence(allSentences[0], true);
    }}
  }};

  // Virtual Keyboard Input Bridge for Mobile / iPad
  const hiddenInputBridge = document.getElementById('typingHiddenInput');
  if (hiddenInputBridge) {{
    hiddenInputBridge.value = '\\u200B';
    hiddenInputBridge.addEventListener('input', () => {{
      const rawVal = hiddenInputBridge.value;
      if (!rawVal || rawVal.length === 0) {{
        hiddenInputBridge.value = '\\u200B';
        handleKeyInput({{
          key: 'Backspace',
          code: 'Backspace',
          preventDefault: () => {{}},
          stopImmediatePropagation: () => {{}}
        }});
        return;
      }}
      const chars = rawVal.replace('\\u200B', '');
      hiddenInputBridge.value = '\\u200B';
      if (!chars) return;
      for (let i = 0; i < chars.length; i++) {{
        const char = chars[i];
        handleKeyInput({{
          key: char,
          code: 'Key' + char.toUpperCase(),
          preventDefault: () => {{}},
          stopImmediatePropagation: () => {{}}
        }});
      }}
    }});
    hiddenInputBridge.addEventListener('keydown', (e) => {{
      if (e.key === 'Backspace' || e.key === 'Enter') {{
        handleKeyInput(e);
      }}
    }});
  }}
}})();
</script>
"""

def safe_replace(name: str, src: str, target: str, replacement: str) -> str:
    if target not in src:
        logging.warning(f"Target pattern '{name}' not found for replacement; template structure may have evolved.")
        return src
    return src.replace(target, replacement)

# Target pattern definitions for reader injection
target_set_rep = """function setMainRepetitions(n) {
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
  }"""

replacement_set_rep = """function setMainRepetitions(n) {
  const nextRep = (n === Infinity || n === 'Infinity' || n === '∞') ? Infinity : Math.max(1, parseInt(n, 10) || 1);
  shadowState.repetitions = nextRep;
  try {
    localStorage.setItem(STORAGE_PREFIX + 'repetitions', String(nextRep));
    localStorage.setItem('reader_focus_repetitions', String(nextRep));
  } catch(e) {}
  renderRepeatBtn(nextRep);
  const focusRepBtn = document.getElementById('focusRepBtn');
  if (focusRepBtn) {
    focusRepBtn.textContent = (nextRep === Infinity) ? '∞' : `${nextRep}×`;
  }"""

target_render_rep = """function renderRepeatBtn(rep) {
  const repBtn = document.getElementById('repeatBtn') || document.getElementById('shadowBtn');
  if (!repBtn) return;
  if (rep > 1) {
    repBtn.innerHTML = `${REPEAT_ICON_SVG}<span class="rep-badge">${rep}</span>`;
    repBtn.classList.add('active');
  } else {
    repBtn.innerHTML = REPEAT_ICON_SVG;
    repBtn.classList.remove('active');
  }
}"""

replacement_render_rep = """function renderRepeatBtn(rep) {
  const repBtn = document.getElementById('repeatBtn') || document.getElementById('shadowBtn');
  if (!repBtn) return;
  const isInf = (rep === Infinity || rep === 'Infinity' || rep === '∞');
  if (isInf || rep > 1) {
    const badgeText = isInf ? '∞' : rep;
    repBtn.innerHTML = `${REPEAT_ICON_SVG}<span class="rep-badge">${badgeText}</span>`;
    repBtn.classList.add('active');
  } else {
    repBtn.innerHTML = REPEAT_ICON_SVG;
    repBtn.classList.remove('active');
  }
  if (typeof updateHudLoopBtn === 'function') updateHudLoopBtn();
}"""

target_focus_status = """function updateFocusStatus() {
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
}"""

replacement_focus_status = """function updateFocusStatus() {
  const repBtn = document.getElementById('focusRepBtn');
  if (repBtn) {
    if (shadowState.repetitions <= 1) {
      repBtn.textContent = '1×';
    } else if (shadowState.repetitions === Infinity) {
      repBtn.textContent = '∞';
    } else {
      const cur = Math.min(shadowState.repetitions, shadowState.completed + 1);
      repBtn.textContent = `${cur}/${shadowState.repetitions}`;
    }
  }
  const statusEl = document.getElementById('focusStatus') || document.getElementById('pocketStatus');
  if (statusEl) {
    if (shadowState.repetitions <= 1) {
      statusEl.textContent = '1/1';
    } else if (shadowState.repetitions === Infinity) {
      statusEl.textContent = '∞';
    } else {
      const cur = Math.min(shadowState.repetitions, shadowState.completed + 1);
      statusEl.textContent = `${cur}/${shadowState.repetitions}`;
    }
  }
  updateFocusPlayBtn();
}"""

target_chip_group = '<button class="dock-chip" id="focusModeBtn" onclick="toggleFocusMode()" aria-label="Focus mode (Shortcut: P)">Focus</button>'
replacement_chip_group = (
    '<button class="dock-chip" id="focusModeBtn" onclick="toggleFocusMode()" aria-label="Focus mode (Shortcut: P)">Focus</button>\n'
    '          <button class="dock-chip" id="typingModeBtn" onclick="toggleTypingMode()" aria-label="Typing practice mode (Shortcut: K)">Typing</button>'
)

target_shortcuts = """    <div class="shortcuts-table">
      <div class="shortcut-item"><span class="kbd-key">Space</span><span>Play / Pause</span></div>
      <div class="shortcut-item"><span class="kbd-key">← / →</span><span>Previous / Next sentence</span></div>
      <div class="shortcut-item"><span class="kbd-key">[ / ]</span><span>Previous / Next chapter</span></div>
      <div class="shortcut-item"><span class="kbd-key">T</span><span>Toggle Bilingual / English-only mode</span></div>
      <div class="shortcut-item"><span class="kbd-key">R</span><span>Repeat sentence loop</span></div>
      <div class="shortcut-item"><span class="kbd-key">P</span><span>Focus Mode (Immersion)</span></div>
      <div class="shortcut-item"><span class="kbd-key">H / B</span><span>Audio mode (hide text for listening)</span></div>
      <div class="shortcut-item"><span class="kbd-key">Esc</span><span>Dismiss popover / modal</span></div>
    </div>"""

replacement_shortcuts = """    <div class="shortcuts-table">
      <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--accent, #3b82f6); margin-top: 4px; margin-bottom: 2px;">Reading Mode</div>
      <div class="shortcut-item"><span class="kbd-key">Space</span><span>Play / Pause</span></div>
      <div class="shortcut-item"><span class="kbd-key">K</span><span>Typing Mode (Practice)</span></div>
      <div class="shortcut-item"><span class="kbd-key">← / →</span><span>Previous / Next sentence</span></div>
      <div class="shortcut-item"><span class="kbd-key">[ / ]</span><span>Previous / Next chapter</span></div>
      <div class="shortcut-item"><span class="kbd-key">T</span><span>Toggle Bilingual / English-only mode</span></div>
      <div class="shortcut-item"><span class="kbd-key">R</span><span>Repeat sentence loop (1× / 2× / 3× / ∞)</span></div>
      <div class="shortcut-item"><span class="kbd-key">P</span><span>Focus Mode (Immersion)</span></div>
      <div class="shortcut-item"><span class="kbd-key">H / B</span><span>Audio mode (hide text for listening)</span></div>
      <div class="shortcut-item"><span class="kbd-key">Esc</span><span>Dismiss popover / modal</span></div>

      <div style="font-size: 11px; font-weight: 700; text-transform: uppercase; color: var(--accent, #3b82f6); margin-top: 14px; margin-bottom: 2px;">Typing Practice Mode</div>
      <div class="shortcut-item"><span class="kbd-key">Tab</span><span>Play / Pause sentence audio</span></div>
      <div class="shortcut-item"><span class="kbd-key">Shift+Tab</span><span>Restart sentence from beginning</span></div>
      <div class="shortcut-item"><span class="kbd-key">⌘R / Ctrl+R</span><span>Restart current sentence</span></div>
      <div class="shortcut-item"><span class="kbd-key">Ctrl+L</span><span>Cycle Loop (Off / 2× / 3× / ∞)</span></div>
      <div class="shortcut-item"><span class="kbd-key">Ctrl+H</span><span>Trigger Hint (Glow expected char)</span></div>
      <div class="shortcut-item"><span class="kbd-key">Ctrl+Enter</span><span>Skip sentence</span></div>
      <div class="shortcut-item"><span class="kbd-key">Alt+T</span><span>Toggle Translation marginalia</span></div>
      <div class="shortcut-item"><span class="kbd-key">Esc</span><span>Exit Typing Mode</span></div>
    </div>"""

def inject_typing_mode_to_html(content: str, *, remote_passkey_gate: bool = False) -> str:
    """Inject the complete interactive typing practice engine into an existing reader HTML."""
    if remote_passkey_gate:
        content = safe_replace("passkey_gate", content, '../../assets/js/passkey-gate.js', 'https://audiblelibrary.online/assets/js/passkey-gate.js')

    # Enable infinite loop '∞' in reader repeat logic
    content = safe_replace(
        "main_rep_levels",
        content,
        'const MAIN_REP_LEVELS = [1, 2, 3];',
        'const MAIN_REP_LEVELS = [1, 2, 3, Infinity];'
    )
    content = safe_replace(
        "focus_rep_levels",
        content,
        'const FOCUS_REP_LEVELS = [1, 2, 3];',
        'const FOCUS_REP_LEVELS = [1, 2, 3, Infinity];'
    )

    content = safe_replace("set_rep", content, target_set_rep, replacement_set_rep)
    content = safe_replace("render_rep", content, target_render_rep, replacement_render_rep)
    content = safe_replace("focus_status", content, target_focus_status, replacement_focus_status)
    content = safe_replace("chip_group", content, target_chip_group, replacement_chip_group)
    content = safe_replace("shortcuts_table", content, target_shortcuts, replacement_shortcuts)

    idx = content.rfind('</body>')
    if idx != -1:
        return content[:idx] + proto_code + content[idx:]
    else:
        return content + proto_code

if __name__ == '__main__':
    default_source = '/Users/lindy/Vault/Audible/books/misbehaving/index.html'
    source_path = sys.argv[1] if len(sys.argv) > 1 else os.environ.get('BOOK_INDEX_PATH', default_source)
    default_target_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'outputs')
    target_dir = sys.argv[2] if len(sys.argv) > 2 else os.environ.get('OUTPUT_DIR', default_target_dir)
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, 'prototype-typing-reader.html')

    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()

    new_content = inject_typing_mode_to_html(content, remote_passkey_gate=True)

    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Re-compiled prototype V16 (Grill Hardened O(1) Fast Engine): {target_path}")
