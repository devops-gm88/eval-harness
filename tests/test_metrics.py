"""The four per-case metrics, including the branches that must return False."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evalkit import Case, Result, citation_correct, completeness, normalise, recall_at_k
from evalkit.metrics import refusal_accuracy, refusal_correct

CASE = Case(id="Q1", question="q", expected="50 CAD", aliases=["50.00 cad"],
            context_ids=("recon#evidence",))


class NormaliseTests(unittest.TestCase):
    def test_currency_and_thousands_separators_are_dropped(self):
        self.assertEqual(normalise("$2,682 CAD"), "2682 cad")

    def test_articles_are_dropped(self):
        self.assertEqual(normalise("2 of the 5 cases"), "2 of 5 cases")

    def test_punctuation_becomes_a_space(self):
        self.assertEqual(normalise("50 CAD; 41 rows!"), "50 cad 41 rows")

    def test_a_comma_is_a_thousands_separator_not_punctuation(self):
        self.assertEqual(normalise("a,b!"), "ab")

    def test_curly_quotes_fold_and_then_read_as_punctuation(self):
        self.assertEqual(normalise("\u201cit\u2019s\u201d"), "it s")

    def test_none_is_empty(self):
        self.assertEqual(normalise(None), "")


class RecallTests(unittest.TestCase):
    def test_expected_source_in_the_top_k(self):
        result = Result(case_id="Q1", retrieved_ids=["noise", "recon#evidence"])
        self.assertTrue(recall_at_k(CASE, result, k=2))

    def test_expected_source_outside_the_top_k(self):
        result = Result(case_id="Q1", retrieved_ids=["noise", "noise2", "recon#evidence"])
        self.assertFalse(recall_at_k(CASE, result, k=2))

    def test_a_case_without_context_ids_cannot_have_recall(self):
        case = Case(id="Q2", question="q", expected="x")
        self.assertFalse(recall_at_k(case, Result(case_id="Q2", retrieved_ids=["x"])))


class CitationTests(unittest.TestCase):
    def test_a_cited_chunk_containing_the_fact_is_correct(self):
        result = Result(case_id="Q1", cited_ids=["1"],
                        cited_texts=["The materiality threshold was 50 CAD."])
        self.assertTrue(citation_correct(CASE, result))

    def test_a_cited_chunk_without_the_fact_is_incorrect(self):
        result = Result(case_id="Q1", cited_ids=["1"], cited_texts=["Nothing relevant here."])
        self.assertFalse(citation_correct(CASE, result))

    def test_an_out_of_range_citation_is_incorrect_even_with_the_fact(self):
        result = Result(case_id="Q1", cited_ids=["9"],
                        cited_texts=["50 CAD was the threshold"], invalid_citations=[9])
        self.assertFalse(citation_correct(CASE, result))

    def test_recorded_fact_must_be_a_declared_form(self):
        good = Result(case_id="Q1", cited_ids=["1"], cited_fact="50.00 cad")
        fabricated = Result(case_id="Q1", cited_ids=["1"], cited_fact="whatever the model liked")
        self.assertTrue(citation_correct(CASE, good))
        self.assertFalse(citation_correct(CASE, fabricated))

    def test_no_citation_at_all_is_incorrect(self):
        self.assertFalse(citation_correct(CASE, Result(case_id="Q1", answer="50 CAD")))

    def test_a_refusal_is_never_a_correct_citation(self):
        result = Result(case_id="Q1", refused=True, cited_texts=["50 CAD"])
        self.assertFalse(citation_correct(CASE, result))


class CompletenessTests(unittest.TestCase):
    def test_the_fact_in_the_answer(self):
        self.assertTrue(completeness(CASE, Result(case_id="Q1", answer="It used 50 CAD.")))

    def test_an_alias_counts(self):
        self.assertTrue(completeness(CASE, Result(case_id="Q1", answer="threshold 50.00 cad")))

    def test_an_unrelated_answer_is_incomplete(self):
        self.assertFalse(completeness(CASE, Result(case_id="Q1", answer="Not in sources.")))

    def test_a_refusal_is_incomplete(self):
        self.assertFalse(completeness(CASE, Result(case_id="Q1", refused=True, answer="50 CAD")))


class RefusalTests(unittest.TestCase):
    def test_refusal_correct_only_accepts_refusal_cases(self):
        case = Case(id="U1", question="q", must_refuse=True)
        self.assertTrue(refusal_correct(case, Result(case_id="U1", refused=True)))
        self.assertFalse(refusal_correct(case, Result(case_id="U1", refused=False)))
        with self.assertRaises(ValueError):
            refusal_correct(CASE, Result(case_id="Q1", refused=True))

    def test_refusal_accuracy_names_its_denominator(self):
        refusal = Case(id="U1", question="q", must_refuse=True)
        pairs = [(CASE, Result(case_id="Q1")),
                 (refusal, Result(case_id="U1", refused=True)),
                 (refusal, Result(case_id="U1", refused=False))]
        bucket = refusal_accuracy(pairs)
        self.assertEqual(bucket, {"correct": 1, "n": 2, "rate": 0.5})


if __name__ == "__main__":
    unittest.main()
