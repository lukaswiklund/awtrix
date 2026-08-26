import time
import unittest
from unittest.mock import patch

from awtrix.codex import _extract_windows, render_codex, render_codex_week


class CodexUsageTests(unittest.TestCase):
    def test_extracts_short_and_weekly_windows_by_duration(self):
        result = {
            "rateLimits": {
                "primary": {
                    "usedPercent": 21,
                    "windowDurationMins": 300,
                    "resetsAt": 1_800_000_000,
                },
                "secondary": {
                    "usedPercent": 63,
                    "windowDurationMins": 10_080,
                    "resetsAt": 1_800_500_000,
                },
            }
        }

        self.assertEqual(
            _extract_windows(result),
            {
                "short": {"pct": 21.0, "resets_at": 1_800_000_000},
                "week": {"pct": 63.0, "resets_at": 1_800_500_000},
            },
        )

    def test_single_primary_weekly_window_is_not_mislabeled_short(self):
        result = {
            "rateLimits": {
                "primary": {
                    "usedPercent": 6,
                    "windowDurationMins": 10_080,
                    "resetsAt": 1_800_000_000,
                },
                "secondary": None,
            }
        }

        self.assertEqual(
            _extract_windows(result),
            {"week": {"pct": 6.0, "resets_at": 1_800_000_000}},
        )

    @patch("awtrix.claude.time.time", return_value=1_799_900_000)
    def test_rendering_uses_distinct_window_colors(self, _time):
        usage = {
            "short": {"pct": 31, "resets_at": 1_800_000_000},
            "week": {"pct": 58, "resets_at": 1_800_500_000},
        }

        self.assertEqual(render_codex(usage)["text"][0]["c"], "10A37F")
        self.assertEqual(render_codex_week(usage)["text"][0]["c"], "A970FF")

    def test_missing_optional_short_window_deletes_frame(self):
        usage = {"week": {"pct": 6, "resets_at": time.time() + 3600}}

        self.assertIsNone(render_codex(usage))
        self.assertEqual(render_codex(None)["text"], "CX?")

    def test_zero_percent_windows_are_hidden(self):
        usage = {
            "short": {"pct": 0, "resets_at": time.time() + 3600},
            "week": {"pct": 0.4, "resets_at": time.time() + 3600},
        }

        self.assertIsNone(render_codex(usage))
        self.assertIsNone(render_codex_week(usage))


if __name__ == "__main__":
    unittest.main()
