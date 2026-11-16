"""
Test suite for Shift-Left Leading Acoustic Gap Gate and EPUB Summary Extractor.
Guarantees regression protection against missing audiobook chapter summaries,
unhandled leading voice gaps, and unanchored audio skips.
"""

import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from quality_gate import _check_temporal_integrity
from intake_reconciler import extract_chapter_summaries_from_epub


class LeadingAcousticGapGateTests(unittest.TestCase):
    def test_unhandled_leading_void_in_chapter_2_fails_gate(self):
        html = """
        <section class="chapter-section" data-ch="2">
            <span class="sentence-unit" id="c2-s-0" data-start="18.5" data-end="21.2" data-matched="1">
                <span class="w" data-s="18.5" data-e="21.2">Overcompensation</span>
            </span>
        </section>
        """
        errors = _check_temporal_integrity(html)
        self.assertTrue(any("unhandled leading void of 18.50s" in e for e in errors), f"Expected leading void error, got: {errors}")

    def test_reconciled_leading_void_passes_gate(self):
        html = """
        <section class="chapter-section" data-ch="2" data-skip-ranges="[{&quot;start&quot;: 0.0, &quot;end&quot;: 19.0}]">
            <span class="sentence-unit" id="c2-s-0" data-start="18.5" data-end="21.2" data-matched="1">
                <span class="w" data-s="18.5" data-e="21.2">Overcompensation</span>
            </span>
        </section>
        """
        errors = _check_temporal_integrity(html)
        self.assertEqual(errors, [])

    def test_unhandled_excessive_gap_between_sentences_fails_gate(self):
        # Simulates old Chapter 4 defect: Sentence 0 (1.36s) -> Sentence 1 (23.60s), gap = 22.24s
        html = """
        <section class="chapter-section" data-ch="4">
            <span class="sentence-unit" id="c4-s-0" data-start="0.0" data-end="1.36" data-matched="1">
                <span class="w" data-s="0.0" data-e="1.36">CHAPTER 4</span>
            </span>
            <span class="sentence-unit" id="c4-s-1" data-start="23.60" data-end="26.80" data-matched="1">
                <span class="w" data-s="23.60" data-e="26.80">What Kills Me</span>
            </span>
        </section>
        """
        errors = _check_temporal_integrity(html)
        self.assertTrue(any("unhandled excessive gap of 22.24s" in e for e in errors), f"Expected excessive gap error, got: {errors}")

    def test_reorder_flag_does_not_bypass_unhandled_forward_gap(self):
        # In the past, data-reorder="1" on Sentence 0 completely suppressed gap checks.
        # This test guarantees data-reorder="1" never acts as an unhandled gap backdoor.
        html = """
        <section class="chapter-section" data-ch="4">
            <span class="sentence-unit" id="c4-s-0" data-start="0.0" data-end="1.36" data-reorder="1" data-matched="1">
                <span class="w" data-s="0.0" data-e="1.36">CHAPTER 4</span>
            </span>
            <span class="sentence-unit" id="c4-s-1" data-start="23.60" data-end="26.80" data-matched="1">
                <span class="w" data-s="23.60" data-e="26.80">What Kills Me</span>
            </span>
        </section>
        """
        errors = _check_temporal_integrity(html)
        self.assertTrue(any("unhandled excessive gap of 22.24s" in e for e in errors), f"Expected gate rejection despite data-reorder, got: {errors}")

    def test_contiguous_patched_sentences_pass_gate(self):
        # Simulates newly patched Chapter 4 with restored summary sentences
        html = """
        <section class="chapter-section" data-ch="4">
            <span class="sentence-unit" id="c4-s-0" data-start="0.0" data-end="1.36" data-matched="1">
                <span class="w" data-s="0.0" data-e="1.36">CHAPTER 4</span>
            </span>
            <span class="sentence-unit" id="c4-s-1" data-start="1.36" data-end="6.80" data-matched="1">
                <span class="w" data-s="1.36" data-e="6.80">The antifragility of the whole</span>
            </span>
            <span class="sentence-unit" id="c4-s-2" data-start="7.20" data-end="9.80" data-matched="1">
                <span class="w" data-s="7.20" data-e="9.80">why death is a necessity</span>
            </span>
            <span class="sentence-unit" id="c4-s-3" data-start="23.60" data-end="26.80" data-skip-ranges="[{&quot;start&quot;: 9.8, &quot;end&quot;: 23.6}]" data-matched="1">
                <span class="w" data-s="23.60" data-e="26.80">What Kills Me</span>
            </span>
        </section>
        """
        errors = _check_temporal_integrity(html)
        self.assertEqual(errors, [])


class EpubSummaryExtractorTests(unittest.TestCase):
    def test_extract_chapter_summaries_from_epub(self):
        with tempfile.TemporaryDirectory() as td:
            epub_path = Path(td) / "sample_map.epub"
            with zipfile.ZipFile(epub_path, "w") as zf:
                zf.writestr("mimetype", "application/epub+zip")
                zf.writestr("META-INF/container.xml", """<?xml version="1.0"?>
                <container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
                   <rootfiles>
                      <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
                   </rootfiles>
                </container>""")
                zf.writestr("OEBPS/content.opf", """<?xml version="1.0"?>
                <package version="2.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId">
                   <metadata><title>Sample</title></metadata>
                   <manifest>
                      <item id="map" href="map.xhtml" media-type="application/xhtml+xml"/>
                   </manifest>
                   <spine><itemref idref="map"/></spine>
                </package>""")
                zf.writestr("OEBPS/map.xhtml", """<?xml version="1.0" encoding="utf-8"?>
                <html xmlns="http://www.w3.org/1999/xhtml">
                <head><title>Chapter Summaries and Map</title></head>
                <body>
                    <h1>Chapter Summaries and Map</h1>
                    <p><b>CHAPTER 1</b>. Explains how we missed antifragility in classrooms.</p>
                    <p><b>CHAPTER 2</b>. Where we find overcompensation.</p>
                    <p><b>CHAPTER 4</b>. The antifragility of the whole often depends on the fragility of the parts.</p>
                    <p><b>EPILOGUE</b>. What happens when Nero leaves to go to the Levant.</p>
                </body>
                </html>""")

            summaries = extract_chapter_summaries_from_epub(epub_path)
            self.assertIn("1", summaries)
            self.assertIn("2", summaries)
            self.assertIn("4", summaries)
            self.assertIn("EPILOGUE", summaries)
            self.assertIn("Explains how we missed", summaries["1"])
            self.assertIn("antifragility of the whole", summaries["4"])


if __name__ == "__main__":
    unittest.main()
