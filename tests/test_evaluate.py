"""evaluate(): per-case rows, aggregates that name their denominator, runner checks."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evalkit import Case, Result, evaluate, metric_fraction

CASES = [
    Case(id="Q1", question="q1", expected="50 CAD", context_ids=("doc-a",)),
    Case(id="Q2", question="q2", expected="41 rows", context_ids=("doc-b",)),
    Case(id="U1", question="u1", must_refuse=True),
]


def runner(case):
    if case.id == "Q1":
        return {"answer": "It was 50 CAD.", "retrieved_ids": ["doc-a"],
                "cited_texts": ["the threshold was 50 CAD"]}
    if case.id == "Q2":
        return {"answer": "I could not find that.", "retrieved_ids": ["doc-b"]}
    return {"answer": "Not in sources.", "refused": True}


class EvaluateTests(unittest.TestCase):
    def setUp(self):
        self.payload = evaluate(CASES, runner)

    def test_one_row_per_case_and_the_case_order_is_kept(self):
        self.assertEqual([row["case"].id for row in self.payload["results"]], ["Q1", "Q2", "U1"])
        self.assertEqual(self.payload["cases"], 3)

    def test_every_aggregate_names_its_denominator(self):
        metrics = self.payload["metrics"]
        for name in ("recall_at_k", "citation_correct", "completeness", "passed"):
            self.assertEqual(metrics[name]["n"], 2, name)
            self.assertIn("rate", metrics[name], name)
        self.assertEqual(metrics["refusal_accuracy"]["n"], 1)

    def test_passed_is_over_answerable_cases_only(self):
        self.assertEqual(metric_fraction(self.payload["metrics"], "passed"), "1/2")
        self.assertEqual(metric_fraction(self.payload["metrics"], "refusal_accuracy"), "1/1")

    def test_a_refusal_is_not_a_pass_on_an_answerable_case(self):
        payload = evaluate(CASES, lambda case: {"refused": True, "answer": "Not in sources."})
        self.assertEqual(metric_fraction(payload["metrics"], "passed"), "0/2")

    def test_a_runner_may_return_a_result_instance(self):
        payload = evaluate([CASES[0]], lambda case: Result(case_id="Q1", answer="50 CAD",
                                                           retrieved_ids=["doc-a"],
                                                           cited_texts=["50 CAD"]))
        self.assertEqual(metric_fraction(payload["metrics"], "passed"), "1/1")

    def test_a_runner_returning_the_wrong_case_id_fails_loudly(self):
        with self.assertRaises(ValueError):
            evaluate([CASES[0]], lambda case: Result(case_id="Q9", answer="50 CAD"))

    def test_an_empty_case_list_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate([], runner)

    def test_a_none_result_scores_as_a_miss_rather_than_crashing(self):
        payload = evaluate([CASES[0]], lambda case: None)
        self.assertEqual(metric_fraction(payload["metrics"], "passed"), "0/1")

    def test_metric_fraction_reads_the_hits_and_the_denominator(self):
        metrics = {"passed": {"hits": 27, "n": 30, "rate": 0.9}}
        self.assertEqual(metric_fraction(metrics, "passed"), "27/30")


if __name__ == "__main__":
    unittest.main()
