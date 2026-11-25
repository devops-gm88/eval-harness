"""Load the published rag-eval-demo fixture this repository validates against.

This module is repo-specific reference data, not part of the generic API. It
exists so the conformance test, the control CLI and the results script all read
the same committed JSON files instead of re-deriving them three ways.

The fixtures are byte copies of the files published in
``github.com/devops-gm88/rag-eval-demo``:

* ``fixtures/rag_eval_questions.json``  -> ``evals/questions.json``
* ``fixtures/eval_baseline.json``       -> ``reports/eval_baseline.json``
* ``fixtures/eval_improved.json``       -> ``reports/eval_improved.json``

Their SHA-256 digests are recorded in ``fixtures/SOURCES.md`` and asserted by
``tests/test_conformance.py``, so a silently modified fixture fails the suite.
"""
from __future__ import annotations

import json
from pathlib import Path

from .case import Case, Result

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"

RUN_FILES = {
    "baseline": "eval_baseline.json",
    "improved": "eval_improved.json",
}


def _read(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def load_questions() -> dict:
    return _read("rag_eval_questions.json")


def load_cases() -> list[Case]:
    """Build the 30 answerable cases plus the 3 refusal cases from the published set."""
    questions = load_questions()
    cases = [
        Case.from_dict(item)
        for item in questions["answerable"]
    ] + [
        Case(id=item["id"], question=item["question"], must_refuse=True)
        for item in questions["unanswerable"]
    ]
    return cases


def load_rows(run: str = "improved") -> dict[str, dict]:
    """Published per-question rows for one run, keyed by case id (answerable + refusals)."""
    if run not in RUN_FILES:
        raise ValueError(f"unknown run {run!r}; choose from {sorted(RUN_FILES)}")
    report = _read(RUN_FILES[run])
    rows = {row["id"]: row for row in report["rows"]}
    for row in report["refusals"]:
        rows[row["id"]] = row
    return rows


def load_totals(run: str = "improved") -> dict:
    """The published totals block, for the conformance test to compare against."""
    return _read(RUN_FILES[run])["totals"]


def replay_results(run: str = "improved") -> list[Result]:
    """Turn the published per-question rows into Results in the case order."""
    rows = load_rows(run)
    results = []
    for case in load_cases():
        row = rows[case.id]
        results.append(
            Result(
                case_id=case.id,
                answer=row.get("answer", ""),
                refused=bool(row.get("refused", False)),
                retrieved_ids=[item["source"] if isinstance(item, dict) else str(item)
                               for item in row.get("retrieved") or []],
                cited_ids=[str(index) for index in row.get("cited") or []],
                cited_fact=row.get("citation_fact"),
                invalid_citations=list(row.get("invalid_citations") or []),
            )
        )
    return results


def replay_runner(run: str = "improved"):
    """A runner that replays the published rows, for ``evaluate``."""
    results = {result.case_id: result for result in replay_results(run)}

    def runner(case: Case) -> Result:
        return results[case.id]

    return runner
