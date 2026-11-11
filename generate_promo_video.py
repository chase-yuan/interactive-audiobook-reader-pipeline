#!/usr/bin/env python3
from __future__ import annotations

"""
generate_promo_video.py — Automated Book Promotion Video Generator.

Generates 9:16 vertical HD promotional videos from interactive audiobook readers
by recording live browser playback (smooth auto-scroll, bilingual karaoke word tracking)
and muxing high-fidelity studio audio into a production-ready MP4.
"""

import argparse
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path


class SilentHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress request spam in terminal


def start_local_server(directory: Path, port: int = 0) -> tuple[socketserver.TCPServer, int]:
    handler = lambda *args, **kwargs: SilentHTTPHandler(*args, directory=str(directory), **kwargs)
    server = socketserver.TCPServer(("127.0.0.1", port), handler)
    actual_port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, actual_port


def parse_sentence_timing(html_path: Path, sentence_id: str) -> tuple[float, float, str]:
    """Extract start time, end time and text from the reader HTML attributes."""
    content = html_path.read_text(encoding="utf-8")
    pattern = rf'id="{re.escape(sentence_id)}"\s+data-start="([\d\.]+)"\s+data-end="([\d\.]+)"'
    match = re.search(pattern, content)
    if not match:
        raise ValueError(f"Sentence {sentence_id} timing not found in {html_path.name}")
    start = float(match.group(1))
    end = float(match.group(2))
    return start, end, ""


def find_chapter_audio(book_dir: Path, chapter_num: int = 1) -> Path:
    """Find local audio file for chapter from manifest or directory."""
    manifest_path = book_dir / "audio_manifest.json"
    if manifest_path.exists():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            for entry in data.get("entries", []):
                if entry.get("chapter") == chapter_num:
                    src = Path(entry.get("source_path", ""))
                    if src.exists():
                        return src
        except Exception:
            pass

    # Fallback to direct file matching
    candidates = list(book_dir.glob("002*.mp3")) + list(book_dir.glob("*ch01*.mp3")) + list(book_dir.glob("*chapter_01*.mp3"))
    if candidates:
        return candidates[0]

    mp3s = sorted(book_dir.glob("*.mp3"))
    if len(mp3s) > 1:
        return mp3s[1]  # Often track 002 is chapter 1
    elif mp3s:
        return mp3s[0]

    raise FileNotFoundError(f"No audio file found for chapter {chapter_num} in {book_dir}")


def record_reader_video(
    html_name: str,
    server_port: int,
    start_sentence_id: str,
    duration: float,
    temp_dir: Path,
    theme: str = "sepia",
) -> tuple[Path, float]:
    from playwright.sync_api import sync_playwright

    video_dir = temp_dir / "raw_video"
    video_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--autoplay-policy=no-user-gesture-required",
                "--disable-web-security",
                "--hide-scrollbars",
            ],
        )

        # Exact 9:16 vertical full-bleed mobile viewport matching recording canvas
        context = browser.new_context(
            viewport={"width": 720, "height": 1280},
            record_video_dir=str(video_dir),
            record_video_size={"width": 720, "height": 1280},
            device_scale_factor=1.0,
        )

        page = context.new_page()

        # Pre-set theme in localStorage before loading
        page.add_init_script(f"""
            try {{
                localStorage.setItem('audible_theme', '{theme}');
                localStorage.setItem('audible_reader_theme', '{theme}');
                localStorage.setItem('reader_the-psychology-of-money_theme', '{theme}');
            }} catch(e) {{}}
        """)

        url = f"http://127.0.0.1:{server_port}/{html_name}"
        page.goto(url, wait_until="networkidle")

        # Inject realistic iOS touch cursor and ripple engine
        page.evaluate("""() => {
            const style = document.createElement('style');
            style.innerHTML = `
                #promo-cursor {
                    position: fixed;
                    width: 38px;
                    height: 38px;
                    border-radius: 50%;
                    background: rgba(255, 255, 255, 0.72);
                    border: 2.5px solid rgba(0, 0, 0, 0.35);
                    box-shadow: 0 4px 16px rgba(0,0,0,0.32);
                    pointer-events: none;
                    z-index: 2147483647;
                    transform: translate(-50%, -50%) scale(1);
                    transition: transform 0.15s ease-out, background 0.15s ease-out, opacity 0.3s ease;
                    opacity: 0;
                }
                #promo-cursor.active { opacity: 1; }
                #promo-cursor.clicking {
                    transform: translate(-50%, -50%) scale(0.72);
                    background: rgba(255, 180, 0, 0.95);
                    border-color: rgba(255, 255, 255, 0.95);
                }
                .promo-ripple {
                    position: fixed;
                    border-radius: 50%;
                    border: 3.5px solid rgba(255, 170, 0, 0.88);
                    pointer-events: none;
                    z-index: 2147483646;
                    animation: promo-ripple-anim 0.55s cubic-bezier(0.1, 0.8, 0.3, 1) forwards;
                }
                @keyframes promo-ripple-anim {
                    0% { width: 14px; height: 14px; opacity: 1; transform: translate(-50%, -50%) scale(0.8); }
                    100% { width: 90px; height: 90px; opacity: 0; transform: translate(-50%, -50%) scale(1.4); }
                }
            `;
            document.head.appendChild(style);

            const cursor = document.createElement('div');
            cursor.id = 'promo-cursor';
            document.body.appendChild(cursor);

            window.__touchTo = function(x, y, durationMs = 500) {
                return new Promise(resolve => {
                    const c = document.getElementById('promo-cursor');
                    c.classList.add('active');
                    const startX = c._curX !== undefined ? c._curX : (window.innerWidth / 2);
                    const startY = c._curY !== undefined ? c._curY : (window.innerHeight + 80);
                    const startTime = performance.now();
                    
                    function frame(now) {
                        const elapsed = now - startTime;
                        const p = Math.min(1, elapsed / durationMs);
                        const ease = p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
                        const cx = startX + (x - startX) * ease;
                        const cy = startY + (y - startY) * ease;
                        c.style.left = cx + 'px';
                        c.style.top = cy + 'px';
                        c._curX = cx;
                        c._curY = cy;
                        if (p < 1) {
                            requestAnimationFrame(frame);
                        } else {
                            resolve();
                        }
                    }
                    requestAnimationFrame(frame);
                });
            };

            window.__touchClick = function() {
                return new Promise(resolve => {
                    const c = document.getElementById('promo-cursor');
                    const x = c._curX || 0;
                    const y = c._curY || 0;
                    c.classList.add('clicking');
                    const rip = document.createElement('div');
                    rip.className = 'promo-ripple';
                    rip.style.left = x + 'px';
                    rip.style.top = y + 'px';
                    document.body.appendChild(rip);
                    setTimeout(() => rip.remove(), 600);
                    setTimeout(() => {
                        c.classList.remove('clicking');
                        resolve();
                    }, 150);
                });
            };

            window.__touchElementAndClick = async function(selector, moveMs = 600) {
                const el = document.querySelector(selector);
                if (!el) return false;
                const r = el.getBoundingClientRect();
                const cx = r.left + r.width / 2;
                const cy = r.top + r.height / 2;
                await window.__touchTo(cx, cy, moveMs);
                await window.__touchClick();
                el.click();
                return true;
            };

            window.__hideCursor = function() {
                const c = document.getElementById('promo-cursor');
                if (c) c.classList.remove('active');
            };
        }""")

        # Target sentence element
        target_selector = f"#{start_sentence_id}"
        page.wait_for_selector(target_selector, state="visible", timeout=15000)
        
        # Scroll target sentence cleanly into center view
        page.evaluate(f"""() => {{
            const el = document.getElementById('{start_sentence_id}');
            if (el) el.scrollIntoView({{ block: 'center', inline: 'nearest' }});
        }}""")
        page.wait_for_timeout(1000)

        # Choreographed Feature Demonstration Routine (~58-60s)
        # Act 1: Gliding to sentence and triggering Tap-to-Read
        page.evaluate(f"window.__touchElementAndClick('#{start_sentence_id} .sentence-text', 800)")
        start_playback_time = time.time()

        # Act 2: Pure audio-text acoustic karaoke tracking (12s)
        while time.time() - start_playback_time < 12.0:
            page.wait_for_timeout(100)

        # Act 3: Expand bottom Menu preference drawer
        page.evaluate("window.__touchElementAndClick('#drawerToggleBtn', 700)")
        page.wait_for_timeout(1500)

        # Act 4: Multi-theme demonstration (Dark, Night, Sepia)
        page.evaluate("window.__touchElementAndClick('.theme-dot-dark', 600)")
        page.wait_for_timeout(3500)

        page.evaluate("window.__touchElementAndClick('.theme-dot-night', 600)")
        page.wait_for_timeout(3000)

        page.evaluate("window.__touchElementAndClick('.theme-dot-sepia', 600)")
        page.wait_for_timeout(1500)
        page.evaluate("window.__touchElementAndClick('#drawerToggleBtn', 500)")
        page.wait_for_timeout(2000)

        # Act 5: 24 Chapters Table of Contents navigation
        page.evaluate("window.__touchElementAndClick('#chapterSelectBtn', 700)")
        page.wait_for_timeout(4000)
        page.evaluate("window.__touchElementAndClick('#chapterSelectBtn', 500)")
        page.wait_for_timeout(2000)

        # Act 6: Immersive Focus / Shadowing Mode
        page.evaluate("window.__touchElementAndClick('#drawerToggleBtn', 500)")
        page.wait_for_timeout(1000)
        page.evaluate("window.__touchElementAndClick('#focusModeBtn', 600)")
        page.wait_for_timeout(4500)
        page.evaluate("window.__touchElementAndClick('#focusExitBtn', 600)")
        page.wait_for_timeout(2000)

        # Act 7: Grand Finale flow until target duration
        page.evaluate("window.__hideCursor()")
        end_time = start_playback_time + duration
        while time.time() < end_time:
            page.wait_for_timeout(100)

        context.close()
        browser.close()

    # Find the recorded webm file
    webm_files = list(video_dir.glob("*.webm"))
    if not webm_files:
        raise RuntimeError("Playwright did not output a recorded video file.")

    raw_video = webm_files[0]
    
    # Measure total WebM duration to calculate exact video offset from click
    probe_cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(raw_video),
    ]
    probe_res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    total_dur = float(probe_res.stdout.strip())
    video_offset = max(0.0, total_dur - duration)

    return raw_video, video_offset


def mux_video_and_audio(
    raw_video: Path,
    audio_path: Path,
    audio_start: float,
    video_offset: float,
    duration: float,
    output_path: Path,
) -> Path:
    """Use ffmpeg to accurately slice audio, trim video, and mux into production-ready MP4."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Production Apple QuickTime / Mobile HD compatibility flags
    cmd = [
        "ffmpeg",
        "-y",
        "-ss", f"{video_offset:.3f}",
        "-i", str(raw_video),
        "-ss", f"{audio_start:.3f}",
        "-i", str(audio_path),
        "-t", f"{duration:.3f}",
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-profile:v", "high",
        "-level", "4.1",
        "-movflags", "+faststart",
        "-colorspace", "bt709",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_path),
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg muxing failed: {res.stderr}")

    return output_path


def generate_promo_video(
    book_dir: Path,
    html_path: Path | None = None,
    output_path: Path | None = None,
    start_sentence_id: str = "c1-s-0",
    duration: float = 58.0,
    theme: str = "sepia",
) -> Path:
    book_dir = book_dir.resolve()
    if not html_path:
        readers = list(book_dir.glob("*Interactive_Reader.html")) + list(book_dir.glob("*reader.html"))
        if not readers:
            raise FileNotFoundError(f"No interactive reader HTML found in {book_dir}")
        html_path = readers[0]

    if not output_path:
        output_path = book_dir / f"{book_dir.name}_promo.mp4"

    print(f"📖 [PROMO] Target Reader: {html_path.name}")
    print(f"🎯 [PROMO] Start Sentence: #{start_sentence_id}")

    # 1. Parse audio start time from sentence
    audio_start, _, _ = parse_sentence_timing(html_path, start_sentence_id)
    print(f"⏱️ [PROMO] Audio timestamp offset: {audio_start:.2f}s | Duration: {duration:.1f}s")

    # 2. Locate local master audio file
    audio_path = find_chapter_audio(book_dir, chapter_num=1)
    print(f"🎵 [PROMO] Master Audio Source: {audio_path.name}")

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)
        
        # 3. Spin up local static server
        server, port = start_local_server(book_dir)
        try:
            print(f"🌐 [PROMO] Temporary web server running on port {port}")
            
            # 4. Record high-res browser reading interaction
            print(f"🎥 [PROMO] Recording mobile 9:16 browser interaction ({theme} theme)...")
            raw_video, video_offset = record_reader_video(
                html_name=html_path.name,
                server_port=port,
                start_sentence_id=start_sentence_id,
                duration=duration,
                temp_dir=tmp_dir,
                theme=theme,
            )

            # 5. Mux with studio audio via ffmpeg
            print(f"🎛️ [PROMO] Muxing HD video and lossless audio via FFmpeg...")
            mux_video_and_audio(
                raw_video=raw_video,
                audio_path=audio_path,
                audio_start=audio_start,
                video_offset=video_offset,
                duration=duration,
                output_path=output_path,
            )
        finally:
            server.shutdown()

    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✅ [PROMO] Promo video successfully generated -> {output_path} ({file_size_mb:.2f} MB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate vertical 9:16 promotional video from interactive reader HTML.")
    parser.add_argument("--book-dir", type=Path, required=True, help="Path to audiobook directory containing reader HTML")
    parser.add_argument("--html", type=Path, default=None, help="Explicit reader HTML file path")
    parser.add_argument("--output", type=Path, default=None, help="Output MP4 file path")
    parser.add_argument("--start", type=str, default="c1-s-0", help="Sentence ID to start playback from (default: c1-s-0)")
    parser.add_argument("--duration", type=float, default=58.0, help="Video duration in seconds (default: 58.0)")
    parser.add_argument("--theme", type=str, default="sepia", choices=["sepia", "light", "dark", "night"], help="Reader theme")
    parser.add_argument("--open", action="store_true", help="Automatically pop open video in player after generation")

    args = parser.parse_args()
    out = generate_promo_video(
        book_dir=args.book_dir,
        html_path=args.html,
        output_path=args.output,
        start_sentence_id=args.start,
        duration=args.duration,
        theme=args.theme,
    )
    if args.open:
        subprocess.run(["open", "-a", "QuickTime Player", str(out)])
        time.sleep(0.5)
        subprocess.run(["osascript", "-e", 'tell application "QuickTime Player" to play front document'])


if __name__ == "__main__":
    main()
