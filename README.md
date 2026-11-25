# eval-harness

A dependency-free Python library that scores retrieval and agent output, and that fails when the
measurement itself is broken.

[![CI](https://github.com/devops-gm88/eval-harness/actions/workflows/ci.yml/badge.svg)](https://github.com/devops-gm88/eval-harness/actions/workflows/ci.yml)
**76 unittest tests**, Python 3.11 / 3.12 / 3.13, standard library only, whole suite under two
seconds. Conformance: it reproduces rag-eval-demo's published **25/30 -> 27/30, 3/3 refusals** from
the committed per-question JSON.

```bash
python3 -m unittest discover -v
```

That is the whole install: no dependencies, no venv, no network.

## The result this repo quotes

`python3 -m evalkit.report results.json` prints exactly this block, and the README is checked
against it, so the table cannot drift:

```text
| Metric | baseline | improved |
|---|---|---|
| recall@5 | 28/30 | 28/30 |
| citation correct | 25/30 | 27/30 |
| complete | 26/30 | 27/30 |
| passed | 25/30 | 27/30 |
| refusals | 3/3 | 3/3 |

paired bootstrap on passed, 30 cases: delta +0.0667, 95% CI [+0.0000, +0.1667], 10000 resamples, seed 20261126
negative control: observed 0.9091 vs shuffled mean 0.0391, p = 0.0010, separated = true
```

Read the second line honestly: the improvement is two cases, and the interval's lower bound is
zero. This dataset supports "two more questions were answered correctly"; it does not support a
significance claim, and the harness prints the interval instead of letting a score stand alone.

## Conformance: the library is not a toy

`tests/test_conformance.py` loads three committed byte copies of the published rag-eval-demo files
(`fixtures/SOURCES.md` records the SHA-256 of each), rebuilds the 30 answerable and 3 refusal cases,
and recomputes every metric from the per-question output: recall@5 from the retrieved sources,
citation correctness from the matched fact form, completeness from the answer text, refusal
accuracy from the answer text, and passed from those three. It then asserts the published totals:

```python
self.assertEqual(metric_fraction(improved["metrics"], "passed"), "27/30")
self.assertEqual(f"{baseline} -> {improved}, {refusals} refusals", "25/30 -> 27/30, 3/3 refusals")
```

A fixture whose bytes changed fails the suite before it can move a number.

## The negative control

An eval that scores well is not yet evidence. `negative_control(cases, results)` keeps every
recorded answer and re-pairs it with the cases at random 1000 times, scoring each shuffle with the
same rule. The p-value is the share of shuffles that score at least as well as the real run.

```bash
python3 -m evalkit.control                    # exits 0: the real run separates (p = 0.0010)
python3 -m evalkit.control --shuffle-labels   # exits 1: shuffled labels cannot be separated
```

Both branches are tested. The first is a real signal; the second is a measurement that carries no
signal, and the CLI refuses to pass it. There is also a deterministic dead run (every answer empty,
observed 0.0000, p = 1.0) in `tests/test_control.py`.

## API

```python
from evalkit import Case, Result, evaluate, paired_bootstrap_ci, negative_control

cases = [
    Case(id="Q1", question="What threshold was used?", expected="50 CAD",
         context_ids=("recon#evidence",), aliases=("50.00 cad",)),
    Case(id="U1", question="What was the client's revenue?", must_refuse=True),
]

def runner(case):
    return Result(case_id=case.id, answer=my_system(case.question),
                  retrieved_ids=..., cited_texts=[...], refused=...)

run = evaluate(cases, runner)          # per-case rows + aggregates, each with its denominator
run["metrics"]["passed"]               # {"hits": 25, "n": 30, "rate": 0.8333}
delta = paired_bootstrap_ci(a, b, n=10000, seed=20261126)   # same seed, same interval
control = negative_control(cases, results)                  # {"separated", "p_value", "detail"}
```

Every aggregate names its denominator (`hits` and `n`; `correct` and `n` for refusals), so a rate
cannot be quoted without the count it came from.

## What this does not measure

Scope, stated once: single-turn questions over a fixed eval set, scored by string-matched facts;
no multi-hop or multi-turn reasoning, no semantic grading, no human preference, and no re-generation
of model answers (the conformance run replays published answers rather than calling a model).

## Layout

```text
evalkit/case.py        Case and Result
evalkit/metrics.py     recall_at_k, citation_correct, completeness, refusal_accuracy
evalkit/evaluate.py    evaluate(), per-case rows + aggregates
evalkit/bootstrap.py   paired_bootstrap_ci() - percentile interval, seedable
evalkit/control.py     negative_control() + `python -m evalkit.control`
evalkit/report.py      markdown and JSON report + `python -m evalkit.report`
evalkit/published.py   loader for the committed published-run fixture (repo-specific)
fixtures/              byte copies of the published rag-eval-demo files
scripts/make_results.py regenerates results.json; a test fails when it goes stale
```

MIT. The published eval set and per-question runs come from
[rag-eval-demo](https://github.com/devops-gm88/rag-eval-demo).
