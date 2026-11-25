"""The negative control: can this run be told apart from shuffled labels?

An eval that always scores well is not evidence. The control asks the harder
question: if the pairing between a case and its recorded answer were random,
would the score change? A measurement that cannot tell the two apart is
measuring nothing.

``negative_control`` is a permutation test. It keeps every recorded answer and
re-pairs them with the cases at random, scores each re-pairing with the same
rule the real run was scored with, and reports the share of those shuffles that
score at least as well as the real pairing. That share is the p-value. When the
real run carries signal the shuffles collapse to near zero and the p-value is
tiny; when it does not, they look the same and the p-value is ordinary.

The CLI exits non-zero when the shuffled pairing cannot be separated from the
real run, because that means the measurement is broken.
"""
from __future__ import annotations

import argparse
import json
import random
import sys

from .case import Case, Result
from .evaluate import evaluate
from .metrics import answer_correct

DEFAULT_PERMUTATIONS = 1000
DEFAULT_SEED = 20261126
DEFAULT_ALPHA = 0.05


def _score(cases, results, k: int) -> float:
    if not cases:
        raise ValueError("the control needs at least one case")
    passed = 0
    for case, result in zip(cases, results):
        if answer_correct(case, result, k):
            passed += 1
    return passed / len(cases)


def _percentile(ordered, q: float) -> float:
    index = min(len(ordered) - 1, max(0, int(q * len(ordered))))
    return round(ordered[index], 4)


def negative_control(cases, results, permutations: int = DEFAULT_PERMUTATIONS,
                     seed: int = DEFAULT_SEED, alpha: float = DEFAULT_ALPHA, k: int = 5) -> dict:
    """Permutation test of the case-to-result pairing.

    Returns ``{"separated", "p_value", "detail"}``. ``separated`` is False when
    the real pairing is indistinguishable from shuffled labels, which is the
    failure the control exists to catch.
    """
    cases = list(cases)
    results = list(results)
    if len(cases) != len(results):
        raise ValueError(
            f"the control needs one result per case: {len(cases)} cases, {len(results)} results"
        )
    if permutations < 1:
        raise ValueError("permutations must be positive")
    observed = _score(cases, results, k)

    rng = random.Random(seed)
    order = list(range(len(cases)))
    null_scores = []
    for _ in range(permutations):
        rng.shuffle(order)
        shuffled = [results[index] for index in order]
        null_scores.append(_score(cases, shuffled, k))

    at_least_observed = sum(1 for score in null_scores if score >= observed - 1e-12)
    p_value = (1 + at_least_observed) / (1 + permutations)
    ordered = sorted(null_scores)
    detail = {
        "observed": round(observed, 4),
        "null_mean": round(sum(null_scores) / len(null_scores), 4),
        "null_median": _percentile(ordered, 0.5),
        "null_p95": _percentile(ordered, 0.95),
        "null_max": round(ordered[-1], 4),
        "permutations": permutations,
        "seed": seed,
        "alpha": alpha,
        "cases": len(cases),
    }
    return {"separated": bool(p_value < alpha), "p_value": round(p_value, 6), "detail": detail}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m evalkit.control",
        description=(
            "Run the shuffled-pairing control on the published rag-eval-demo run. "
            "Exits 1 when the shuffled pairing cannot be separated from the real run."
        ),
    )
    parser.add_argument("--run", default="improved", choices=["baseline", "improved"],
                        help="published run to replay (default: improved)")
    parser.add_argument("--permutations", type=int, default=DEFAULT_PERMUTATIONS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--shuffle-labels", action="store_true",
                        help="deliberately break the pairing, to show the control failing")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    return parser


def main(argv=None) -> int:
    from .published import load_cases, replay_results

    args = build_parser().parse_args(argv)
    cases = load_cases()
    results = replay_results(args.run)
    if args.shuffle_labels:
        rng = random.Random(args.seed + 17)
        order = list(range(len(results)))
        rng.shuffle(order)
        results = [results[index] for index in order]
    report = negative_control(cases, results, permutations=args.permutations, seed=args.seed)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        detail = report["detail"]
        print(f"observed {detail['observed']:.4f}  shuffled mean {detail['null_mean']:.4f} "
              f"(p95 {detail['null_p95']:.4f}, max {detail['null_max']:.4f})")
        print(f"permutations {detail['permutations']}  seed {detail['seed']}  "
              f"p = {report['p_value']:.4f}  alpha {detail['alpha']}")
        if report["separated"]:
            print("control PASSED: the real run separates from shuffled labels")
    if not report["separated"]:
        print("control FAILED: the shuffled pairing cannot be separated from the real run, "
              "so this measurement is not measuring the thing it claims", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
