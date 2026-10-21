# 0002. Reader Engine Deep Power-Saving & Off-Screen Containment

Date: 2026-10-21  
Status: Accepted & Merged to main (`40792c2`)  
Decider: CTO Architecture Council  

## Context
Generated HTML readers were causing excessive battery drain and thermal rise on Safari (iOS/macOS) during long reading and listening sessions (> 1 hour).
The compilation engine in `html_builder.py` and styling in `reader_theme.py` produced readers that:
- Triggered 24/7 background `setInterval(..., 250)` timers regardless of playback or shadowing state.
- Executed redundant binary searches and DOM traversals on every animation frame.
- Fully rendered thousands of sentence nodes off-screen on the GPU compositor.
- Eagerly buffered multi-megabyte audio tracks via `preload="auto"`.

## Decision
1. **Engine-Level Template Optimizations (`html_builder.py`)**:
   - Replaced `setInterval(250)` with on-demand `armShadowPauseWatchdog()`, ensuring zero timer wakeups when idle.
   - Introduced `currentActiveWordStart` and `currentActiveWordEnd` time-window caching in `syncPlayback()` to bypass 95% of word lookups.
   - Cached `currentActiveSection` to eliminate per-frame `document.querySelector` root traversals.
   - Updated `getNextShadowSentence` to navigate the in-memory `sentenceTimeIndex` instead of performing full DOM `querySelectorAll`.
   - Guaranteed `preload="metadata"` default across all compiled `<audio>` elements.
2. **Style-Level Off-Screen Containment (`reader_theme.py`)**:
   - Injected `content-visibility: auto; contain-intrinsic-size: 0 72px;` on `.sentence-unit`, skipping layout computation and paint trees for off-screen sentences.
   - Added `content-visibility: visible;` override for `.sentence-unit.active`.

## Verification
- Unit test suite: `python -m unittest test_html_builder.py test_release_gate.py` (37/37 passed in 0.285s).
- Validated output reader generation passes algorithmic alignment and release gates.
