#!/usr/bin/env python3
"""
test_library_acoustic_continuity.py
Universal Red-Team Automated Test Suite for Library-Wide Acoustic Continuity.

Audits books and chapters across any generated interactive reader or library.
Guarantees users never act as 'human testers' by programmatically catching:
  1. Leading Speech Voids (unhandled delay before chapter narration starts).
  2. Excessive Inter-Sentence Gaps (missing tables, sidebars, summaries, or dropped paragraphs).
  3. Text-only books (gracefully classified and exempted from acoustic checks).
"""

import os
import sys
import re
import json
import unittest
import argparse
from pathlib import Path

DEFAULT_AUDIBLE_DIR = Path("/Users/lindy/Vault/Audible")

LEADING_THRESHOLD_NORMAL = 4.5  # Seconds allowed before chapter narration starts
LEADING_THRESHOLD_CH1 = 30.0    # Seconds allowed for ch1 publisher intro
GAP_THRESHOLD_WARNING = 8.0     # Gap between sentences to emit a warning
GAP_THRESHOLD_CRITICAL = 15.0   # Gap between sentences to classify as critical missing text


def parse_chapter_html(html_path: Path):
    """Extract chapter metadata, audio status, skip ranges, and sentence unit timestamps."""
    html = Path(html_path).read_text(encoding="utf-8")
    
    m_ch = re.search(r'data-ch=[\x22\x27](\d+)[\x22\x27]', html)
    ch_num = int(m_ch.group(1)) if m_ch else 0

    m_audio = re.search(r'data-audio=[\x22\x27]([^\x22\x27]*)[\x22\x27]', html)
    audio_src = m_audio.group(1).strip() if m_audio else ""
    is_text_only = (not audio_src)

    m_skips = re.search(r'data-skip-ranges="([^"]+)"', html) or re.search(r"data-skip-ranges='([^']+)'", html)
    ch_skips = []
    if m_skips:
        try:
            import html as html_lib
            ch_skips = json.loads(html_lib.unescape(m_skips.group(1)))
        except Exception:
            pass

    # Extract sentence units
    unit_matches = re.findall(
        r'<span class=[\x22\x27]sentence-unit[^>]+id=[\x22\x27]([^\x22\x27]+)[\x22\x27][^>]+'
        r'data-start=[\x22\x27]([^\x22\x27]+)[\x22\x27][^>]+data-end=[\x22\x27]([^\x22\x27]+)[\x22\x27]',
        html
    )

    matched_units = []
    for uid, s_str, e_str in unit_matches:
        if s_str in ("null", "", "None") or e_str in ("null", "", "None"):
            continue
        try:
            st = float(s_str)
            en = float(e_str)
            matched_units.append({"id": uid, "start": st, "end": en})
        except ValueError:
            pass

    # If no units have valid timestamps, treat as text-only
    if not matched_units and len(unit_matches) > 0:
        is_text_only = True

    return {
        "chapter_num": ch_num,
        "audio_src": audio_src,
        "is_text_only": is_text_only,
        "skips": ch_skips,
        "units": matched_units,
        "total_units": len(unit_matches),
        "matched_count": len(matched_units)
    }


def is_range_covered(start: float, end: float, skip_ranges: list, tolerance: float = 2.0) -> bool:
    """Check if a time range is reconciled by declared skip ranges."""
    for r in skip_ranges:
        r_st = float(r.get("start", 0))
        r_en = float(r.get("end", 0))
        if r_st <= (start + tolerance) and r_en >= (end - tolerance):
            return True
    return False


def audit_chapter_html(html_path: Path):
    """Audit single chapter for temporal and acoustic continuity defects."""
    data = parse_chapter_html(html_path)
    if data["is_text_only"]:
        return []

    ch_num = data["chapter_num"]
    skips = data["skips"]
    units = data["units"]

    defects = []
    if not units:
        defects.append({
            "type": "EMPTY_CHAPTER",
            "severity": "CRITICAL",
            "duration": 0.0,
            "message": f"Zero aligned sentence units found in audio chapter {Path(html_path).name}"
        })
        return defects

    # 1. Leading void check
    first = units[0]
    lead_thresh = LEADING_THRESHOLD_CH1 if ch_num == 1 else LEADING_THRESHOLD_NORMAL
    if first["start"] > lead_thresh:
        if not is_range_covered(0.0, first["start"], skips, tolerance=1.5):
            defects.append({
                "type": "LEADING_VOID",
                "severity": "CRITICAL" if first["start"] > 10.0 else "WARNING",
                "unit": first["id"],
                "start": 0.0,
                "end": first["start"],
                "duration": round(first["start"], 2),
                "message": f"Leading unhandled void of {first['start']:.2f}s before unit {first['id']}"
            })

    # 2. Inter-sentence gap check
    prev_end = first["end"]
    for u in units[1:]:
        gap = u["start"] - prev_end
        if gap > GAP_THRESHOLD_WARNING:
            if not is_range_covered(prev_end, u["start"], skips, tolerance=2.0):
                severity = "CRITICAL" if gap >= GAP_THRESHOLD_CRITICAL else "WARNING"
                defects.append({
                    "type": "INTER_SENTENCE_VOID",
                    "severity": severity,
                    "unit": u["id"],
                    "prev_end": round(prev_end, 2),
                    "start": round(u["start"], 2),
                    "duration": round(gap, 2),
                    "message": f"Unhandled void of {gap:.2f}s between {prev_end:.2f}s and {u['start']:.2f}s before unit {u['id']}"
                })
        prev_end = max(prev_end, u["end"])

    return defects


def audit_book_dir(book_dir: Path):
    """Audit all chapters of a book directory."""
    book_dir = Path(book_dir)
    chapters_dir = book_dir / "chapters"
    if not chapters_dir.exists():
        # Check if single html exists
        html_files = list(book_dir.glob("*.html"))
        if not html_files:
            return {
                "book": book_dir.name,
                "status": "NO_CHAPTERS",
                "chapter_count": 0,
                "critical_count": 0,
                "warning_count": 0,
                "defects": []
            }
        chapters_dir = book_dir

    chapter_files = sorted(
        chapters_dir.glob("*.html"),
        key=lambda p: int(re.search(r"\d+", p.name).group(0)) if re.search(r"\d+", p.name) else 0
    )

    book_defects = []
    critical_count = 0
    warning_count = 0
    is_text_only = False

    if chapter_files:
        sample_data = parse_chapter_html(chapter_files[0])
        is_text_only = sample_data["is_text_only"]

    if is_text_only:
        return {
            "book": book_dir.name,
            "status": "TEXT_ONLY",
            "chapter_count": len(chapter_files),
            "critical_count": 0,
            "warning_count": 0,
            "defects": []
        }

    for cf in chapter_files:
        c_defects = audit_chapter_html(cf)
        for d in c_defects:
            d["file"] = cf.name
            book_defects.append(d)
            if d.get("severity") == "CRITICAL":
                critical_count += 1
            else:
                warning_count += 1

    return {
        "book": book_dir.name,
        "status": "CLEAN" if critical_count == 0 and warning_count == 0 else "DEFECTIVE",
        "chapter_count": len(chapter_files),
        "total_defects": len(book_defects),
        "critical_count": critical_count,
        "warning_count": warning_count,
        "defects": book_defects
    }


class TestAcousticContinuityGate(unittest.TestCase):
    """Unit tests for the acoustic continuity checker itself."""

    def test_clean_audio_chapter_passes(self):
        html = """
        <section class="chapter-section" data-ch="2" data-audio="audio.mp3">
            <span class="sentence-unit" id="c2-s-1" data-start="1.20" data-end="4.50"></span>
            <span class="sentence-unit" id="c2-s-2" data-start="5.00" data-end="9.10"></span>
        </section>
        """
        tmp_file = Path("/tmp/test_clean.html")
        tmp_file.write_text(html, encoding="utf-8")
        try:
            defects = audit_chapter_html(tmp_file)
            self.assertEqual(len(defects), 0)
        finally:
            if tmp_file.exists():
                tmp_file.unlink()

    def test_leading_void_detected_in_non_ch1(self):
        html = """
        <section class="chapter-section" data-ch="2" data-audio="audio.mp3">
            <span class="sentence-unit" id="c2-s-1" data-start="12.50" data-end="16.00"></span>
        </section>
        """
        tmp_file = Path("/tmp/test_leading.html")
        tmp_file.write_text(html, encoding="utf-8")
        try:
            defects = audit_chapter_html(tmp_file)
            self.assertEqual(len(defects), 1)
            self.assertEqual(defects[0]["type"], "LEADING_VOID")
            self.assertEqual(defects[0]["severity"], "CRITICAL")
        finally:
            if tmp_file.exists():
                tmp_file.unlink()

    def test_inter_sentence_excessive_gap_detected(self):
        html = """
        <section class="chapter-section" data-ch="2" data-audio="audio.mp3">
            <span class="sentence-unit" id="c2-s-1" data-start="1.00" data-end="5.00"></span>
            <span class="sentence-unit" id="c2-s-2" data-start="25.00" data-end="30.00"></span>
        </section>
        """
        tmp_file = Path("/tmp/test_gap.html")
        tmp_file.write_text(html, encoding="utf-8")
        try:
            defects = audit_chapter_html(tmp_file)
            self.assertEqual(len(defects), 1)
            self.assertEqual(defects[0]["type"], "INTER_SENTENCE_VOID")
            self.assertEqual(defects[0]["duration"], 20.0)
        finally:
            if tmp_file.exists():
                tmp_file.unlink()

    def test_skip_ranges_reconcile_voids(self):
        html = """
        <section class="chapter-section" data-ch="2" data-audio="audio.mp3" data-skip-ranges='[{"start":0.0,"end":15.0},{"start":20.0,"end":40.0}]'>
            <span class="sentence-unit" id="c2-s-1" data-start="14.00" data-end="19.00"></span>
            <span class="sentence-unit" id="c2-s-2" data-start="39.00" data-end="45.00"></span>
        </section>
        """
        tmp_file = Path("/tmp/test_reconciled.html")
        tmp_file.write_text(html, encoding="utf-8")
        try:
            defects = audit_chapter_html(tmp_file)
            self.assertEqual(len(defects), 0)
        finally:
            if tmp_file.exists():
                tmp_file.unlink()

    def test_text_only_chapter_exempted(self):
        html = """
        <section class="chapter-section" data-ch="1" data-audio="">
            <span class="sentence-unit" id="c1-s-1" data-start="null" data-end="null"></span>
            <span class="sentence-unit" id="c1-s-2" data-start="null" data-end="null"></span>
        </section>
        """
        tmp_file = Path("/tmp/test_text_only.html")
        tmp_file.write_text(html, encoding="utf-8")
        try:
            defects = audit_chapter_html(tmp_file)
            self.assertEqual(len(defects), 0)
        finally:
            if tmp_file.exists():
                tmp_file.unlink()


def main():
    parser = argparse.ArgumentParser(description="Audit library-wide acoustic continuity")
    parser.add_argument("--audible-dir", type=str, default=str(DEFAULT_AUDIBLE_DIR), help="Path to Audible library root")
    parser.add_argument("--book", type=str, help="Audit a single book ID")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--markdown", type=str, help="Export markdown audit report to file")
    parser.add_argument("--fail-on-critical", action="store_true", help="Exit with code 1 if critical defects exist")
    args = parser.parse_args()

    audible_path = Path(args.audible_dir)
    manifest_path = audible_path / "manifest.json"
    books_dir = audible_path / "books"

    if not manifest_path.exists():
        print(f"Error: manifest.json not found at {manifest_path}")
        sys.exit(1)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    all_books = [b["id"] for b in manifest.get("books", [])]
    if args.book:
        if args.book not in all_books:
            print(f"Error: book '{args.book}' not found in manifest.")
            sys.exit(1)
        target_books = [args.book]
    else:
        target_books = all_books

    if not args.json:
        print("\n" + "=" * 80)
        print("      AUDIBLE LIBRARY · RED-TEAM ACOUSTIC CONTINUITY AUDITOR")
        print("=" * 80)
        print(f"Scanning {len(target_books)} books across {books_dir}...")

    results = []
    total_critical = 0
    total_warnings = 0

    clean_books = []
    text_only_books = []
    impaired_books = []

    for b_id in target_books:
        b_dir = books_dir / b_id
        res = audit_book_dir(b_dir)
        results.append(res)
        total_critical += res["critical_count"]
        total_warnings += res["warning_count"]
        
        if res.get("status") == "TEXT_ONLY":
            text_only_books.append(b_id)
        elif res["critical_count"] == 0 and res["warning_count"] == 0:
            clean_books.append(b_id)
        else:
            impaired_books.append(res)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    # Print summary leaderboard
    print(f"\n📊 AUDIT SUMMARY:")
    print(f"  • Total Books Audited:    {len(target_books)}")
    print(f"  • 🟢 Perfect / Gap-Free:  {len(clean_books)} audiobooks")
    print(f"  • 📖 Text-Only Readers:   {len(text_only_books)} books")
    print(f"  • 🔴 Defective Audiobooks:{len(impaired_books)} audiobooks")
    print(f"  • Critical Voids (>15s):  {total_critical}")
    print(f"  • Minor Voids (8-15s):    {total_warnings}")

    if clean_books:
        print(f"\n🟢 FULLY VERIFIED CONTINUOUS BOOKS ({len(clean_books)}):")
        for b in clean_books:
            print(f"   ✓ {b}")

    if text_only_books:
        print(f"\n📖 TEXT-ONLY INTERACTIVE READERS ({len(text_only_books)}):")
        for b in text_only_books:
            print(f"   ℹ️ {b} (Text-only edition, no audio alignment required)")

    if impaired_books:
        print(f"\n🔴 AUDIOBOOKS WITH DEFECTS ({len(impaired_books)}):")
        impaired_books.sort(key=lambda x: x["critical_count"], reverse=True)
        for b_res in impaired_books:
            crit = b_res["critical_count"]
            warn = b_res["warning_count"]
            print(f"\n  📖 {b_res['book']} ({b_res['chapter_count']} chs): {crit} CRITICAL, {warn} WARNINGS")
            
            crit_defects = [d for d in b_res["defects"] if d.get("severity") == "CRITICAL"]
            crit_defects.sort(key=lambda x: x.get("duration", 0), reverse=True)
            for d in crit_defects[:5]:
                dur = d.get('duration', 0.0)
                unit_str = f" ({d['unit']})" if 'unit' in d else ""
                print(f"     ❌ [{d['type']}] {d['file']}{unit_str}: {dur:.2f}s void ({d['message']})")
            if len(crit_defects) > 5:
                print(f"     ... and {len(crit_defects) - 5} more critical voids")

    if args.markdown:
        md_path = Path(args.markdown)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# Audible Library Acoustic Continuity Audit Report\n\n")
            f.write(f"- **Total Books Audited**: {len(target_books)}\n")
            f.write(f"- **Clean Audiobooks**: {len(clean_books)}\n")
            f.write(f"- **Text-Only Books**: {len(text_only_books)}\n")
            f.write(f"- **Defective Audiobooks**: {len(impaired_books)}\n")
            f.write(f"- **Critical Voids (>15s)**: {total_critical}\n")
            f.write(f"- **Minor Voids (8-15s)**: {total_warnings}\n\n")
            
            f.write("## Defect Leaderboard\n\n")
            f.write("| Book | Chapters | Critical Voids | Warnings | Status |\n")
            f.write("| :--- | :--- | :--- | :--- | :--- |\n")
            for b in clean_books:
                f.write(f"| `{b}` | - | 0 | 0 | 🟢 CLEAN |\n")
            for b in text_only_books:
                f.write(f"| `{b}` | - | 0 | 0 | 📖 TEXT-ONLY |\n")
            for b_res in impaired_books:
                f.write(f"| `{b_res['book']}` | {b_res['chapter_count']} | {b_res['critical_count']} | {b_res['warning_count']} | 🔴 IMPAIRED |\n")

        print(f"\nSaved Markdown report to: {md_path}")

    print("\n" + "=" * 80)
    if args.fail_on_critical and total_critical > 0:
        print(f"FAILED: {total_critical} critical acoustic voids detected.")
        sys.exit(1)
    else:
        print(f"Audit completed successfully.")
        sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] not in ("-h", "--help", "--audible-dir", "--book", "--json", "--markdown", "--fail-on-critical"):
        unittest.main()
    else:
        main()
