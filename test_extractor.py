import unittest
from extract_epub import split_into_atomic_sentences, extract_chapter_from_epub

class SentenceBoundaryTests(unittest.TestCase):
    def test_parenthetical_sentence_is_separate(self):
        text = "First sentence. (A second sentence.) Two years later, a third sentence."
        self.assertEqual(split_into_atomic_sentences(text), [
            "First sentence.", "(A second sentence.)", "Two years later, a third sentence."
        ])

    def test_abbreviations_do_not_split(self):
        self.assertEqual(split_into_atomic_sentences("Dr. Smith arrived. He spoke."), [
            "Dr. Smith arrived.", "He spoke."
        ])

    def test_single_letter_name_initials(self):
        text = (
            "Instead, in the hope of making the Haldemans happy, Errol agreed that the boy would have "
            "names from that side of the family: Elon, after Maye’s grandfather J. Elon Haldeman, "
            "and Reeve, the maiden name of Maye’s maternal grandmother."
        )
        self.assertEqual(split_into_atomic_sentences(text), [text])

    def test_multiple_initials_and_authors(self):
        text = "He admired W. E. B. Du Bois and read J. K. Rowling and C. S. Lewis. Next, he met George R. R. Martin."
        self.assertEqual(split_into_atomic_sentences(text), [
            "He admired W. E. B. Du Bois and read J. K. Rowling and C. S. Lewis.",
            "Next, he met George R. R. Martin."
        ])

    def test_time_abbreviations_inside_vs_end_of_sentence(self):
        # Inside sentence (followed by comma or lowercase) -> do not split
        text1 = "He arrived at 10 a.m. on Tuesday."
        self.assertEqual(split_into_atomic_sentences(text1), [text1])

        # End of sentence (followed by capital starting next sentence) -> split
        text2 = "He arrived at 10 a.m. After getting calls from the school, she left."
        self.assertEqual(split_into_atomic_sentences(text2), [
            "He arrived at 10 a.m.",
            "After getting calls from the school, she left."
        ])

    def test_zip_slip_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            extract_chapter_from_epub("dummy.epub", "../escape.html", "out.json")
        with self.assertRaises(ValueError):
            extract_chapter_from_epub("dummy.epub", "/absolute/escape.html", "out.json")

    def test_footnote_residues_are_stripped(self):
        raw = "It has been estimated that 20 million people in India rose out of destitution in a decade.{7} In China, it fell from 374 million by 2004,{8} now just 10 percent."
        expected = [
            "It has been estimated that 20 million people in India rose out of destitution in a decade.",
            "In China, it fell from 374 million by 2004, now just 10 percent."
        ]
        self.assertEqual(split_into_atomic_sentences(raw), expected)

    def test_chapter_parser_ignores_sup_and_noteref(self):
        from extract_epub import ChapterParser
        parser = ChapterParser()
        html = '<p>Destitution in a decade.<sup class="calibre7"><a href="#fn1">{7}</a></sup> Next sentence.</p>'
        parser.feed(html)
        self.assertEqual(len(parser.elements), 1)
        self.assertEqual(parser.elements[0]["text"], "Destitution in a decade. Next sentence.")

    def test_shorthand_etc_splits_when_followed_by_sentence(self):
        text = "They bought art, health, music, etc. The fundamental fallacy is that prices are fixed."
        expected = [
            "They bought art, health, music, etc.",
            "The fundamental fallacy is that prices are fixed."
        ]
        self.assertEqual(split_into_atomic_sentences(text), expected)

    def test_footnote_inlining_inserts_substantive_footnote(self):
        text = "If the earth stood straight up on its axis,__ATTACH_NOTE_filepos123__ night and day would be equal. Next sentence."
        footnote_map = {"filepos123": "Purists can say that there is no up or down in space."}
        expected = [
            "If the earth stood straight up on its axis, night and day would be equal.",
            "Purists can say that there is no up or down in space.",
            "Next sentence."
        ]
        self.assertEqual(split_into_atomic_sentences(text, footnote_map=footnote_map), expected)

    def test_is_title_text_with_vs(self):
        from extract_epub import is_title_text
        self.assertTrue(is_title_text("Monopoly Prices vs. Competitive Prices"))
        self.assertTrue(is_title_text("Costs vs. Expenditures"))
        self.assertTrue(is_title_text("Benefits vs. Net Benefits"))


if __name__ == "__main__":
    unittest.main()
