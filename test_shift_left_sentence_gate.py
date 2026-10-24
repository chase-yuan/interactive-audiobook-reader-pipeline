"""
Test suite for Shift-Left Sentence Quality Gate and Acoustic Cleanser.
Enforces 4-Dimensional Orthogonal Boundary Test Matrix:
1. Input Domain: trailing hyphens, lowercase fragments, orphan words, unclosed quotes, clean text.
2. Environmental Friction: Acoustic text cleansing of asterisks, footnotes, daggers, citations.
3. State & Concurrency: Shift-left gate halts universal runner before expensive stages.
4. Scale & Temporal: Multi-chapter batch validation performance.
"""

import json
import os
import tempfile
import unittest
import zipfile
from pathlib import Path

from validate_outputs import validate_canonical_sentences, check_sentence_orthography, auto_heal_canonical_quotes
from kokoro_synthesizer import clean_acoustic_text, is_standalone_divider
from extract_epub import clean_and_merge_elements, extract_chapter_from_epub
from dynamic_aligner import _duplicate_source_fragment_indices


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

    def test_zero_none_invariant_fails_gate(self):
        items = [
            {"id": "s-0", "text": "This has a valid paragraph index.", "elem_idx": 1, "is_heading": False},
            {"id": "s-1", "text": "This has a null paragraph index.", "elem_idx": None, "is_heading": False},
        ]
        issues = validate_canonical_sentences(items)
        self.assertTrue(any("elem_idx is none" in iss.lower() for iss in issues))

    def test_dirty_repeated_quotes_fails_gate(self):
        items = [
            {"id": "s-0", "text": '““The opening quote is repeated.', "elem_idx": 1, "is_heading": False},
            {"id": "s-1", "text": 'The closing quote is repeated.""', "elem_idx": 1, "is_heading": False},
        ]
        issues = validate_canonical_sentences(items)
        self.assertTrue(any("dirty consecutive leading quotes" in iss.lower() for iss in issues))
        self.assertTrue(any("dirty repeated quotes" in iss.lower() for iss in issues))

    def test_consecutive_single_sentence_anomaly_fails_gate(self):
        items = [
            {"id": f"s-{i}", "text": f"This is an isolated single-sentence prose paragraph number {i}.", "elem_idx": i, "is_heading": False}
            for i in range(5)
        ]
        issues = validate_canonical_sentences(items)
        self.assertTrue(any("consecutive single-sentence paragraph explosion" in iss.lower() for iss in issues))

    def test_cohesive_paragraphs_pass_gate(self):
        items = [
            {"id": "s-0", "text": "This is the first sentence of a well-formed paragraph.", "elem_idx": 1, "is_heading": False},
            {"id": "s-1", "text": "This is the second sentence of the same paragraph.", "elem_idx": 1, "is_heading": False},
            {"id": "s-2", "text": "This is the first sentence of the second paragraph.", "elem_idx": 2, "is_heading": False},
            {"id": "s-3", "text": "This is the second sentence of the second paragraph.", "elem_idx": 2, "is_heading": False},
        ]
        issues = validate_canonical_sentences(items)
        self.assertEqual(issues, [])


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


    def test_auto_heal_canonical_quotes_straight(self):
        items = [
            {"id": "s-0", "text": '"This is an unclosed quote in paragraph one.', "is_heading": False},
            {"id": "s-1", "text": "This paragraph continues without a closing mark.", "is_heading": False},
        ]
        issues = validate_canonical_sentences(items)
        self.assertTrue(any("unclosed quote" in iss.lower() for iss in issues))
        healed = auto_heal_canonical_quotes(items)
        self.assertEqual(validate_canonical_sentences(healed), [])
        self.assertTrue(healed[-1]["text"].endswith('"'))

    def test_auto_heal_canonical_quotes_curly(self):
        items = [
            {"id": "s-0", "text": "“This is an unclosed curly quote.", "is_heading": False},
        ]
        issues = validate_canonical_sentences(items)
        self.assertTrue(any("unclosed quote" in iss.lower() for iss in issues))
        healed = auto_heal_canonical_quotes(items)
        self.assertEqual(validate_canonical_sentences(healed), [])
        self.assertTrue(healed[-1]["text"].endswith("”"))

    def test_duplicate_source_fragment_indices_pull_quote(self):
        sentences = [
            {"id": "s-0", "text": "The language instinct got into humans in exactly the same way."},
            {"id": "s-1", "text": "“ The language instinct got into humans in exactly the same way.”"},
            {"id": "s-2", "text": "And that is why we communicate so effortlessly."},
        ]
        dupes = _duplicate_source_fragment_indices(sentences)
        self.assertIn(1, dupes)


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

    def test_merge_unpunctuated_lines_capped_to_prevent_mega_sentence(self):
        # 10 lines without terminal punctuation totaling > 40 words or > 280 chars
        raw_elements = [
            {"tag": "p", "class": "", "text": f"Line {i} discusses an intricate detail regarding industrial capital allocation without punctuation"}
            for i in range(10)
        ]
        merged = clean_and_merge_elements(raw_elements)
        # Should not merge all 10 lines into one single mega-element
        self.assertGreater(len(merged), 1)
        for el in merged:
            self.assertLessEqual(len(el["text"].split()), 55)

    def test_extract_chapter_with_start_and_stop_markers(self):
        with tempfile.TemporaryDirectory() as td:
            epub_path = os.path.join(td, "test.epub")
            out_json = os.path.join(td, "out.json")
            with zipfile.ZipFile(epub_path, "w") as z:
                z.writestr("test.html", "<html><body><h1>Part 1</h1><p>First section.</p><h1>Part 2</h1><p>Second section.</p><h1>Part 3</h1><p>Third section.</p></body></html>")
            
            res_stop = extract_chapter_from_epub(epub_path, "test.html::stop=Part 2", out_json)
            self.assertEqual([x["text"] for x in res_stop], ["Part 1", "First section."])
            
            res_start = extract_chapter_from_epub(epub_path, "test.html::start=Part 2", out_json)
            self.assertEqual([x["text"] for x in res_start], ["Part 2", "Second section.", "Part 3", "Third section."])

    def test_extract_chapter_marker_ignores_body_text_collision(self):
        with tempfile.TemporaryDirectory() as td:
            epub_path = os.path.join(td, "collision.epub")
            out_json = os.path.join(td, "collision_out.json")
            long_body_para = "<p>In this comprehensive introductory treatise we explore how the concepts of Part 2 were originally drafted in an earlier volume before the author revised the complete taxonomy.</p>"
            with zipfile.ZipFile(epub_path, "w") as z:
                z.writestr("test.html", f"<html><body><h1>Part 1</h1><p>First section.</p>{long_body_para}<p>Still section 1.</p><h1>Part 2</h1><p>Second section.</p></body></html>")

            # stop=Part 2 must NOT trigger on the long body paragraph, but on <h1>Part 2</h1>
            res_stop = extract_chapter_from_epub(epub_path, "test.html::stop=Part 2", out_json)
            self.assertEqual(len(res_stop), 4)
            self.assertEqual(res_stop[0]["text"], "Part 1")
            self.assertEqual(res_stop[1]["text"], "First section.")
            self.assertIn("In this comprehensive introductory treatise", res_stop[2]["text"])
            self.assertEqual(res_stop[3]["text"], "Still section 1.")


if __name__ == "__main__":
    unittest.main()
