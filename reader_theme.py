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

  /* --- OLED Pocket Mode Tokens --- */
  --pocket-bg: #000000;
  --pocket-title: #334155;
  --pocket-status: #64748b;
  --pocket-hint: #1e293b;
  --pocket-btn-bg: #0f172a;
  --pocket-btn-border: #1e293b;
  --pocket-btn-text: #94a3b8;
  --pocket-btn-active-bg: #1e293b;
  --pocket-btn-active-text: #f1f5f9;
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
  padding: var(--space-md) var(--space-2xl);
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-lg);
}

.chapter-nav-wrapper {
  position: relative;
  flex: 1;
  min-width: 0;
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

/* Collapsible Control Drawer */
.control-drawer {
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
}

.control-drawer.open {
  display: block;
  animation: drawerSlideDown var(--transition-drawer);
}

@keyframes drawerSlideDown {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.drawer-inner {
  max-width: var(--max-content-width);
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-lg);
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
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-base);
}

.drawer-group {
  display: flex;
  align-items: center;
  gap: var(--space-md);
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
}

.pill-btn:hover {
  background: var(--bg-hover);
  border-color: var(--accent-light);
}

.pill-btn:active {
  opacity: 0.85;
}

.pill-btn.active {
  background: var(--accent);
  color: var(--btn-primary-text);
  border-color: var(--accent);
}

.toggle-pill {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  user-select: none;
}

.toggle-pill input[type="checkbox"] {
  display: none;
}

.toggle-badge {
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
  .control-drawer {
    padding: var(--space-base) var(--space-xl);
    max-height: calc(100vh - 54px);
    max-height: calc(100dvh - 54px);
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }
  .drawer-inner {
    gap: var(--space-base);
  }
  .drawer-row {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: var(--space-md);
  }
  .drawer-group {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--space-sm);
    width: 100%;
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

/* Sentence Units & Tap Inspection */
.sentence-unit {
  margin-bottom: var(--space-lg);
  border-radius: var(--radius-base);
  transition: background var(--transition-fast);
}

.sentence-text {
  cursor: pointer;
  padding: var(--space-xs) var(--space-sm);
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}

.sentence-text:hover {
  background: var(--bg-hover);
}

.sentence-unit.active .sentence-text {
  background: var(--bg-panel);
}

.sentence-unit[data-matched="0"] .sentence-text {
  opacity: 0.88;
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
}

#reader-toast.show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

/* OLED Pocket Mode Overlay (Zero-Power Pitch Black + Touch Shield) */
#pocket-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  width: 100dvw;
  height: 100dvh;
  background-color: var(--pocket-bg);
  z-index: 2147483647;
  display: none;
  flex-direction: column;
  justify-content: space-between;
  align-items: center;
  padding: env(safe-area-inset-top, 40px) 24px env(safe-area-inset-bottom, 40px) 24px;
  box-sizing: border-box;
  user-select: none;
  -webkit-user-select: none;
  touch-action: manipulation;
}

.pocket-header {
  margin-top: 36px;
  text-align: center;
}

.pocket-title {
  color: var(--pocket-title);
  font-size: 0.85rem;
  letter-spacing: 0.05em;
  font-family: var(--font-sans);
  text-transform: uppercase;
  margin-bottom: 8px;
}

.pocket-status {
  color: var(--pocket-status);
  font-size: 1.15rem;
  font-weight: 600;
  font-family: var(--font-sans);
}

.pocket-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
}

.pocket-hint {
  color: var(--pocket-hint);
  font-size: 0.82rem;
  font-family: var(--font-sans);
  letter-spacing: 0.02em;
}

.pocket-exit-btn {
  background: var(--pocket-btn-bg);
  color: var(--pocket-btn-text);
  border: 1px solid var(--pocket-btn-border);
  border-radius: var(--radius-full);
  padding: 12px 28px;
  font-size: 0.92rem;
  font-weight: 500;
  font-family: var(--font-sans);
  cursor: pointer;
  min-height: 44px;
  min-width: 140px;
  touch-action: manipulation;
  transition: all var(--transition-base);
}

.pocket-exit-btn:active {
  background: var(--pocket-btn-active-bg);
  color: var(--pocket-btn-active-text);
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
  font-size: var(--font-size-h2);
  font-weight: 700;
  margin-top: var(--space-6xl);
  margin-bottom: var(--space-lg);
  color: var(--accent);
  border-bottom: var(--space-3xs) solid var(--border);
  padding-bottom: var(--space-sm);
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
"""
