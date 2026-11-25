"""Paired bootstrap: determinism, pairing, and the interval bracketing the delta."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evalkit import paired_bootstrap_ci
from evalkit.bootstrap import case_value

BASELINE = [True] * 23 + [False] * 7
IMPROVED = [True] * 25 + [False] * 5


class BootstrapTests(unittest.TestCase):
    def test_same_seed_returns_the_same_interval(self):
        first = paired_bootstrap_ci(BASELINE, IMPROVED, n=2000, seed=42)
        second = paired_bootstrap_ci(BASELINE, IMPROVED, n=2000, seed=42)
        self.assertEqual(first["ci95"], second["ci95"])
        self.assertEqual(first["delta"], second["delta"])

    def test_a_different_seed_moves_the_interval(self):
        # 0/1 values only span 31 possible means for 30 cases, so percentiles
        # coincide often. Continuous per-case values show the seed feeds the draw.
        base = [index / 200 for index in range(200)]
        better = [value + (0.013 if index % 3 == 0 else 0.0) for index, value in enumerate(base)]
        first = paired_bootstrap_ci(base, better, n=2000, seed=42)
        second = paired_bootstrap_ci(base, better, n=2000, seed=43)
        self.assertNotEqual(first["ci95"], second["ci95"])

    def test_the_interval_brackets_the_point_delta(self):
        payload = paired_bootstrap_ci(BASELINE, IMPROVED, n=2000, seed=7)
        self.assertAlmostEqual(payload["delta"], 0.0667, places=4)
        self.assertLessEqual(payload["ci95"][0], payload["delta"])
        self.assertGreaterEqual(payload["ci95"][1], payload["delta"])

    def test_the_same_interval_width_for_a_small_improvement_brackets_zero(self):
        narrow = [True] * 23 + [False] * 7
        barely = list(narrow)
        barely[23] = True
        barely[24] = True
        payload = paired_bootstrap_ci(narrow, barely, n=4000, seed=20261126)
        self.assertEqual(payload["ci95"][0], 0.0)
        self.assertFalse(payload["excludes_zero"])

    def test_the_report_records_its_inputs(self):
        payload = paired_bootstrap_ci(BASELINE, IMPROVED, n=100, seed=1)
        self.assertEqual(payload["resamples"], 100)
        self.assertEqual(payload["pairs"], 30)
        self.assertEqual(payload["seed"], 1)

    def test_unequal_lengths_are_rejected(self):
        with self.assertRaises(ValueError):
            paired_bootstrap_ci([True], [True, False])

    def test_one_case_is_not_enough(self):
        with self.assertRaises(ValueError):
            paired_bootstrap_ci([True], [False])

    def test_per_case_values_may_be_bools_numbers_or_dicts(self):
        self.assertEqual(case_value(True), 1.0)
        self.assertEqual(case_value(0), 0.0)
        self.assertEqual(case_value({"passed": True}), 1.0)
        with self.assertRaises(TypeError):
            case_value("yes")


if __name__ == "__main__":
    unittest.main()
