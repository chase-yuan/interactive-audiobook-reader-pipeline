import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from artifact_io import atomic_write_json
from intake_reconciler import approve_plan, build_plan, parse_epub, verify_gate


def _make_epub(path: Path) -> None:
    container = """<?xml version='1.0'?>
    <container xmlns='urn:oasis:names:tc:opendocument:xmlns:container'>
      <rootfiles><rootfile full-path='EPUB/content.opf'/></rootfiles>
    </container>"""
    opf = """<package xmlns='http://www.idpf.org/2007/opf' version='3.0'>
      <metadata xmlns:dc='http://purl.org/dc/elements/1.1/'><dc:title>Fixture</dc:title></metadata>
      <manifest>
        <item id='nav' href='nav.xhtml' media-type='application/xhtml+xml' properties='nav'/>
        <item id='empty' href='empty.xhtml' media-type='application/xhtml+xml'/>
        <item id='c1' href='c1.xhtml' media-type='application/xhtml+xml'/>
        <item id='c2' href='c2.xhtml' media-type='application/xhtml+xml'/>
        <item id='cover' href='cover.jpg' media-type='image/jpeg' properties='cover-image'/>
      </manifest>
      <spine><itemref idref='empty'/><itemref idref='c1'/><itemref idref='c2'/></spine>
    </package>"""
    nav = """<html xmlns='http://www.w3.org/1999/xhtml'><body><nav><ol>
      <li><a href='c1.xhtml'>The Beginning</a></li><li><a href='c2.xhtml'>The Ending</a></li>
    </ol></nav></body></html>"""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("META-INF/container.xml", container)
        zf.writestr("EPUB/content.opf", opf)
        zf.writestr("EPUB/nav.xhtml", nav)
        zf.writestr("EPUB/empty.xhtml", "<html><body><img src='x.jpg'/></body></html>")
        zf.writestr("EPUB/c1.xhtml", "<html><body>The beginning opens with a red door and a quiet street.</body></html>")
        zf.writestr("EPUB/c2.xhtml", "<html><body>The ending closes beside the blue sea under a silent moon.</body></html>")
        zf.writestr("EPUB/cover.jpg", b"jpeg fixture")


class IntakeReconcilerTests(unittest.TestCase):
    def test_epub_spine_titles_empty_filter_and_cover(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            epub = root / "book.epub"
            cover = root / "cover.jpg"
            _make_epub(epub)
            parsed = parse_epub(epub, cover)
            self.assertEqual([ch["title"] for ch in parsed["chapters"]], ["The Beginning", "The Ending"])
            self.assertEqual(cover.read_bytes(), b"jpeg fixture")

    def test_hash_bound_approval_blocks_changed_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            epub = root / "book.epub"
            audio = root / "audio"
            audio.mkdir()
            _make_epub(epub)
            intro = audio / "001 intro.mp3"
            chapter1 = audio / "002 chapter.mp3"
            chapter2 = audio / "003 chapter.mp3"
            for path in (intro, chapter1, chapter2):
                path.write_bytes(path.name.encode())
            probes = {
                intro.name: {"head": "audible hopes you enjoy this program", "tail": ""},
                chapter1.name: {"head": "the beginning opens with a red door and a quiet street", "tail": "the beginning opens with a red door and a quiet street"},
                chapter2.name: {"head": "the ending closes beside the blue sea under a silent moon", "tail": "the ending closes beside the blue sea under a silent moon"},
            }
            plan = build_plan(epub, audio, probes, duration_probe=lambda _: 60.0, threshold=0.80)
            self.assertEqual(plan["mappings"][0]["kind"], "skip_audio")
            plan_path = root / "intake_plan.json"
            atomic_write_json(plan_path, plan)
            approve_plan(plan_path)
            self.assertEqual(verify_gate(plan_path)["gate_status"], "approved")
            chapter1.write_bytes(b"changed")
            with self.assertRaisesRegex(RuntimeError, "missing or changed"):
                verify_gate(plan_path)

    def test_low_confidence_plan_cannot_be_approved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            epub = root / "book.epub"
            audio = root / "audio"
            audio.mkdir()
            _make_epub(epub)
            for number in (1, 2):
                (audio / f"{number}.mp3").write_bytes(b"audio")
            plan = build_plan(epub, audio, {"1.mp3": {"head": "unrelated"}, "2.mp3": {"head": "noise"}}, duration_probe=lambda _: 1.0)
            path = root / "plan.json"
            atomic_write_json(path, plan)
            with self.assertRaisesRegex(RuntimeError, "confidence threshold"):
                approve_plan(path)

    def test_reconciler_supports_two_epub_chapters_in_one_audio_track(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            epub = root / "book.epub"
            audio = root / "audio"
            audio.mkdir()
            _make_epub(epub)
            combined = audio / "combined.mp3"
            combined.write_bytes(b"combined")
            probes = {combined.name: {
                "head": "the beginning opens with a red door and a quiet street",
                "tail": "the ending closes beside the blue sea under a silent moon",
            }}
            plan = build_plan(epub, audio, probes, duration_probe=lambda _: 120.0, threshold=0.90)
            matches = [row for row in plan["mappings"] if row["kind"] == "match"]
            self.assertEqual(matches[0]["chapter_indices"], [0, 1])
            self.assertEqual(matches[0]["audio_indices"], [0])
            self.assertGreaterEqual(matches[0]["confidence"], 0.90)

    def test_reconciler_records_print_only_epub_spine_documents(self):
        chapters = [
            {"title": "Cover", "head_anchor": "cover", "tail_anchor": "cover", "text_chars": 5},
            {"title": "Chapter One", "head_anchor": "chapter begins", "tail_anchor": "chapter ends", "text_chars": 100},
            {"title": "Index", "head_anchor": "index entries", "tail_anchor": "index entries", "text_chars": 50},
        ]
        audios = [{"name": "chapter.mp3", "duration": 60.0}]
        probes = {"chapter.mp3": {"head": "chapter begins", "tail": "chapter ends"}}
        from intake_reconciler import reconcile
        rows = reconcile(chapters, audios, probes)
        self.assertEqual([row["kind"] for row in rows], ["skip_chapter", "match", "skip_chapter"])
        self.assertEqual(rows[1]["chapter_indices"], [1])
        self.assertEqual(rows[1]["audio_indices"], [0])

    def test_ffprobe_duration_specifies_explicit_timeout(self):
        from unittest.mock import patch, MagicMock
        from intake_reconciler import ffprobe_duration
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout="123.45\n")
            dur = ffprobe_duration(Path("/fake/audio.mp3"))
            self.assertEqual(dur, 123.45)
            self.assertEqual(mock_run.call_args[1].get("timeout"), 60)


    def test_reconstruct_legacy_paragraphs_shredded(self):
        from intake_reconciler import reconstruct_legacy_paragraphs
        # 20 legacy sentences where elem_idx = 0..19 (100% shredded)
        shredded = [
            {"id": f"s-{i}", "text": f"This is sentence {i} in an old OCR book.", "elem_idx": i, "is_heading": False}
            for i in range(20)
        ]
        reconstructed = reconstruct_legacy_paragraphs(shredded, target_sentences=4)
        unique_new_elems = set(it["elem_idx"] for it in reconstructed)
        # Should be grouped into ~5 paragraphs (4 sentences each), not 20!
        self.assertLessEqual(len(unique_new_elems), 6)
        self.assertGreaterEqual(len(unique_new_elems), 4)
        # Check first paragraph has multiple sentences
        p0_sents = [it["id"] for it in reconstructed if it["elem_idx"] == 0]
        self.assertGreaterEqual(len(p0_sents), 3)

    def test_reconstruct_legacy_paragraphs_intact_preserved(self):
        from intake_reconciler import reconstruct_legacy_paragraphs
        # Intact book where elem_idx is already grouped (e.g. 20 sentences in 4 paragraphs)
        intact = [
            {"id": f"s-{i}", "text": f"This is sentence {i}.", "elem_idx": i // 5, "is_heading": False}
            for i in range(20)
        ]
        res = reconstruct_legacy_paragraphs(intact)
        # Must not mutate already-grouped books
        self.assertEqual([it["elem_idx"] for it in res], [it["elem_idx"] for it in intact])


if __name__ == "__main__":
    unittest.main()
