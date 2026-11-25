"""Evaluate a list of cases with a runner, and report per-case rows plus aggregates.

``evaluate`` is the only place that knows how a run is scored. It returns:

* ``results``: one row per case, holding the case, the runner's Result, and the
  four per-case verdicts;
* ``metrics``: every aggregate, each carrying its own denominator (``n``), so a
  rate cannot be read without the count it came from.
"""
from __future__ import annotations

from .case import Case, Result
from .metrics import (
    answer_correct,
    citation_correct,
    completeness,
    recall_at_k,
    refusal_accuracy,
)


def _aggregate(pairs, scorer, k=None) -> dict:
    hits = sum(1 for case, result in pairs if scorer(case, result))
    n = len(pairs)
    out = {"hits": hits, "n": n, "rate": round(hits / n, 4) if n else None}
    if k is not None:
        out["k"] = k
    return out


def evaluate(cases, runner, k: int = 5) -> dict:
    """Score every case with ``runner`` and return rows plus aggregates.

    ``runner`` is any callable that takes a :class:`Case` and returns a
    :class:`Result` or a dict with the same fields.
    """
    cases = list(cases)
    if not cases:
        raise ValueError("evaluate needs at least one case")
    rows = []
    pairs = []
    for case in cases:
        result = Result.from_runner(case, runner(case))
        if result.case_id != case.id:
            raise ValueError(
                f"runner returned case_id {result.case_id!r} for case {case.id!r}"
            )
        pairs.append((case, result))
        rows.append(
            {
                "case": case,
                "result": result,
                "recall_at_k": recall_at_k(case, result, k),
                "citation_correct": citation_correct(case, result),
                "completeness": completeness(case, result),
                "passed": answer_correct(case, result, k),
            }
        )

    answerable = [(case, result) for case, result in pairs if not case.must_refuse]
    metrics = {
        "recall_at_k": _aggregate(answerable, lambda c, r: recall_at_k(c, r, k), k=k),
        "citation_correct": _aggregate(answerable, citation_correct),
        "completeness": _aggregate(answerable, completeness),
        # ``passed`` is over answerable cases only, matching how a score is quoted
        # ("25/30 answered correctly"); refusal cases are scored separately by
        # refusal_accuracy, so they are not doubled into the pass rate.
        "passed": _aggregate(answerable, lambda c, r: answer_correct(c, r, k)),
        "refusal_accuracy": refusal_accuracy(pairs),
        "cases": len(cases),
        "answerable": len(answerable),
        "must_refuse": len(cases) - len(answerable),
    }
    return {"cases": len(cases), "k": k, "results": rows, "metrics": metrics}


def metric_fraction(metrics: dict, name: str) -> str:
    """Render an aggregate as "hits/n", the way a result is quoted in prose."""
    bucket = metrics[name]
    if name == "refusal_accuracy":
        return f"{bucket['correct']}/{bucket['n']}"
    return f"{bucket['hits']}/{bucket['n']}"
