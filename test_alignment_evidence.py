import json
import tempfile
import unittest
from pathlib import Path

from dynamic_aligner import align_sentences_with_audio


class AlignmentEvidenceTests(unittest.TestCase):
    def run_alignment(self, words, sentences):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            acoustic = root / "acoustic.json"
            analysis = root / "analysis.json"
            output = root / "aligned.json"
            acoustic.write_text(json.dumps({"words": words}), encoding="utf-8")
            analysis.write_text(json.dumps(sentences), encoding="utf-8")
            return align_sentences_with_audio(acoustic, analysis, output)

    def test_exact_match_has_evidence(self):
        words = [{"word": word, "start": index, "end": index + 0.5} for index, word in enumerate("The quick brown fox".split())]
        item = self.run_alignment(words, [{"id": "s-1", "text": "The quick brown fox."}])[0]
        self.assertEqual(item["alignment_status"], "validated")
        self.assertEqual(item["matched_token_count"], 4)
        self.assertEqual(item["match_ratio"], 1.0)

    def test_weak_match_requires_review(self):
        words = [{"word": word, "start": index, "end": index + 0.5} for index, word in enumerate("noise only one token here".split())]
        item = self.run_alignment(words, [{"id": "s-1", "text": "one entirely different sentence"}])[0]
        self.assertEqual(item["alignment_status"], "review-required")
        self.assertFalse(item["fallback_used"])
        self.assertIsNone(item["start"])
        self.assertIsNone(item["end"])

    def test_out_of_order_global_match_requires_review(self):
        words = [{"word": word, "start": index, "end": index + 0.5} for index, word in enumerate("second exact phrase filler first exact phrase".split())]
        result = self.run_alignment(words, [{"id": "s-1", "text": "first exact phrase"}, {"id": "s-2", "text": "second exact phrase"}])
        self.assertEqual(result[0]["alignment_status"], "validated")
        self.assertEqual(result[1]["alignment_reason"], "global_match_out_of_order")

    def test_word_spans_follow_matching_blocks_after_audio_insertion(self):
        words = [{"word": word, "start": index, "end": index + 0.5} for index, word in enumerate("alpha extra beta gamma".split())]
        result = self.run_alignment(words, [{"id": "s-1", "text": "alpha beta gamma"}])[0]
        self.assertEqual([span["word"] for span in result["word_spans"]], ["alpha", "beta", "gamma"])
        self.assertEqual(result["word_spans"][1]["start"], 2)
        self.assertEqual(result["word_spans"][2]["start"], 3)

    def test_unmatched_word_is_interpolated_between_adjacent_matches(self):
        words = [{"word": word, "start": index, "end": index + 0.5} for index, word in enumerate("alpha beta".split())]
        item = self.run_alignment(words, [{"id": "s-1", "text": "alpha UNKNOWN beta"}])[0]
        unknown = item["word_spans"][1]
        self.assertGreaterEqual(unknown["start"], 0.5)
        self.assertLessEqual(unknown["end"], 1.0)

    def test_ambiguous_short_sentence_requires_review(self):
        words = [{"word": word, "start": index, "end": index + 0.5} for index, word in enumerate("No. Maybe no.".split())]
        item = self.run_alignment(words, [{"id": "s-1", "text": "No."}])[0]
        self.assertEqual(item["alignment_status"], "review-required")
        self.assertEqual(item["alignment_reason"], "ambiguous_short_sentence")

    def test_short_exact_match_uses_unique_neighbor_bounded_occurrence(self):
        words = [{"word": word, "start": index, "end": index + 0.5} for index, word in enumerate(
            "opening context excuse me closing context excuse me".split()
        )]
        result = self.run_alignment(words, [
            {"id": "s-1", "text": "opening context"},
            {"id": "s-2", "text": "Excuse me!"},
            {"id": "s-3", "text": "closing context"},
        ])
        self.assertEqual(result[1]["alignment_status"], "validated")
        self.assertEqual(result[1]["alignment_method"], "contextual_short_exact_match")
        self.assertEqual(result[1]["word_spans"][0]["start"], 2)

    def test_common_contraction_matches_spoken_expansion(self):
        words = [{"word": word, "start": index, "end": index + 0.5} for index, word in enumerate("I did not know".split())]
        item = self.run_alignment(words, [{"id": "s-1", "text": "I didn't know."}])[0]
        self.assertEqual(item["alignment_status"], "validated")
        self.assertEqual(item["matched_token_count"], 4)
        self.assertEqual(item["word_spans"][1]["start"], 1)

    def test_real_chapter_two_leading_attribution_is_bound_before_printed_quote(self):
        words = [{"word": word, "start": start, "end": end} for word, start, end in [
            ("Chapter", 0.0, 0.6), ("2.", 0.6, 0.9),
            ("A", 3.04, 3.76), ("quote", 3.76, 4.14), ("from", 4.14, 4.54),
            ("Major", 4.54, 5.24), ("Ofendra's", 5.24, 5.96), ("Guide", 5.96, 6.32),
            ("to", 6.32, 6.52), ("the", 6.52, 6.64), ("Writer's", 6.64, 7.0),
            ("Quadrant,", 7.0, 7.5), ("Unauthorized", 7.76, 8.76), ("Edition.", 8.76, 9.12),
            ("There's", 10.44, 11.16), ("a", 11.16, 11.26),
            ("misconception", 11.26, 11.86), ("that", 11.86, 12.42),
            ("it's", 12.42, 12.62), ("kill", 12.62, 13.16), ("or", 13.16, 13.42),
            ("be", 13.42, 13.72), ("killed", 13.72, 14.16), ("in", 14.16, 14.36),
            ("the", 14.36, 14.46), ("Writer's", 14.46, 14.82), ("Quadrant.", 14.82, 15.28),
        ]]
        result = self.run_alignment(words, [
            {"id": "s-0", "text": "There’s a misconception that it’s kill or be killed in the Riders Quadrant."},
            {"id": "s-1", "text": "—Major Afendra’s Guide to the Riders Quadrant (Unauthorized Edition)"},
        ])
        attribution = result[1]
        self.assertEqual(attribution["alignment_method"], "leading_epigraph_attribution")
        self.assertEqual(attribution["audio_start"], 3.04)
        self.assertEqual(attribution["audio_end"], 9.12)
        self.assertEqual(attribution["audio_order"], 5)
        self.assertTrue(attribution["has_audio_match"])
        self.assertEqual(result[0]["audio_start"], 10.44)

    def test_chapter_one_long_intro_does_not_hide_heading_or_attribution(self):
        intro = [f"intro{i}" for i in range(174)]
        spoken = intro + [
            "Chapter", "one", "A", "quote", "from", "Article", "One", "Section", "One",
            "The", "Dragon", "Rider's", "Codex", "A", "dragon", "without", "its", "rider",
            "is", "a", "tragedy",
        ]
        words = [
            {"word": word, "start": index * 0.5, "end": index * 0.5 + 0.4}
            for index, word in enumerate(spoken)
        ]
        result = self.run_alignment(words, [
            {"id": "s-0", "text": "A dragon without its rider is a tragedy."},
            {"id": "s-1", "text": "—Article One, Section One The Dragon Rider’s Codex"},
            {"id": "s-2", "text": "CHAPTER ONE"},
        ])
        self.assertEqual(result[1]["alignment_method"], "leading_epigraph_attribution")
        self.assertEqual(result[2]["alignment_method"], "chapter_heading_numeric_variant")
        self.assertEqual(result[0]["alignment_status"], "validated")

    def test_real_chapter_nine_recovered_dialogue_block_aligns_monotonically(self):
        spoken = "Dain sighs I never said I did not think you can cut it Violet You say it every day I snap Dain laces his fingers behind his neck".split()
        words = [{"word": word, "start": index, "end": index + 0.5} for index, word in enumerate(spoken)]
        result = self.run_alignment(words, [
            {"id": "s-289", "text": "Dain sighs."},
            {"id": "s-290", "text": "I never said I don’t think you can cut it, Violet."},
            {"id": "s-291", "text": "You say it every day!"},
            {"id": "s-292", "text": "I snap."},
            {"id": "s-300", "text": "Dain laces his fingers behind his neck."},
        ])
        self.assertTrue(all(item["alignment_status"] == "validated" for item in result))
        self.assertEqual([item["audio_start"] for item in result], sorted(item["audio_start"] for item in result))

    def test_real_chapter_twelve_recovered_short_exchange_aligns(self):
        spoken = "Please do not tell anyone I will not she whispers You are all right Other than having a few years of my life shaved off I laugh".split()
        words = [{"word": word, "start": index, "end": index + 0.5} for index, word in enumerate(spoken)]
        result = self.run_alignment(words, [
            {"id": "s-365", "text": "Please don’t tell anyone."},
            {"id": "s-366", "text": "I won’t, she whispers."},
            {"id": "s-367", "text": "You’re all right?"},
            {"id": "s-368", "text": "Other than having a few years of my life shaved off."},
            {"id": "s-369", "text": "I laugh."},
        ])
        self.assertTrue(all(item["alignment_status"] == "validated" for item in result))

    def test_observed_asr_name_and_number_variants_are_normalized(self):
        words = [{"word": word, "start": index, "end": index + 0.5} for index, word in enumerate(
            "Zayden Ryerson. 68 dead. Tern!".split()
        )]
        result = self.run_alignment(words, [
            {"id": "s-1", "text": "Xaden Riorson."},
            {"id": "s-2", "text": "Sixty-eight dead."},
            {"id": "s-3", "text": "Tairn!"},
        ])
        self.assertTrue(all(item["alignment_status"] == "validated" for item in result))

    def test_word_spans_do_not_drift_with_contractions_and_punctuation(self):
        # Regression: proportional linear mapping previously caused contractions (It's -> it is)
        # and punctuation to distort word indices, causing cursor to jump ahead by 1-3 words.
        spoken = "It is impossible to overpay the truly extraordinary CEO".split()
        words = [{"word": word, "start": 40.0 + index, "end": 40.0 + index + 0.8} for index, word in enumerate(spoken)]
        # Text has contraction "It's" and footnote citation "CEO.1"
        result = self.run_alignment(words, [
            {"id": "s-1", "text": "It’s impossible to overpay the truly extraordinary CEO.1"}
        ])[0]
        self.assertEqual(result["alignment_status"], "validated")
        spans = result["word_spans"]
        self.assertEqual(len(spans), 8)
        self.assertEqual(spans[0]["word"], "It’s")
        self.assertEqual(spans[0]["start"], 40.0)
        self.assertEqual(spans[3]["word"], "overpay")
        self.assertEqual(spans[3]["start"], 44.0)
        self.assertEqual(spans[7]["word"], "CEO.1")
        self.assertEqual(spans[7]["start"], 48.0)

    def test_adjacent_sentences_strictly_monotonic_without_overlap(self):
        # Guarantee that sentence end timestamps never exceed next sentence start timestamps
        spoken = "First sentence ends here Second sentence starts here".split()
        words = [{"word": word, "start": index * 2.0, "end": index * 2.0 + 1.5} for index, word in enumerate(spoken)]
        result = self.run_alignment(words, [
            {"id": "s-1", "text": "First sentence ends here."},
            {"id": "s-2", "text": "Second sentence starts here."},
        ])
        self.assertLessEqual(result[0]["audio_end"], result[1]["audio_start"])

