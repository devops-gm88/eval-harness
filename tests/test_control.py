"""The negative control: both branches, and the CLI exit codes.

Branch one: a real run separates from shuffled labels (p < alpha).
Branch two: a broken measurement does not, and the CLI exits non-zero.
"""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evalkit import Case, Result, negative_control
from evalkit.published import load_cases, replay_results

CASES = [
    Case(id="Q1", question="q1", expected="50 CAD", context_ids=("a",)),
    Case(id="Q2", question="q2", expected="41 rows", context_ids=("b",)),
    Case(id="Q3", question="q3", expected="2682 CAD", context_ids=("c",)),
    Case(id="U1", question="u1", must_refuse=True),
]


def honest_runner(case):
    facts = {"Q1": "50 CAD", "Q2": "41 rows", "Q3": "2682 CAD"}
    if case.must_refuse:
        return Result(case_id=case.id, answer="Not in sources.", refused=True)
    return Result(case_id=case.id, answer=f"The answer is {facts[case.id]}.",
                  retrieved_ids=list(case.context_ids), cited_texts=[facts[case.id]])


def broken_runner(case):
    return Result(case_id=case.id, answer="", refused=False)


class NegativeControlTests(unittest.TestCase):
    def test_a_real_signal_separates_from_shuffled_labels(self):
        results = [honest_runner(case) for case in CASES]
        report = negative_control(CASES, results, permutations=200, seed=11)
        self.assertTrue(report["separated"])
        self.assertLess(report["p_value"], 0.05)
        self.assertGreater(report["detail"]["observed"], report["detail"]["null_mean"])

    def test_a_broken_measurement_does_not_separate(self):
        results = [broken_runner(case) for case in CASES]
        report = negative_control(CASES, results, permutations=200, seed=11)
        self.assertFalse(report["separated"])
        self.assertEqual(report["p_value"], 1.0)
        self.assertEqual(report["detail"]["observed"], 0.0)

    def test_the_control_is_deterministic_for_a_seed(self):
        results = [honest_runner(case) for case in CASES]
        first = negative_control(CASES, results, permutations=100, seed=5)
        second = negative_control(CASES, results, permutations=100, seed=5)
        self.assertEqual(first, second)

    def test_the_detail_names_every_input(self):
        report = negative_control(CASES, [honest_runner(case) for case in CASES],
                                  permutations=50, seed=5, alpha=0.01)
        for key in ("observed", "null_mean", "null_p95", "permutations", "seed", "alpha", "cases"):
            self.assertIn(key, report["detail"])
        self.assertEqual(report["detail"]["permutations"], 50)

    def test_a_result_per_case_is_required(self):
        with self.assertRaises(ValueError):
            negative_control(CASES, [honest_runner(CASES[0])])

    def test_the_published_run_passes_the_control(self):
        report = negative_control(load_cases(), replay_results("improved"),
                                  permutations=300, seed=20261126)
        self.assertTrue(report["separated"])
        self.assertLess(report["p_value"], 0.01)


class ControlCliTests(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "evalkit.control", *args],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )

    def test_the_default_run_exits_zero(self):
        completed = self._run()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("control PASSED", completed.stdout)

    def test_shuffled_labels_make_the_cli_exit_non_zero(self):
        completed = self._run("--shuffle-labels")
        self.assertEqual(completed.returncode, 1)
        self.assertIn("control FAILED", completed.stderr)

    def test_the_cli_can_print_json(self):
        completed = self._run("--permutations", "50", "--json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('"separated": true', completed.stdout)


if __name__ == "__main__":
    unittest.main()
