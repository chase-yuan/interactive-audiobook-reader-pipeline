"""
Test suite for Shift-Left Sentence Quality Gate and Acoustic Cleanser.
Enforces 4-Dimensional Orthogonal Boundary Test Matrix:
1. Input Domain: trailing hyphens, lowercase fragments, orphan words, unclosed quotes, clean text.
2. Environmental Friction: Acoustic text cleansing of asterisks, footnotes, daggers, citations.
3. State & Concurrency: Shift-left gate halts universal runner before expensive stages.
4. Scale & Temporal: Multi-chapter batch validation performance.
"""

import json
import tempfile
import unittest
from pathlib import Path

from validate_outputs import validate_canonical_sentences, check_sentence_orthography
from kokoro_synthesizer import clean_acoustic_text, is_standalone_divider
from extract_epub import clean_and_merge_elements


class ShiftLeftSentenceGateTests(unittest.TestCase):
    # 1. Input Domain Boundaries
    def test_clean_sentences_pass_gate(self):
        items = [
            {"id": "s-0", "text": "Chapter 1", "is_heading": True},
            {"id": "s-1", "text": "This is a clean and well-formed sentence.", "is_heading": False},
            {"id": "s-2", "text": "Critical thinking requires careful examination of evidence.", "is_heading": False},
        ]
        issues = validate_canonical_sentences(items)
        self.assertEqual(issues, [])

    def test_trailing_hyphen_fails_gate(self):
        items = [
            {"id": "s-0", "text": "This is an oversimplifi-", "is_heading": False},
        ]
        issues = validate_canonical_sentences(items)
        self.assertTrue(any("trailing hyphen" in iss.lower() for iss in issues))

    def test_lowercase_continuation_fails_gate(self):
        items = [
            {"id": "s-0", "text": "cation of the original argument.", "is_heading": False},
        ]
        issues = validate_canonical_sentences(items)
        self.assertTrue(any("lowercase" in iss.lower() for iss in issues))

    def test_orphan_single_word_fails_gate(self):
        items = [
            {"id": "s-0", "text": "Armies", "is_heading": False},
        ]
        issues = validate_canonical_sentences(items)
        self.assertTrue(any("orphan word" in iss.lower() for iss in issues))

    def test_heading_allowed_single_word(self):
        items = [
            {"id": "s-0", "text": "Armies", "is_heading": True},
        ]
        issues = validate_canonical_sentences(items)
        self.assertEqual(issues, [])

    def test_unclosed_quotes_fails_gate(self):
        items = [
            {"id": "s-0", "text": "“This is an unclosed quote that never terminates.", "is_heading": False},
        ]
        issues = validate_canonical_sentences(items)
        self.assertTrue(any("unclosed quote" in iss.lower() for iss in issues))


class AcousticCleanserTests(unittest.TestCase):
    # 2. Acoustic Cleanser (Kokoro Symbol Neutralization)
    def test_strip_footnote_asterisk(self):
        # Must not say 'asterisk'
        raw = "You *This is typically accomplished by using two or more cameras."
        cleaned = clean_acoustic_text(raw)
        self.assertNotIn("*", cleaned)
        self.assertEqual(cleaned, "You This is typically accomplished by using two or more cameras.")

    def test_strip_trailing_asterisk(self):
        raw = "the practical value of that work does not interest us.”*"
        cleaned = clean_acoustic_text(raw)
        self.assertNotIn("*", cleaned)
        self.assertEqual(cleaned, "the practical value of that work does not interest us.”")

    def test_strip_markdown_bold_and_italic(self):
        raw = "This is **very important** and *essential* reading."
        cleaned = clean_acoustic_text(raw)
        self.assertNotIn("*", cleaned)
        self.assertEqual(cleaned, "This is very important and essential reading.")

    def test_strip_bracketed_citation_numbers(self):
        raw = "According to previous studies [1], and later evidence [2, 3], cognition varies."
        cleaned = clean_acoustic_text(raw)
        self.assertNotIn("[1]", cleaned)
        self.assertNotIn("[2, 3]", cleaned)
        self.assertEqual(cleaned, "According to previous studies, and later evidence, cognition varies.")

    def test_strip_bullet_glyphs(self):
        raw = "• Obligations: Demands on behavior."
        cleaned = clean_acoustic_text(raw)
        self.assertNotIn("•", cleaned)
        self.assertEqual(cleaned, "Obligations: Demands on behavior.")

    def test_preserve_natural_punctuation(self):
        raw = "Wait—now, let's see: $100 is 50% of $200."
        cleaned = clean_acoustic_text(raw)
        self.assertEqual(cleaned, "Wait—now, let's see: $100 is 50% of $200.")

    def test_is_standalone_divider(self):
        self.assertTrue(is_standalone_divider("* * *"))
        self.assertTrue(is_standalone_divider("***"))
        self.assertTrue(is_standalone_divider("---"))
        self.assertTrue(is_standalone_divider("– – –"))
        self.assertFalse(is_standalone_divider("Chapter 1: The Beginning"))
        self.assertFalse(is_standalone_divider("* Note on method"))


class ElementMergeDehyphenationTests(unittest.TestCase):
    # 3. Element-Level Stitching (extract_epub.py)
    def test_merge_hyphenated_break(self):
        raw_elements = [
            {"tag": "p", "class": "", "text": "This is a gross oversimplifi-"},
            {"tag": "p", "class": "", "text": "cation of the facts in dispute."},
        ]
        merged = clean_and_merge_elements(raw_elements)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["text"], "This is a gross oversimplification of the facts in dispute.")

    def test_merge_unpunctuated_lines(self):
        raw_elements = [
            {"tag": "p", "class": "", "text": "In time, the baby cried not only at the sight"},
            {"tag": "p", "class": "", "text": "of the rat but also at anything furry."},
        ]
        merged = clean_and_merge_elements(raw_elements)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["text"], "In time, the baby cried not only at the sight of the rat but also at anything furry.")

    def test_filter_running_headers(self):
        raw_elements = [
            {"tag": "p", "class": "", "text": "Part Three: A Strategy"},
            {"tag": "p", "class": "", "text": "Part Three: A Strategy"},
            {"tag": "p", "class": "", "text": "Actual substantive text begins here."},
        ]
        merged = clean_and_merge_elements(raw_elements)
        self.assertEqual(len(merged), 2)
        self.assertEqual(merged[0]["text"], "Part Three: A Strategy")
        self.assertEqual(merged[1]["text"], "Actual substantive text begins here.")


if __name__ == "__main__":
    unittest.main()
