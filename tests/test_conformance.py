"""Conformance: the harness must reproduce rag-eval-demo's published numbers.

The fixtures are byte copies of three files published in
github.com/devops-gm88/rag-eval-demo. The digests below fail the suite if a
fixture is edited, so this test cannot be made to pass by changing the data.

What is genuinely recomputed here (not read back from the published totals):
  recall@5        from the recorded retrieved sources vs the expected sources
  citation        from the recorded matched fact form vs the declared facts
  complete        from the recorded answer text vs the declared facts
  refusals        from the recorded answer text ("NOT IN SOURCES")
  passed          from recall AND citation AND complete

What is replayed rather than recomputed: the model answers themselves, which
this repository does not re-generate (no model, no corpus). That boundary is
what the README's scope line states.
"""
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evalkit import evaluate, metric_fraction, paired_bootstrap_ci
from evalkit.published import FIXTURES, load_cases, load_totals, replay_runner

FIXTURE_DIGESTS = {
    "rag_eval_questions.json": "8c9e157d3565221d098159dd508ad7a649e071207749ce2518dd2cd50878f409",
    "eval_baseline.json": "8e30a8e04324846a236838611777c1f6930d74119cc87e6eb19fb60917db3d36",
    "eval_improved.json": "f53b21bf57776012111b9a1a6e090f53bdae3c0b6c82b38e1f50c4477cfe1d95",
}

PUBLISHED = {
    "baseline": {"recall_at_k": "28/30", "citation_correct": "25/30",
                 "completeness": "26/30", "passed": "25/30", "refusal_accuracy": "3/3"},
    "improved": {"recall_at_k": "28/30", "citation_correct": "27/30",
                 "completeness": "27/30", "passed": "27/30", "refusal_accuracy": "3/3"},
}


class FixtureIntegrityTests(unittest.TestCase):
    def test_fixtures_are_the_published_bytes(self):
        for name, expected in FIXTURE_DIGESTS.items():
            digest = hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest()
            self.assertEqual(digest, expected, name)

    def test_the_fixture_set_is_33_cases_30_answerable_3_refusals(self):
        questions = json.loads((FIXTURES / "rag_eval_questions.json").read_text())
        self.assertEqual(len(questions["answerable"]), 30)
        self.assertEqual(len(questions["unanswerable"]), 3)

    def test_every_case_has_a_published_row(self):
        cases = load_cases()
        self.assertEqual(len(cases), 33)
        for run in ("baseline", "improved"):
            runner = replay_runner(run)
            for case in cases:
                self.assertEqual(case.id, runner(case).case_id)


class ConformanceTests(unittest.TestCase):
    def setUp(self):
        self.cases = load_cases()
        self.evaluated = {run: evaluate(self.cases, replay_runner(run))
                          for run in ("baseline", "improved")}

    def test_baseline_reproduces_25_of_30(self):
        self.assertEqual(metric_fraction(self.evaluated["baseline"]["metrics"], "passed"), "25/30")

    def test_improved_reproduces_27_of_30(self):
        self.assertEqual(metric_fraction(self.evaluated["improved"]["metrics"], "passed"), "27/30")

    def test_refusals_reproduce_3_of_3(self):
        for run in ("baseline", "improved"):
            self.assertEqual(
                metric_fraction(self.evaluated[run]["metrics"], "refusal_accuracy"), "3/3"
            )

    def test_every_published_metric_reproduces(self):
        for run, expected in PUBLISHED.items():
            metrics = self.evaluated[run]["metrics"]
            for key, value in expected.items():
                self.assertEqual(metric_fraction(metrics, key), value, f"{run}/{key}")
                self.assertEqual(load_totals(run)["passed"],
                                 metrics["passed"]["hits"])

    def test_the_headline_numbers_literally_quoted_are_reproduced(self):
        baseline = metric_fraction(self.evaluated["baseline"]["metrics"], "passed")
        improved = metric_fraction(self.evaluated["improved"]["metrics"], "passed")
        refusals = metric_fraction(self.evaluated["improved"]["metrics"], "refusal_accuracy")
        self.assertEqual(f"{baseline} -> {improved}, {refusals} refusals",
                         "25/30 -> 27/30, 3/3 refusals")

    def test_the_paired_delta_is_two_cases(self):
        answerable = [row for row in self.evaluated["improved"]["results"]
                      if not row["case"].must_refuse]
        ids = {row["case"].id for row in answerable}
        passed_a = [row["passed"] for row in self.evaluated["baseline"]["results"]
                    if row["case"].id in ids]
        passed_b = [row["passed"] for row in answerable]
        payload = paired_bootstrap_ci(passed_a, passed_b, n=2000, seed=20261126)
        self.assertEqual(sum(passed_a), 25)
        self.assertEqual(sum(passed_b), 27)
        self.assertAlmostEqual(payload["delta"], 2 / 30, places=4)
        self.assertLessEqual(payload["ci95"][0], payload["delta"])
        self.assertGreaterEqual(payload["ci95"][1], payload["delta"])

    def test_the_delta_interval_touches_zero_so_no_significance_is_claimed(self):
        answerable = [row for row in self.evaluated["improved"]["results"]
                      if not row["case"].must_refuse]
        ids = {row["case"].id for row in answerable}
        passed_a = [row["passed"] for row in self.evaluated["baseline"]["results"]
                    if row["case"].id in ids]
        passed_b = [row["passed"] for row in answerable]
        payload = paired_bootstrap_ci(passed_a, passed_b, n=10000, seed=20261126)
        self.assertFalse(payload["excludes_zero"])


if __name__ == "__main__":
    unittest.main()
