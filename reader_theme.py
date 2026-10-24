"""Interactive Audiobook Reader Design Tokens & Theme Stylesheets."""

def get_reader_css() -> str:
    return """
:root {
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
  --dock-max-width: calc(var(--max-content-width) - var(--space-2xl) * 2);
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

  /* --- Focus Immersion Mode Tokens (Theme-Harmonized & Invariant) --- */
  --focus-bg: var(--bg-page);
  --focus-text: var(--text-main);
  --focus-text-trans: var(--text-sub);
  --focus-font-scale: 1;
  --focus-title: var(--text-sub);
  --focus-status: var(--accent);
  --focus-hint: var(--text-sub);
  --focus-dock-bg: var(--bg-panel-glass);
  --focus-dock-border: var(--border);
  --focus-btn-bg: var(--bg-panel);
  --focus-btn-border: var(--border-subtle);
  --focus-btn-text: var(--text-main);
  --focus-btn-active-bg: var(--bg-hover);
  --focus-btn-active-border: var(--accent);
  --focus-btn-active-text: var(--accent);
  --focus-close-hover: var(--text-main);
  --focus-word-active-bg: var(--word-highlight-bg);
  --focus-word-active-text: var(--word-highlight-text);
  --focus-exit-bg: var(--bg-panel);
  --focus-exit-border: var(--border);
  --focus-exit-text: var(--text-main);
  --focus-exit-active-bg: var(--bg-hover);
  --focus-exit-active-text: var(--accent);
  --focus-exit-holding-border: var(--accent);
  --focus-progress-bg: var(--accent-light);

  /* --- Backward-compatible Pocket Mode Aliases --- */
  --pocket-bg: var(--focus-bg);
  --pocket-title: var(--focus-title);
  --pocket-status: var(--focus-status);
  --pocket-hint: var(--focus-hint);
  --pocket-btn-bg: var(--focus-exit-bg);
  --pocket-btn-border: var(--focus-exit-border);
  --pocket-btn-text: var(--focus-exit-text);
  --pocket-btn-active-bg: var(--focus-exit-active-bg);
  --pocket-btn-active-text: var(--focus-exit-active-text);

  /* --- Theme Swatch Tokens for Boxless Popover (AP2 Compliant) --- */
  --swatch-sepia: #fbf7ee;
  --swatch-sepia-border: #d8d0c0;
  --swatch-light: #ffffff;
  --swatch-light-border: #cbd5e1;
  --swatch-dark: #12151c;
  --swatch-dark-border: #334155;
  --swatch-night: #000000;
  --swatch-night-border: #27272a;
}

/* Theme 1: Sepia (Parchment Paper - Warm & Calming) */
[data-theme="sepia"] {
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
}

/* Theme 2: Light (Studio Clean Day - High Contrast) */
[data-theme="light"] {
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
}

/* Theme 3: Dark (Slate Evening - Preserves #12151c Contract) */
[data-theme="dark"] {
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
}

/* Theme 4: Night (True OLED Obsidian Black) */
[data-theme="night"] {
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
}

* { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font-serif);
  background-color: var(--bg-page);
  color: var(--text-main);
  font-size: var(--font-size-base);
  line-height: var(--line-height-base);
  padding-bottom: var(--space-bottom-clearance);
  transition: background-color var(--transition-smooth), color var(--transition-smooth);
  -webkit-font-smoothing: antialiased;
}

/* Top Sticky Navigation Bar */
.top-nav {
  position: sticky;
  top: 0;
  z-index: var(--z-nav);
  background: var(--bg-page-glass);
  border-bottom: var(--space-3xs) solid var(--border-subtle);
  box-shadow: var(--shadow-nav);
  backdrop-filter: var(--blur-nav);
  -webkit-backdrop-filter: var(--blur-nav);
  transition: background-color var(--transition-smooth), border-color var(--transition-smooth);
}

.nav-bar {
  max-width: var(--max-content-width);
  margin: 0 auto;
  padding: var(--space-sm) var(--space-2xl);
  display: flex;
  justify-content: flex-start;
  align-items: center;
}

.chapter-nav-wrapper {
  position: relative;
  display: inline-flex;
}

.chapter-btn {
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
}

.chapter-btn:hover {
  background: var(--bg-hover);
  border-color: var(--accent-light);
}

#currentChapterLabel {
  font-weight: 600;
  color: var(--text-main);
}

.book-pill-title {
  color: var(--text-sub);
  font-weight: 400;
}

.dropdown-arrow {
  font-size: var(--font-size-xs);
  color: var(--text-sub);
  margin-left: var(--space-2xs);
}

.chapter-dropdown {
  display: none;
  position: absolute;
  top: calc(100% + var(--space-md));
  left: 0;
  width: var(--dropdown-width);
  max-width: calc(100vw - 32px);
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
}

.chapter-dropdown.open {
  display: block;
  animation: dropdownFadeIn var(--transition-dropdown);
}

@keyframes dropdownFadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.chapter-item {
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
}

.chapter-item:hover {
  background: var(--bg-hover);
}

.chapter-item.active {
  background: var(--bg-panel);
  color: var(--accent);
  font-weight: 600;
}

.chapter-item-tag {
  font-size: var(--font-size-2xs);
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.nav-actions {
  display: flex;
  align-items: center;
  gap: var(--space-md);
}

.icon-btn {
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
}

.icon-btn:hover {
  background: var(--bg-hover);
  border-color: var(--accent-light);
}

.icon-btn:active {
  opacity: 0.85;
}

.icon-btn.primary {
  background: var(--accent);
  color: var(--btn-primary-text);
  border-color: var(--accent);
  font-weight: 600;
}

.icon-btn.primary:hover {
  filter: brightness(1.08);
}

/* Bottom Symmetrical Morphing Control Dock (Option B) */
.bottom-control-dock {
  position: fixed;
  bottom: calc(var(--space-base) + env(safe-area-inset-bottom, 16px));
  left: 50%;
  transform: translateX(-50%);
  width: min(var(--dock-max-width), calc(100vw - 32px));
  height: 48px;
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-floating);
  display: flex;
  flex-direction: column;
  padding: 0 var(--space-sm) 0 var(--space-xs);
  z-index: 1100;
  box-sizing: border-box;
  overflow: hidden;
  transition: transform 0.32s cubic-bezier(0.16, 1, 0.3, 1),
              opacity 0.28s ease,
              height 0.28s cubic-bezier(0.16, 1, 0.3, 1),
              border-radius 0.28s cubic-bezier(0.16, 1, 0.3, 1),
              padding 0.28s cubic-bezier(0.16, 1, 0.3, 1),
              box-shadow 0.28s cubic-bezier(0.16, 1, 0.3, 1);
}

.bottom-control-dock.dock-idle-hidden {
  transform: translateX(-50%) translateY(calc(100% + var(--space-2xl)));
  opacity: 0;
  pointer-events: none;
}

.bottom-control-dock.expanded {
  height: 102px;
  border-radius: var(--radius-xl);
  padding: 0 var(--space-md);
  box-shadow: var(--shadow-floating);
}

.dock-primary-row {
  height: 48px;
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  flex-shrink: 0;
}

.dock-play-btn {
  height: 36px;
  min-width: 36px;
  padding: 0 var(--space-md);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2xs);
  background: var(--accent);
  color: var(--btn-primary-text);
  border: none;
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--font-size-xs);
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
  box-shadow: var(--shadow-subtle);
  transition: transform var(--transition-fast), filter var(--transition-fast);
}

.dock-play-btn:hover {
  filter: brightness(1.08);
}

.dock-play-btn:active {
  opacity: 0.88;
}

.dock-chip {
  height: 32px;
  min-width: 32px;
  padding: 0 var(--space-sm);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  border-radius: var(--radius-pill);
  color: var(--text-main);
  font-family: var(--font-sans);
  font-size: var(--font-size-xs);
  font-weight: 500;
  font-variant-numeric: tabular-nums;
  cursor: pointer;
  flex-shrink: 0;
  transition: all var(--transition-fast);
  user-select: none;
}

.dock-chip:hover {
  background: var(--bg-hover);
  border-color: var(--accent-light);
}

.dock-chip:active {
  opacity: 0.88;
}

.dock-chip.active {
  background: var(--accent);
  color: var(--btn-primary-text);
  border-color: var(--accent);
  font-weight: 600;
}

.dock-rep-icon {
  width: 13px;
  height: 13px;
  display: block;
  flex-shrink: 0;
  stroke: currentColor;
}

.dock-chip .rep-badge {
  font-size: var(--font-size-2xs);
  font-weight: 700;
  line-height: 1;
  margin-left: var(--space-2xs);
}

.dock-scrubber-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  gap: var(--space-xs);
  min-width: 0;
  padding: 0 var(--space-2xs);
}

.dock-time {
  font-family: var(--font-sans);
  font-size: var(--font-size-2xs);
  font-variant-numeric: tabular-nums;
  color: var(--text-sub);
  user-select: none;
  flex-shrink: 0;
}

/* Morphing Expanded Content Row (Aliased with .control-drawer) */
.dock-expanded-content,
.control-drawer {
  display: none;
  opacity: 0;
  width: 100%;
  flex-shrink: 0;
  transition: opacity 0.22s cubic-bezier(0.16, 1, 0.3, 1) 0.05s;
}

.bottom-control-dock.expanded .dock-expanded-content,
.bottom-control-dock.expanded .control-drawer,
.control-drawer.open {
  display: flex;
  flex-direction: column;
  opacity: 1;
}

.dock-hairline {
  width: 100%;
  height: var(--space-3xs);
  background: var(--border-subtle);
  margin: 0;
  flex-shrink: 0;
}

.dock-expanded-grid {
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  padding: 0 var(--space-xs);
  box-sizing: border-box;
}

.dock-sub-row {
  display: inline-flex;
  align-items: center;
  gap: var(--space-md);
}

.dock-sub-hairline {
  display: none;
}

.dock-chip-group {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
}

.dock-chip-group .pill-btn,
.dock-chip-group .dock-chip {
  height: 28px;
  padding: 0 var(--space-sm);
  font-size: var(--font-size-xs);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  border-radius: var(--radius-pill);
  color: var(--text-main);
  font-family: var(--font-sans);
  cursor: pointer;
  transition: all var(--transition-fast);
  user-select: none;
}

.dock-chip-group .pill-btn:hover,
.dock-chip-group .dock-chip:hover {
  background: var(--bg-hover);
  border-color: var(--accent-light);
}

.dock-chip-group .pill-btn.active,
.dock-chip-group .dock-chip.active {
  background: var(--accent);
  color: var(--btn-primary-text);
  border-color: var(--accent);
  font-weight: 600;
}

.dock-expanded-grid .toggle-pill {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.dock-expanded-grid .toggle-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  height: 26px;
  padding: 0 var(--space-sm);
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--font-size-2xs);
  color: var(--text-sub);
  transition: all var(--transition-fast);
}

.dock-expanded-grid .toggle-pill input[type="checkbox"]:checked + .toggle-badge {
  background: var(--bg-hover);
  border-color: var(--accent-light);
  color: var(--accent);
}

.dock-theme-group {
  display: inline-flex;
  align-items: center;
  gap: var(--space-md);
}

.theme-swatches {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
}

.theme-dot {
  width: 18px;
  height: 18px;
  border-radius: var(--radius-full);
  border: var(--space-3xs) solid var(--border-subtle);
  cursor: pointer;
  padding: 0;
  box-sizing: border-box;
  transition: transform var(--transition-fast), border-color var(--transition-fast);
}

.theme-dot:hover {
  box-shadow: 0 0 0 2px var(--accent-light);
}

.theme-dot.active {
  border: 2px solid var(--accent);
  box-shadow: 0 0 0 1px var(--accent-light);
}

.theme-dot-sepia {
  background: var(--swatch-sepia);
  border-color: var(--swatch-sepia-border);
}

.theme-dot-light {
  background: var(--swatch-light);
  border-color: var(--swatch-light-border);
}

.theme-dot-dark {
  background: var(--swatch-dark);
  border-color: var(--swatch-dark-border);
}

.theme-dot-night {
  background: var(--swatch-night);
  border-color: var(--swatch-night-border);
}

.dock-text-link {
  background: none;
  border: none;
  padding: 0;
  font-family: var(--font-sans);
  font-size: var(--font-size-2xs);
  color: var(--text-sub);
  cursor: pointer;
  opacity: 0.8;
  transition: opacity var(--transition-fast), color var(--transition-fast);
}

.dock-text-link:hover {
  opacity: 1;
  color: var(--accent);
}

@media (max-width: 480px) {
  .bottom-control-dock {
    height: 44px;
    padding: 0 var(--space-xs);
  }
  .bottom-control-dock.expanded {
    height: 144px;
    padding: 0 var(--space-md) var(--space-2xs);
  }
  .dock-primary-row {
    height: 44px;
    gap: var(--space-2xs);
  }
  .dock-play-btn {
    height: 32px;
    padding: 0 var(--space-xs);
    font-size: var(--font-size-2xs);
  }
  .dock-chip {
    height: 28px;
    padding: 0 var(--space-xs);
    font-size: var(--font-size-2xs);
  }
  .dock-time {
    display: none;
  }
  .dock-expanded-grid {
    height: auto;
    display: flex;
    flex-direction: column;
    padding: 0;
    gap: 0;
  }
  .dock-sub-row {
    height: 44px;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .dock-sub-hairline {
    display: block;
    width: 100%;
    height: var(--space-3xs);
    background: var(--border-subtle);
  }
  .dock-chip-group .pill-btn,
  .dock-chip-group .dock-chip {
    height: 28px;
    padding: 0 var(--space-sm);
    font-size: var(--font-size-xs);
  }
  .dock-expanded-grid .toggle-badge {
    min-height: 26px;
    height: 26px;
    padding: 0 var(--space-sm);
    font-size: var(--font-size-2xs);
  }
  .dock-theme-group {
    width: 100%;
    justify-content: space-between;
  }
  .theme-dot {
    width: 18px;
    height: 18px;
  }
  .dock-text-link {
    font-size: var(--font-size-xs);
  }
}

/* Shortcuts Centered Modal */
.shortcuts-modal-overlay {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--focus-overlay-bg);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  z-index: 2000;
  align-items: center;
  justify-content: center;
}

.shortcuts-modal-overlay.open {
  display: flex;
  animation: fadeIn var(--transition-fast);
}

.shortcuts-modal {
  width: min(440px, calc(100vw - 32px));
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-floating);
  padding: var(--space-xl);
  box-sizing: border-box;
}

.shortcuts-modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-base);
}

.shortcuts-modal-title {
  font-family: var(--font-sans);
  font-size: var(--font-size-base);
  font-weight: 600;
  color: var(--text-main);
}

.shortcuts-modal-close {
  background: none;
  border: none;
  color: var(--text-sub);
  font-size: var(--font-size-base);
  cursor: pointer;
  padding: var(--space-3xs);
  line-height: 1;
  transition: color var(--transition-fast);
}

.shortcuts-modal-close:hover {
  color: var(--text-main);
}

.shortcuts-table {
  display: flex;
  flex-direction: column;
  gap: var(--space-sm);
}

.shortcut-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-md);
  font-family: var(--font-sans);
  font-size: var(--font-size-xs);
  color: var(--text-sub);
}

.shortcut-item .kbd-key {
  min-width: 44px;
  text-align: center;
}

@media (max-width: 480px) {
  .shortcuts-modal {
    padding: var(--space-lg) var(--space-base);
  }
  .shortcut-item {
    font-size: var(--font-size-2xs);
    gap: var(--space-xs);
  }
  .shortcut-item .kbd-key {
    min-width: 32px;
    font-size: var(--font-size-2xs);
    padding: 2px var(--space-2xs);
  }
}

.s-key {
  font-family: var(--font-sans);
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--text-main);
  background: var(--bg-hover);
  border: var(--space-3xs) solid var(--border-subtle);
  border-radius: var(--radius-sm);
  padding: 2px var(--space-xs);
  flex-shrink: 0;
  min-width: 44px;
  text-align: center;
}

.s-desc {
  font-family: var(--font-sans);
  font-size: var(--font-size-xs);
  color: var(--text-sub);
  text-align: right;
}

.hidden-audio {
  position: fixed !important;
  top: -9999px !important;
  left: -9999px !important;
  width: 1px !important;
  height: 1px !important;
  opacity: 0.001 !important;
  pointer-events: none !important;
  z-index: -100 !important;
  display: block !important;
}

.audio-player-bar {
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
}

.player-speed-btn {
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
}

.player-speed-btn:hover {
  background: var(--accent);
  color: var(--btn-primary-text);
  border-color: var(--accent);
  filter: brightness(1.08);
}

.player-speed-btn:active {
  opacity: 0.85;
}

.player-speed-btn.custom-speed {
  background: var(--accent);
  color: var(--btn-primary-text);
  border-color: var(--accent);
}

.player-time {
  font-family: var(--font-sans);
  font-size: var(--font-size-xs);
  color: var(--text-sub);
  font-variant-numeric: tabular-nums;
  min-width: var(--space-7xl);
  text-align: center;
  flex-shrink: 0;
  user-select: none;
}

.player-slider-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  position: relative;
  min-width: 0;
}

.player-slider {
  -webkit-appearance: none;
  appearance: none;
  width: 100%;
  height: var(--space-xs);
  background: var(--border);
  border-radius: var(--radius-full);
  outline: none;
  cursor: pointer;
  margin: 0;
}

.player-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: var(--space-lg);
  height: var(--space-lg);
  border-radius: var(--radius-full);
  background: var(--accent);
  cursor: pointer;
  box-shadow: var(--shadow-kbd);
  transition: filter var(--transition-fast);
}

.player-slider::-webkit-slider-thumb:hover {
  filter: brightness(1.15);
}

.player-slider::-moz-range-thumb {
  width: var(--space-lg);
  height: var(--space-lg);
  border: none;
  border-radius: var(--radius-full);
  background: var(--accent);
  cursor: pointer;
  box-shadow: var(--shadow-kbd);
  transition: filter var(--transition-fast);
}

.player-slider::-moz-range-thumb:hover {
  filter: brightness(1.15);
}

.drawer-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-md);
  width: 100%;
}

.drawer-group {
  display: contents;
}

.segmented-control {
  display: inline-flex;
  align-items: center;
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  border-radius: var(--radius-pill);
  padding: var(--space-2xs) var(--space-xs);
  box-shadow: var(--shadow-subtle);
}

.seg-btn {
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
}

.seg-btn:hover {
  background: var(--bg-hover);
}

.seg-btn:active {
  opacity: 0.85;
}

.seg-btn.active {
  background: var(--bg-hover);
  color: var(--accent);
  font-weight: 600;
}

.seg-divider {
  width: var(--space-3xs);
  height: var(--seg-divider-height);
  background: var(--border-subtle);
  margin: 0 var(--space-3xs);
}

.seg-select {
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
}

.pill-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 42px;
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  color: var(--text-main);
  padding: 0 var(--space-md);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--font-size-sm);
  font-weight: 500;
  cursor: pointer;
  box-shadow: var(--shadow-subtle);
  transition: all var(--transition-fast);
  line-height: var(--line-height-btn);
  box-sizing: border-box;
  text-align: center;
}

.pill-btn:hover {
  background: var(--bg-hover);
  border-color: var(--accent-light);
}

.pill-btn:active {
  opacity: 0.88;
}

.pill-btn.active {
  background: var(--accent);
  color: var(--btn-primary-text);
  border-color: var(--accent);
  font-weight: 600;
}

.toggle-pill {
  display: inline-flex;
  width: 100%;
  cursor: pointer;
  user-select: none;
}

.toggle-pill input[type="checkbox"] {
  display: none;
}

.toggle-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: 42px;
  gap: var(--space-xs);
  background: var(--bg-page);
  border: var(--space-3xs) solid var(--border-subtle);
  color: var(--text-sub);
  padding: 0 var(--space-md);
  border-radius: var(--radius-pill);
  font-family: var(--font-sans);
  font-size: var(--font-size-sm);
  font-weight: 500;
  box-shadow: var(--shadow-subtle);
  transition: all var(--transition-base);
  line-height: var(--line-height-btn);
  box-sizing: border-box;
  text-align: center;
}

.toggle-pill input[type="checkbox"]:checked + .toggle-badge {
  color: var(--text-main);
  border-color: var(--accent-light);
  background: var(--bg-hover);
}

.toggle-pill input[type="checkbox"]:checked + .toggle-badge::before {
  content: "";
  display: inline-block;
  width: var(--space-sm);
  height: var(--space-sm);
  border-radius: var(--radius-full);
  background-color: var(--accent);
  margin-right: var(--space-xs);
}

.drawer-tips {
  display: none;
  font-family: var(--font-sans);
  font-size: var(--font-size-sm);
  background: var(--bg-page);
  padding: var(--space-2xl) var(--space-3xl);
  border-radius: var(--radius-lg);
  border: var(--space-3xs) solid var(--border-subtle);
  box-shadow: var(--shadow-drawer-box);
  animation: drawerSlideDown var(--transition-base);
}

.drawer-tips.open {
  display: block;
}

.tips-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4xl);
}

@media (max-width: 600px) {
  .control-drawer,
  .control-popover {
    right: 0;
    width: 270px;
    max-width: calc(100vw - 32px);
    padding: var(--space-base);
  }
  .tips-columns {
    grid-template-columns: 1fr;
    gap: var(--space-xl);
  }
}

.tips-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-md);
}

.tips-section-title {
  font-size: var(--font-size-xs);
  font-weight: 700;
  color: var(--accent);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: var(--space-2xs);
  padding-bottom: var(--space-xs);
  border-bottom: var(--space-3xs) solid var(--border-subtle);
}

.tips-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-lg);
  font-size: var(--font-size-sm);
  color: var(--text-main);
  line-height: var(--line-height-normal);
}

.kbd-key {
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
}

/* Main Layout */
.container {
  max-width: var(--max-content-width);
  margin: var(--space-5xl) auto;
  padding: 0 var(--space-3xl);
}

.chapter-section {
  display: none;
}

.chapter-section.active {
  display: block;
}

.book-header {
  text-align: center;
  margin-bottom: var(--space-7xl);
  padding-bottom: var(--space-3xl);
  border-bottom: var(--space-3xs) solid var(--border);
}

.book-subtitle {
  font-family: var(--font-sans);
  font-size: var(--font-size-ui);
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: var(--accent);
  margin-bottom: var(--space-md);
}

.book-chapter-label {
  font-family: var(--font-sans);
  font-size: var(--font-size-2xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  color: var(--accent);
  margin-bottom: var(--space-xs);
}

.book-title {
  font-size: var(--font-size-h1);
  font-weight: 700;
  line-height: var(--line-height-tight);
  margin-bottom: var(--space-base);
}

.book-author {
  font-family: var(--font-sans);
  font-size: var(--font-size-sub);
  color: var(--text-sub);
}

/* Center-Stage Reading Canvas */
.reader-main {
  width: 100%;
  max-width: var(--max-content-width, 740px);
  margin: var(--space-5xl) auto var(--space-bottom-clearance);
  padding: 0 var(--space-2xl);
  box-sizing: border-box;
  position: relative;
}

.chapter-section {
  position: relative;
  width: 100%;
}

.chapter-layout {
  display: block;
  width: 100%;
  margin: 0 auto;
}

.prose-column {
  width: 100%;
  margin: 0 auto;
}

.prose-p {
  margin-bottom: var(--space-4xl);
  line-height: var(--line-height-base);
  font-size: var(--font-size-base);
  font-family: var(--font-serif);
  color: var(--text-main);
  text-align: left;
}

.prose-heading-block {
  margin-top: var(--space-5xl);
  margin-bottom: var(--space-xl);
}

.prose-epigraph-block {
  margin: var(--space-3xl) 0;
  padding-left: var(--space-xl);
  border-left: var(--space-xs) solid var(--border);
}

/* Inline Sentence Units */
.sentence-unit.s-inline {
  display: inline;
  margin-bottom: 0;
  content-visibility: visible;
  contain-intrinsic-size: none;
  border-radius: var(--radius-xs);
  transition: background var(--transition-fast);
  cursor: pointer;
}

.sentence-unit.s-inline .sentence-text {
  display: inline;
  padding: 1px 2px;
  border-radius: var(--radius-xs);
  transition: background var(--transition-fast);
}

.sentence-unit.s-inline:hover .sentence-text {
  background: var(--bg-hover);
}

.sentence-unit.s-inline.active .sentence-text {
  background: var(--bg-panel);
}

.sentence-unit.s-inline .inspect-panel {
  display: none !important;
}

/* Fallback for block sentence units */
.sentence-unit:not(.s-inline) {
  margin-bottom: var(--space-lg);
  border-radius: var(--radius-base);
  transition: background var(--transition-fast);
  content-visibility: auto;
  contain-intrinsic-size: 0 72px;
}

.sentence-unit:not(.s-inline).active {
  content-visibility: visible;
}

.sentence-unit:not(.s-inline) .sentence-text {
  cursor: pointer;
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}

.sentence-unit:not(.s-inline) .sentence-text:hover {
  background: var(--bg-hover);
}

.sentence-unit:not(.s-inline).active .sentence-text {
  background: var(--bg-panel);
}

.sentence-unit[data-matched="0"] .sentence-text {
  opacity: 0.88;
}

/* Baseline-Aligned Dynamic Marginalia Note */
.marginalia-note {
  position: absolute;
  left: calc(100% + var(--space-xl));
  width: clamp(220px, calc(50vw - 370px - 32px), 300px);
  top: 0;
  opacity: 0;
  pointer-events: none;
  transform: translateX(-4px);
  transition: top 0.22s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease, transform 0.2s ease;
  z-index: 100;
  background: transparent;
  border: none;
  padding: 0;
}

.marginalia-note.visible {
  opacity: 1;
  pointer-events: auto;
  transform: translateX(0);
}

.marginalia-trans {
  font-family: var(--font-serif);
  font-size: var(--font-size-sub);
  line-height: var(--line-height-relaxed);
  color: var(--text-main);
  margin-bottom: var(--space-xs);
  letter-spacing: 0.01em;
}

.marginalia-vocab {
  border-top: var(--space-3xs) solid var(--border-subtle);
  padding-top: var(--space-xs);
  margin-top: var(--space-xs);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.marginalia-vocab:empty {
  display: none !important;
}

.marginalia-vocab .vocab-row {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  column-gap: var(--space-xs);
  row-gap: 2px;
}

.marginalia-vocab .v-word {
  font-family: var(--font-sans);
  font-weight: 600;
  font-size: var(--font-size-xs);
  color: var(--accent);
}

.marginalia-vocab .v-pos {
  font-style: italic;
  color: var(--text-sub);
  font-size: var(--font-size-2xs);
}

.marginalia-vocab .v-def {
  width: 100%;
  color: var(--text-sub);
  font-size: var(--font-size-xs);
  line-height: var(--line-height-normal);
}

/* Mobile responsive fallback (< 1200px viewport) */
@media (max-width: 1199px) {
  .marginalia-note {
    left: var(--space-xl);
    right: var(--space-xl);
    bottom: calc(var(--space-base) + 48px + var(--space-sm) + env(safe-area-inset-bottom, 16px));
    top: auto !important;
    position: fixed;
    width: auto;
    max-width: 540px;
    margin: 0 auto;
    background: var(--bg-panel-glass);
    backdrop-filter: var(--blur-drawer);
    -webkit-backdrop-filter: var(--blur-drawer);
    border: var(--space-3xs) solid var(--border);
    border-radius: var(--radius-lg);
    padding: var(--space-base) var(--space-xl);
    box-shadow: var(--shadow-floating);
    transform: translateY(8px);
    z-index: 1500;
  }
  .marginalia-note.visible {
    transform: translateY(0);
  }
}

[data-hide-chinese="true"] .marginalia-note:not(.visible) {
  display: none !important;
}

.scene-divider {
  text-align: center;
  margin: 2.2rem 0;
  color: var(--text-muted);
  letter-spacing: 0.5em;
  font-size: 0.95rem;
  user-select: none;
  opacity: 0.7;
}

.editorial-notice-box {
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
}

.editorial-notice-box .notice-icon {
  font-size: 1.15rem;
  flex-shrink: 0;
}

.editorial-notice-box .notice-content {
  flex: 1;
}

#reader-toast {
  display: none !important;
}

/* Focus & Pocket Mode Overlay (Single-Sentence Immersion Theater) */
#focus-overlay,
#pocket-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  width: 100dvw;
  height: 100dvh;
  background-color: var(--focus-bg);
  color: var(--focus-text);
  z-index: 2147483647;
  display: none;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  padding: env(safe-area-inset-top, var(--space-xl)) var(--space-xl) env(safe-area-inset-bottom, var(--space-xl)) var(--space-xl);
  box-sizing: border-box;
  user-select: none;
  -webkit-user-select: none;
  touch-action: pan-y;
}

.focus-top-bar,
.focus-header,
.pocket-header {
  width: 100%;
  max-width: 900px;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  padding: var(--space-sm) 0;
  box-sizing: border-box;
}

.focus-title,
.pocket-title {
  display: none !important;
}

.focus-close-icon,
.pocket-close-icon {
  background: transparent;
  color: var(--focus-title);
  border: none;
  font-size: var(--font-size-h3);
  cursor: pointer;
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-sm);
  line-height: 1;
  transition: color var(--transition-fast);
}

.focus-close-icon:hover,
.pocket-close-icon:hover {
  color: var(--focus-close-hover);
}

/* Centered Sentence Immersion Box */
.focus-sentence-container,
.pocket-sentence-container {
  flex: 1;
  width: 100%;
  max-width: clamp(860px, 80vw, 1080px);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  padding: var(--space-lg) var(--space-base);
  box-sizing: border-box;
  overflow: hidden;
}

.focus-sentence-box,
.pocket-sentence-box {
  width: 100%;
  text-align: left;
  cursor: pointer;
  padding: var(--space-md) var(--space-base);
  border-radius: var(--radius-lg);
  max-height: calc(100vh - 160px);
  max-height: calc(100dvh - 160px);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  transition: background var(--transition-fast);
}

.focus-sentence-text,
.pocket-sentence-text {
  font-family: var(--font-serif);
  font-size: calc(clamp(1.25rem, 2.8vw, 1.85rem) * var(--focus-font-scale, 1));
  line-height: 1.55;
  color: var(--focus-text);
  font-weight: 500;
  letter-spacing: -0.01em;
  margin-bottom: var(--space-lg);
  text-align: left;
  transition: filter var(--transition-base), opacity var(--transition-base), font-size var(--transition-fast);
}

.focus-sentence-text .w,
.pocket-sentence-text .w {
  display: inline;
  transition: background-color var(--transition-fast);
}

/* ZERO LAYOUT JITTER (AP4): Strictly zero padding to prevent horizontal font expansion and reflow */
.focus-sentence-text .active-word,
.pocket-sentence-text .active-word {
  background-color: var(--focus-word-active-bg) !important;
  color: var(--focus-word-active-text) !important;
  border-radius: var(--radius-xs);
  padding: 0 !important;
  margin: 0 !important;
}

.focus-sentence-trans,
.pocket-sentence-trans {
  font-family: var(--font-sans);
  font-size: clamp(0.92rem, 1.8vw, 1.05rem);
  line-height: 1.6;
  color: var(--focus-text-trans);
  font-weight: 400;
  max-width: 860px;
  text-align: left;
  margin: 0;
  transition: opacity var(--transition-base);
}

.focus-sentence-vocab {
  margin-top: var(--space-md);
  padding-top: var(--space-sm);
  border-top: var(--space-3xs) solid var(--border-subtle);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
  max-width: 860px;
  width: 100%;
  text-align: left;
  transition: opacity var(--transition-base);
}

.focus-sentence-vocab .vocab-row {
  font-family: var(--font-sans);
  font-size: clamp(0.85rem, 1.5vw, 0.95rem);
  line-height: var(--line-height-normal);
  display: flex;
  align-items: baseline;
  gap: var(--space-sm);
}

/* Independent Translation & Vocab Visibility Toggle */
#focus-overlay.hide-trans .focus-sentence-trans,
#pocket-overlay.hide-trans .pocket-sentence-trans,
#focus-overlay.hide-trans .focus-sentence-vocab,
#pocket-overlay.hide-trans .focus-sentence-vocab {
  display: none !important;
}

/* Blind Mode (Active Recall Blur) */
#focus-overlay.blind-mode .focus-sentence-text,
#pocket-overlay.blind-mode .pocket-sentence-text {
  filter: blur(14px);
  opacity: 0.15;
}

#focus-overlay.blind-mode .focus-sentence-trans,
#pocket-overlay.blind-mode .pocket-sentence-trans,
#focus-overlay.blind-mode .focus-sentence-vocab,
#pocket-overlay.blind-mode .focus-sentence-vocab {
  opacity: 0;
  pointer-events: none;
}

#focus-overlay.blind-mode .focus-sentence-box.revealed .focus-sentence-text,
#pocket-overlay.blind-mode .focus-sentence-box.revealed .pocket-sentence-text {
  filter: blur(0);
  opacity: 1;
}

#focus-overlay.blind-mode:not(.hide-trans) .focus-sentence-box.revealed .focus-sentence-trans,
#pocket-overlay.blind-mode:not(.hide-trans) .pocket-sentence-box.revealed .focus-sentence-trans,
#focus-overlay.blind-mode:not(.hide-trans) .focus-sentence-box.revealed .focus-sentence-vocab,
#pocket-overlay.blind-mode:not(.hide-trans) .pocket-sentence-box.revealed .focus-sentence-vocab {
  opacity: 1;
}

/* Floating Bottom Control Dock (AP1 & AP5 Pill Dock) */
.focus-dock {
  display: inline-flex;
  align-items: center;
  gap: var(--space-xs);
  background: var(--focus-dock-bg);
  border: var(--space-3xs) solid var(--focus-dock-border);
  border-radius: var(--radius-pill);
  padding: var(--space-2xs) var(--space-sm);
  box-shadow: var(--shadow-subtle);
  margin-bottom: var(--space-md);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  user-select: none;
  -webkit-user-select: none;
  transition: opacity var(--transition-base), transform var(--transition-base);
}

.focus-dock.dock-hidden {
  opacity: 0;
  transform: translateY(16px);
  pointer-events: none;
}

.focus-dock-btn,
.focus-tool-btn,
.pocket-tool-btn {
  background: none;
  border: none;
  color: var(--focus-btn-text);
  font-family: var(--font-sans);
  font-size: var(--font-size-ui);
  font-weight: 500;
  padding: var(--space-xs) var(--space-md);
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: all var(--transition-fast);
  line-height: var(--line-height-btn);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 38px;
  min-height: 36px;
}

.focus-dock-btn:hover,
.focus-tool-btn:hover,
.pocket-tool-btn:hover {
  background: var(--bg-hover);
  color: var(--accent);
}

.focus-dock-btn:active,
.focus-tool-btn:active,
.pocket-tool-btn:active {
  opacity: 0.85;
}

.focus-dock-btn.active,
.focus-tool-btn.active,
.pocket-tool-btn.active {
  background: var(--bg-hover);
  color: var(--accent);
  font-weight: 600;
}

.focus-rep-pill {
  font-weight: 600;
  letter-spacing: 0.02em;
}

.focus-dock-play {
  font-size: 1.05rem;
}

/* Mobile Responsive Optimization (Width Recovery & Comfortable Line Span) */
@media (max-width: 640px) {
  #focus-overlay,
  #pocket-overlay {
    padding: env(safe-area-inset-top, 12px) 12px env(safe-area-inset-bottom, 12px) 12px;
  }
  .focus-sentence-container,
  .pocket-sentence-container {
    padding: var(--space-xs) var(--space-2xs);
  }
  .focus-sentence-box,
  .pocket-sentence-box {
    padding: var(--space-xs) var(--space-2xs);
    max-height: calc(100vh - 130px);
    max-height: calc(100dvh - 130px);
  }
  .focus-sentence-text,
  .pocket-sentence-text {
    font-size: calc(clamp(1.10rem, 3.8vw, 1.25rem) * var(--focus-font-scale, 1));
    line-height: 1.58;
    margin-bottom: var(--space-md);
  }
  .focus-sentence-trans,
  .pocket-sentence-trans {
    font-size: 0.92rem;
    line-height: 1.55;
  }
  .focus-dock {
    gap: 3px;
    padding: 3px 6px;
    margin-bottom: var(--space-xs);
    max-width: calc(100vw - 20px);
    max-width: calc(100dvw - 20px);
    flex-wrap: nowrap;
  }
  .focus-dock-btn {
    padding: 5px 7px;
    min-width: 28px;
    min-height: 32px;
    font-size: 0.80rem;
  }
}

.w {
  display: inline;
  border-radius: var(--radius-xs);
  box-decoration-break: clone;
  -webkit-box-decoration-break: clone;
}

.w.active-word {
  background-color: var(--word-highlight-bg) !important;
  color: var(--word-highlight-text) !important;
  border-radius: var(--radius-xs);
}

/* Collapsible Inspection Card */
.inspect-panel {
  display: none;
  background: var(--bg-panel);
  border-left: var(--space-xs) solid var(--accent);
  border-radius: 0 var(--radius-base) var(--radius-base) 0;
  padding: var(--space-base) var(--space-xl);
  margin: var(--space-sm) 0 var(--space-xl) var(--space-sm);
  box-shadow: var(--card-shadow);
  cursor: pointer;
}

.sentence-unit.active:not(.card-collapsed) .inspect-panel {
  display: block;
}

/* Global Chinese Lock (Pure English Listening Mode) */
[data-hide-chinese="true"] .inspect-panel {
  display: none !important;
}


.inspect-trans {
  font-family: var(--font-serif);
  font-size: var(--font-size-trans);
  line-height: var(--line-height-relaxed);
  color: var(--text-main);
  margin-bottom: var(--space-md);
}

.inspect-vocab-list {
  border-top: var(--space-3xs) solid var(--border);
  padding-top: var(--space-sm);
  margin-top: var(--space-sm);
  display: flex;
  flex-direction: column;
  gap: var(--space-xs);
}

.vocab-row {
  font-family: var(--font-sans);
  font-size: var(--font-size-sm);
  line-height: var(--line-height-normal);
  display: flex;
  align-items: baseline;
  gap: var(--space-sm);
}

.v-word {
  font-weight: 700;
  color: var(--accent);
}

.v-pos {
  font-size: var(--font-size-xs);
  color: var(--text-sub);
  font-style: italic;
}

.v-def {
  color: var(--text-main);
}

.chapter-heading-1 {
  display: inline-block;
  font-size: var(--font-size-h2);
  font-weight: 700;
  color: var(--accent);
  border-bottom: var(--space-3xs) solid var(--border);
  padding-bottom: var(--space-xs);
  cursor: pointer;
  letter-spacing: -0.01em;
  line-height: var(--line-height-tight);
}

.chapter-intext-heading {
  font-family: var(--font-sans);
  font-size: var(--font-size-h3);
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--accent);
  text-align: center;
  margin: var(--space-4xl) 0 var(--space-2xl);
  padding: var(--space-md) var(--space-lg);
}

.epigraph-citation {
  font-style: italic;
  color: var(--text-sub);
  font-size: var(--font-size-sub);
  margin-bottom: var(--space-3xl);
}

/* Mobile Specific Refinements */
@media (max-width: 640px) {
  :root {
    --font-size-base: 1.15rem;
    --line-height-base: 1.82;
  }
  .container {
    padding: 0 var(--space-xl);
    margin: var(--space-2xl) auto;
  }
  .book-title {
    font-size: 1.65rem;
  }
  .nav-bar {
    padding: var(--space-sm) var(--space-lg);
  }
  .icon-btn {
    padding: var(--space-xs) var(--space-base);
    font-size: 0.78rem;
  }
  .chapter-btn {
    font-size: var(--font-size-ui);
  }
  .chapter-dropdown {
    width: 240px;
  }
}

/* Landscape Mobile Optimization (Short Viewport Ergonomics) */
@media (max-height: 520px) and (orientation: landscape) {
  :root {
    --font-size-base: 1.05rem;
    --line-height-base: 1.6;
  }
  .reader-container {
    padding-bottom: calc(var(--space-2xl) + 40px);
  }
  .bottom-control-dock {
    height: 40px;
    bottom: max(var(--space-2xs), env(safe-area-inset-bottom, 4px));
    padding: 0 var(--space-sm);
  }
  .nav-bar {
    padding: var(--space-2xs) var(--space-md);
  }
  #focus-overlay,
  #pocket-overlay {
    padding: max(var(--space-2xs), env(safe-area-inset-top, 4px)) var(--space-md) max(var(--space-2xs), env(safe-area-inset-bottom, 4px)) var(--space-md);
  }
  .focus-dock {
    height: 38px;
    margin-top: var(--space-xs);
  }
  .focus-sentence-text {
    font-size: 1.12rem;
    line-height: 1.45;
  }
  .focus-sentence-zh {
    font-size: 0.92rem;
    margin-top: var(--space-2xs);
  }
}
"""
