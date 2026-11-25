"""Paired bootstrap confidence interval on the difference between two runs.

The two runs are scored on the same cases, so the resampling is paired: one
draw of case indices is used for both runs, which keeps the per-case correlation
that makes a paired interval narrower than two independent ones.

Standard library only, and seedable: the same seed returns the same interval,
which the test suite asserts.
"""
from __future__ import annotations

import random

DEFAULT_RESAMPLES = 10000
DEFAULT_SEED = 20261126


def case_value(item):
    """Read one case's 0/1 value from a bool, a number, a dict or a Result row."""
    if isinstance(item, bool):
        return float(item)
    if isinstance(item, (int, float)):
        return float(item)
    if isinstance(item, dict):
        for key in ("passed", "value", "correct"):
            if key in item:
                return float(bool(item[key]))
    raise TypeError(f"cannot read a per-case value from {type(item).__name__}")


def _percentile_interval(values, low=0.025, high=0.975) -> list[float]:
    ordered = sorted(values)
    start = int(low * len(ordered))
    end = max(start, int(high * len(ordered)) - 1)
    return [round(ordered[start], 4), round(ordered[end], 4)]


def paired_bootstrap_ci(results_a, results_b, n: int = DEFAULT_RESAMPLES, seed: int = DEFAULT_SEED) -> dict:
    """95% interval on ``mean(b) - mean(a)`` over the same cases.

    ``results_a`` and ``results_b`` are per-case results in the same case order.
    Each item may be a bool, a 0/1 number, or a dict carrying ``passed``.
    """
    a = [case_value(item) for item in results_a]
    b = [case_value(item) for item in results_b]
    if len(a) != len(b):
        raise ValueError(
            f"paired bootstrap needs the same cases on both sides: {len(a)} vs {len(b)}"
        )
    if len(a) < 2:
        raise ValueError("paired bootstrap needs at least two cases")
    if n < 1:
        raise ValueError("resamples must be positive")

    rng = random.Random(seed)
    pairs = len(a)
    deltas = []
    for _ in range(n):
        total_a = 0.0
        total_b = 0.0
        for _ in range(pairs):
            index = rng.randrange(pairs)
            total_a += a[index]
            total_b += b[index]
        deltas.append((total_b - total_a) / pairs)

    point = sum(b) / pairs - sum(a) / pairs
    ci = _percentile_interval(deltas)
    return {
        "delta": round(point, 4),
        "ci95": ci,
        "resamples": n,
        "pairs": pairs,
        "seed": seed,
        "excludes_zero": ci[0] > 0 or ci[1] < 0,
    }
