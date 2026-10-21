# 0003. Focus Immersion Mode Architecture & Aesthetic Zero-Jitter Protocol

Date: 2026-10-21  
Status: Accepted  
Decider: Lead Product Manager & Principal Design Architect  

## Context
1. The reader's experimental overlay was previously designated as "Pocket Mode" (放入口袋), reflecting an obsolete design metaphor that attempted to emulate native lock-screen behaviors inside a web container.
2. The user experience suffered from critical ergonomic and aesthetic flaws:
   - **Severe Layout Jitter (Font expansion/shrinkage)**: Active-word highlighting inside the immersion sentence container dynamically introduced `padding: 1px 3px` while inactive words had zero padding. This caused an instant 6px horizontal width reflow per active word, causing the entire sentence to shudder and jitter during playback.
   - **AP0 / AP3 Violations**: The UI was polluted with decorative emojis (`👁 盲听模式`, `🙈 盲听中`) and patronizing parenthetical annotations (`(点此显字)`), degrading Apple Books-grade typography into amateur aesthetics.
   - **High-Friction Exit Barrier**: A 1.5-second hold-to-exit requirement generated severe usability friction during active cognitive training.
   - **Missing User Controls**: Repetition loops were hardcoded in the engine (default 3x) with zero user agency, and bilingual translation visibility could not be toggled independently.
   - **Broken Design Token Invariant**: Hardcoded hex color literals and raw `rgba(...)` in component rules broke `test_design_tokens.py`.

## Decision
1. **Conceptual & Naming Elevation**:
   - Redesignate "Pocket Mode" to **Focus Immersion Mode** (`Focus 专注精听舱`).
2. **Elimination of Word Layout Shift (Zero-Jitter AP4)**:
   - Enforce strictly zero padding (`padding: 0 !important`) on `.focus-sentence-text .active-word` matching standard word layout. Word highlights modify only color and background tokens, preserving identical text metrics with zero cumulative layout shift (CLS = 0).
3. **Ergonomic Controls (Instant Flow AP5)**:
   - **Single-Tap Instant Exit**: Eliminate the 1.5s hold timer. Clicking the exit button, the close icon, pressing `Esc`, or double-tapping background exits instantly.
   - **Cyclic Repetition Control**: Introduce a cyclic repetition pill button toggling through `1×` $\rightarrow$ `3×` $\rightarrow$ `5×` $\rightarrow$ `1×` on single clicks (keyboard shortcut `R`).
   - **Independent Translation Control**: Add a dedicated `译文` toggle (keyboard shortcut `T`), with user preference state persisted across sessions via `localStorage.getItem('reader_focus_show_trans')`.
4. **Strict Aesthetic Principle Zero (AP0 / AP2 / AP3)**:
   - Strip all emojis (`👁`, `🙈`, `ℹ️`, `✕` as decorative art) and bureaucratic parentheses (`(点此显字)`).
   - 100% tokenized CSS: Define all Focus mode tokens (`--focus-bg`, `--focus-status`, `--focus-btn-*`, etc.) in `:root` and bind them via `var(--...)`.

## Verification & Acceptance
- `test_design_tokens.py`: 100% PASS with 0 raw hex/rgba literals in component rules.
- `test_html_builder.py`: 100% PASS across reader generation suite.
- Zero-Jitter test assertion: `.focus-sentence-text .active-word` has zero padding/margin changes.
