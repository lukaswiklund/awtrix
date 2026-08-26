import unittest

from awtrix.claude import render_claude, render_claude_fable, render_claude_week


class ClaudeUsageTests(unittest.TestCase):
    def test_zero_percent_windows_are_hidden(self):
        usage = {
            "five_hour": {"pct": 0, "resets_at": None},
            "seven_day": {"pct": 0.4, "resets_at": None},
            "fable": {"pct": 0, "resets_at": None},
        }

        self.assertIsNone(render_claude(usage))
        self.assertIsNone(render_claude_week(usage))
        self.assertIsNone(render_claude_fable(usage))

    def test_fetch_failure_still_has_visible_error_frame(self):
        self.assertEqual(render_claude(None)["text"], "CC?")


if __name__ == "__main__":
    unittest.main()
