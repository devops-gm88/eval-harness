"""evalkit: a dependency-free harness for scoring retrieval and agent output.

The public API is everything a caller needs and nothing else:

    from evalkit import Case, Result, evaluate, paired_bootstrap_ci, negative_control

Typical use: build a list of :class:`Case`, write a runner that returns a
:class:`Result` for each one, score it with :func:`evaluate`, then prove the
score is real with :func:`negative_control`.

Scope (stated once, here and in the README): single-turn, fixed eval sets,
string-matched facts, no multi-hop questions and no human grading.

``control`` and ``report`` are imported lazily (PEP 562) so that
``python -m evalkit.control`` and ``python -m evalkit.report`` do not import the
module they are about to run.
"""
from __future__ import annotations

from .bootstrap import DEFAULT_RESAMPLES, DEFAULT_SEED, paired_bootstrap_ci
from .case import Case, Result
from .evaluate import evaluate, metric_fraction
from .metrics import (
    answer_correct,
    citation_correct,
    completeness,
    contains,
    first_match,
    normalise,
    recall_at_k,
    refusal_accuracy,
    refusal_correct,
)

_LAZY = {
    "negative_control": ("evalkit.control", "negative_control"),
    "DEFAULT_ALPHA": ("evalkit.control", "DEFAULT_ALPHA"),
    "DEFAULT_PERMUTATIONS": ("evalkit.control", "DEFAULT_PERMUTATIONS"),
    "markdown_table": ("evalkit.report", "markdown_table"),
    "markdown_detail": ("evalkit.report", "markdown_detail"),
    "markdown_report": ("evalkit.report", "markdown_report"),
}

__all__ = [
    "Case",
    "Result",
    "evaluate",
    "metric_fraction",
    "paired_bootstrap_ci",
    "negative_control",
    "recall_at_k",
    "citation_correct",
    "completeness",
    "refusal_accuracy",
    "refusal_correct",
    "answer_correct",
    "normalise",
    "contains",
    "first_match",
    "markdown_table",
    "markdown_detail",
    "markdown_report",
    "DEFAULT_RESAMPLES",
    "DEFAULT_SEED",
    "DEFAULT_ALPHA",
    "DEFAULT_PERMUTATIONS",
]

__version__ = "1.0.0"


def __getattr__(name):
    if name in _LAZY:
        module_name, attribute = _LAZY[name]
        from importlib import import_module

        value = getattr(import_module(module_name), attribute)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
