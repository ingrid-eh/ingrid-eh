import unittest

from rewrite_agent import rewrite_instructions


class RewriteAgentTests(unittest.TestCase):
    def test_pronoun_resolution_with_previous_object(self):
        result = rewrite_instructions("Review the report. Send it to legal.")
        self.assertIn("Send report to legal.", result["human_readable"])
        self.assertEqual(result["quality_checks"]["unresolved_references"], [])

    def test_unresolved_pronoun_flagged(self):
        result = rewrite_instructions("Send it now.")
        self.assertIn("it", result["quality_checks"]["unresolved_references"])
        self.assertGreaterEqual(len(result["quality_checks"]["notes"]), 1)

    def test_passive_to_active_conversion(self):
        result = rewrite_instructions("The report must be reviewed by the manager.")
        self.assertEqual(result["human_readable"], "the manager must review The report.")
        self.assertFalse(result["quality_checks"]["passive_sentences_remaining"])

    def test_mixed_multi_sentence_input(self):
        result = rewrite_instructions("The checklist was completed by Ana. Then she sent it to QA.")
        self.assertIn("Ana completed The checklist.", result["human_readable"])
        self.assertIn("Then she sent checklist to QA.", result["human_readable"])
        self.assertEqual(result["quality_checks"]["unresolved_references"], [])

    def test_no_change_when_already_clear(self):
        text = "Ana reviews the report daily."
        result = rewrite_instructions(text)
        self.assertEqual(result["human_readable"], text)


if __name__ == "__main__":
    unittest.main()
