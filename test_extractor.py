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


if __name__ == "__main__":
    unittest.main()
