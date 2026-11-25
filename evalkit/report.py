"""Render a results payload as the markdown table quoted in the README.

    python -m evalkit.report results.json          # markdown table
    python -m evalkit.report results.json --json   # the same payload, reformatted

The markdown printed here is the block pasted into README.md, and
``tests/test_report.py`` fails when the README and the render drift apart.
"""
from __future__ import annotations

import argparse
import json
import sys

METRIC_ROWS = [
    ("recall_at_k", "recall@5"),
    ("citation_correct", "citation correct"),
    ("completeness", "complete"),
    ("passed", "passed"),
    ("refusal_accuracy", "refusals"),
]


def _cell(metrics: dict, key: str) -> str:
    bucket = metrics[key]
    if key == "refusal_accuracy":
        return f"{bucket['correct']}/{bucket['n']}"
    return f"{bucket['hits']}/{bucket['n']}"


def markdown_table(payload: dict) -> str:
    """The results table: one row per metric, one column per run, denominators included."""
    runs = payload["runs"]
    names = list(runs)
    header = "| Metric | " + " | ".join(names) + " |"
    rule = "|---|" + "|".join("---" for _ in names) + "|"
    lines = [header, rule]
    for key, label in METRIC_ROWS:
        cells = []
        for name in names:
            metrics = runs[name]["metrics"]
            if key == "refusal_accuracy":
                cell = _cell(metrics, key)
            elif key == "passed":
                cell = _cell(metrics, key)
            else:
                cell = _cell(metrics, key)
            cells.append(cell)
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def markdown_detail(payload: dict) -> str:
    """The two lines under the table: the paired interval and the negative control."""
    delta = payload["delta"]
    control = payload["negative_control"]
    detail = control["detail"]
    lines = [
        f"paired bootstrap on passed, {delta['pairs']} cases: "
        f"delta {delta['delta']:+.4f}, 95% CI [{delta['ci95'][0]:+.4f}, {delta['ci95'][1]:+.4f}], "
        f"{delta['resamples']} resamples, seed {delta['seed']}",
        f"negative control: observed {detail['observed']:.4f} vs shuffled mean "
        f"{detail['null_mean']:.4f}, p = {control['p_value']:.4f}, "
        f"separated = {str(control['separated']).lower()}",
    ]
    return "\n".join(lines)


def markdown_report(payload: dict) -> str:
    return markdown_table(payload) + "\n\n" + markdown_detail(payload) + "\n"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m evalkit.report",
        description="Print the markdown results table for a results.json payload.",
    )
    parser.add_argument("path", help="path to results.json")
    parser.add_argument("--json", action="store_true", help="print the payload as JSON instead")
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    payload = json.loads(open(args.path, encoding="utf-8").read())
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        sys.stdout.write(markdown_report(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
