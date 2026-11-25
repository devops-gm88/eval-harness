"""Case validation. A malformed case must fail loudly, not score as a miss."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evalkit import Case


class CaseTests(unittest.TestCase):
    def test_minimal_answerable_case(self):
        case = Case(id="Q1", question="How many rows?", expected="41 ledger rows")
        self.assertEqual(case.fact_forms, ("41 ledger rows",))
        self.assertFalse(case.must_refuse)
        self.assertEqual(case.context_ids, ())

    def test_aliases_extend_the_fact_forms(self):
        case = Case(id="Q1", question="q", expected="50 CAD", aliases=["50.00 cad"])
        self.assertEqual(case.fact_forms, ("50 CAD", "50.00 cad"))

    def test_lists_are_stored_as_tuples_so_the_case_is_hashable(self):
        case = Case(id="Q1", question="q", expected="x", context_ids=["a", "b"])
        self.assertEqual(case.context_ids, ("a", "b"))
        self.assertEqual(len({case, case}), 1)

    def test_a_case_needs_an_id(self):
        with self.assertRaises(ValueError):
            Case(id=" ", question="q", expected="x")

    def test_a_case_needs_a_question(self):
        with self.assertRaises(ValueError):
            Case(id="Q1", question="", expected="x")

    def test_an_answerable_case_needs_an_expected_fact(self):
        with self.assertRaises(ValueError):
            Case(id="Q1", question="q")

    def test_a_refusal_case_must_not_carry_an_expected_fact(self):
        with self.assertRaises(ValueError):
            Case(id="U1", question="q", expected="x", must_refuse=True)

    def test_refusal_case_is_valid_without_an_expected_fact(self):
        case = Case(id="U1", question="What is the revenue?", must_refuse=True)
        self.assertTrue(case.must_refuse)

    def test_round_trip_through_dicts(self):
        case = Case(id="Q1", question="q", expected="x", context_ids=["s1"], aliases=["y"])
        self.assertEqual(Case.from_dict(case.to_dict()), case)

    def test_from_dict_accepts_the_published_eval_set_keys(self):
        case = Case.from_dict(
            {"id": "Q01", "question": "q", "key_fact": "50 CAD",
             "expected_sources": ["doc#section"], "aliases": ["50.00 cad"]}
        )
        self.assertEqual(case.expected, "50 CAD")
        self.assertEqual(case.context_ids, ("doc#section",))

    def test_cases_are_immutable(self):
        case = Case(id="Q1", question="q", expected="x")
        with self.assertRaises(Exception):
            case.expected = "y"


if __name__ == "__main__":
    unittest.main()
