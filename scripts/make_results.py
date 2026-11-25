"""Regenerate results.json from the committed fixture.

    python3 scripts/make_results.py

Nothing in the payload is typed by hand: every count comes from ``evaluate``,
the interval from ``paired_bootstrap_ci`` and the p-value from
``negative_control``. ``tests/test_report.py`` fails when the committed
results.json no longer matches a fresh run of this script.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evalkit import (  # noqa: E402
    DEFAULT_PERMUTATIONS,
    DEFAULT_RESAMPLES,
    DEFAULT_SEED,
    evaluate,
    markdown_report,
    metric_fraction,
    negative_control,
    paired_bootstrap_ci,
)
from evalkit.published import (  # noqa: E402
    load_cases,
    load_questions,
    load_rows,
    load_totals,
    replay_results,
    replay_runner,
)

RUNS = ("baseline", "improved")


def _rows(payload: dict) -> list[dict]:
    return [
        {
            "id": row["case"].id,
            "recall_at_k": row["recall_at_k"],
            "citation_correct": row["citation_correct"],
            "completeness": row["completeness"],
            "passed": row["passed"],
        }
        for row in payload["results"]
    ]


def build_payload() -> dict:
    questions = load_questions()
    cases = load_cases()
    evaluated = {run: evaluate(cases, replay_runner(run)) for run in RUNS}

    answerable_ids = [case.id for case in cases if not case.must_refuse]
    passed_a = [row["passed"] for row in evaluated["baseline"]["results"]
                if row["case"].id in answerable_ids]
    passed_b = [row["passed"] for row in evaluated["improved"]["results"]
                if row["case"].id in answerable_ids]
    delta = paired_bootstrap_ci(passed_a, passed_b, n=DEFAULT_RESAMPLES, seed=DEFAULT_SEED)

    control = negative_control(cases, replay_results("improved"),
                               permutations=DEFAULT_PERMUTATIONS, seed=DEFAULT_SEED)

    published = {run: load_totals(run) for run in RUNS}
    conformance = {
        "source": "github.com/devops-gm88/rag-eval-demo",
        "published": {
            run: {
                "recall_at_5": f"{published[run]['recall_at_5']}/{published[run]['questions']}",
                "citation_correct": f"{published[run]['citation_correct']}/{published[run]['questions']}",
                "answer_complete": f"{published[run]['answer_complete']}/{published[run]['questions']}",
                "passed": f"{published[run]['passed']}/{published[run]['questions']}",
                "refusals_correct": f"{published[run]['refusals_correct']}/{published[run]['unanswerable']}",
            }
            for run in RUNS
        },
        "reproduced": {
            run: {
                "recall_at_5": metric_fraction(evaluated[run]["metrics"], "recall_at_k"),
                "citation_correct": metric_fraction(evaluated[run]["metrics"], "citation_correct"),
                "answer_complete": metric_fraction(evaluated[run]["metrics"], "completeness"),
                "passed": metric_fraction(evaluated[run]["metrics"], "passed"),
                "refusals_correct": metric_fraction(evaluated[run]["metrics"], "refusal_accuracy"),
            }
            for run in RUNS
        },
    }
    conformance["matches"] = conformance["published"] == conformance["reproduced"]

    payload = {
        "generated_at": date.today().isoformat(),
        "generated_by": "scripts/make_results.py",
        "dataset": {
            "name": "rag-eval-demo published eval set",
            "source": "github.com/devops-gm88/rag-eval-demo",
            "fixtures": [
                "fixtures/rag_eval_questions.json",
                "fixtures/eval_baseline.json",
                "fixtures/eval_improved.json",
            ],
            "cases": len(cases),
            "answerable": len(answerable_ids),
            "must_refuse": len(cases) - len(answerable_ids),
            "corpus_documents": 57,
            "description": questions["description"],
            "runs": list(RUNS),
        },
        "runs": {
            run: {"metrics": {key: value for key, value in evaluated[run]["metrics"].items()
                              if isinstance(value, dict)}, "rows": _rows(evaluated[run])}
            for run in RUNS
        },
        "delta": delta,
        "negative_control": control,
        "conformance": conformance,
    }
    return payload


def main() -> int:
    payload = build_payload()
    target = ROOT / "results.json"
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(markdown_report(payload))
    print(f"wrote {target.relative_to(ROOT)}")
    if not payload["conformance"]["matches"]:
        print("conformance FAILED: the harness does not reproduce the published totals",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
