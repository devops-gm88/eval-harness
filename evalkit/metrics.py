"""Per-case metrics. Every one is a yes/no on one case, so a rate is a count.

The matching rule is deliberately boring: normalise the text, then ask whether
the expected fact appears in it. Nothing here understands meaning, and that is
the point - a reviewer can reproduce every hit by eye.

Normalisation (the same rule the published rag-eval-demo run used) lowercases,
drops "$" and thousands commas, folds curly quotes, turns punctuation into
spaces, and drops the articles "the", "a", "an". Dropping articles lets
"2 of 5" match "2 of the 5 cases"; the articles carry no meaning in a fact
check.
"""
from __future__ import annotations

import re

from .case import Case, Result

PUNCT = re.compile(r"[^a-z0-9./%+#\- ]+")
ARTICLES = {"the", "a", "an"}


def normalise(text: str) -> str:
    """Lowercase, strip currency and thousands separators, fold quotes, drop articles."""
    if text is None:
        return ""
    text = str(text).lower()
    text = text.replace("$", "").replace(",", "")
    text = text.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')
    text = PUNCT.sub(" ", text)
    tokens = [token for token in text.split() if token not in ARTICLES]
    return " ".join(tokens)


def contains(haystack: str, needle: str) -> bool:
    """True when ``needle`` appears in ``haystack`` after normalisation."""
    needle_normalised = normalise(needle)
    if not needle_normalised:
        return False
    return needle_normalised in normalise(haystack)


def first_match(haystack: str, facts) -> str | None:
    """Return the first declared fact form found in ``haystack``, else None."""
    for fact in facts:
        if contains(haystack, fact):
            return fact
    return None


def recall_at_k(case: Case, result: Result, k: int = 5) -> bool:
    """An expected context id is among the first ``k`` retrieved ids."""
    if not case.context_ids:
        return False
    top_k = result.retrieved_ids[:k]
    return any(context_id in top_k for context_id in case.context_ids)


def citation_correct(case: Case, result: Result) -> bool:
    """A cited chunk carries the expected fact, and no citation index is out of range.

    When the runner recorded the matched fact string (``cited_fact``) instead of
    the cited chunk text, the string must be one of the case's declared fact
    forms. That keeps a hand-written or invented string from passing.
    """
    if result.refused:
        return False
    if result.invalid_citations:
        return False
    facts = case.fact_forms
    if result.cited_texts:
        return any(first_match(text, facts) for text in result.cited_texts)
    if result.cited_fact:
        return normalise(result.cited_fact) in {normalise(fact) for fact in facts}
    return False


def completeness(case: Case, result: Result) -> bool:
    """The answer itself contains the expected fact."""
    if result.refused:
        return False
    return first_match(result.answer, case.fact_forms) is not None


def answer_correct(case: Case, result: Result, k: int = 5) -> bool:
    """Recall, citation and completeness on the same case: the pass rule."""
    if case.must_refuse:
        return refusal_correct(case, result)
    return recall_at_k(case, result, k) and citation_correct(case, result) and completeness(case, result)


def refusal_correct(case: Case, result: Result) -> bool:
    """A case whose right answer is a refusal was refused."""
    if not case.must_refuse:
        raise ValueError(f"case {case.id!r} is answerable; it has no refusal to score")
    return bool(result.refused)


def refusal_accuracy(pairs) -> dict:
    """Refusals correctly refused over refusal cases asked. Names its denominator."""
    refusals = [(case, result) for case, result in pairs if case.must_refuse]
    correct = sum(1 for case, result in refusals if refusal_correct(case, result))
    return {
        "correct": correct,
        "n": len(refusals),
        "rate": round(correct / len(refusals), 4) if refusals else None,
    }
