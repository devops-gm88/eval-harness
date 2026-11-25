"""The report: committed results.json is fresh, and the README quotes what it prints."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from evalkit import markdown_report, markdown_table  # noqa: E402
from evalkit.report import markdown_detail  # noqa: E402

RESULTS = ROOT / "results.json"
README = ROOT / "README.md"


def load_payload():
    return json.loads(RESULTS.read_text(encoding="utf-8"))


class ResultsFreshnessTests(unittest.TestCase):
    def test_committed_results_json_matches_a_fresh_run(self):
        from make_results import build_payload

        fresh = build_payload()
        committed = load_payload()
        fresh.pop("generated_at", None)
        committed.pop("generated_at", None)
        self.assertEqual(json.dumps(fresh, sort_keys=True), json.dumps(committed, sort_keys=True))

    def test_the_committed_payload_records_its_own_provenance(self):
        payload = load_payload()
        self.assertEqual(payload["generated_by"], "scripts/make_results.py")
        self.assertEqual(payload["dataset"]["cases"], 33)
        self.assertEqual(payload["dataset"]["answerable"], 30)
        self.assertEqual(payload["dataset"]["must_refuse"], 3)
        self.assertTrue(payload["conformance"]["matches"])

    def test_every_committed_aggregate_has_a_denominator(self):
        payload = load_payload()
        for run in payload["runs"].values():
            for name, bucket in run["metrics"].items():
                self.assertIn("n", bucket, name)
                self.assertIn("rate", bucket, name)


class ReportRenderingTests(unittest.TestCase):
    def test_the_table_has_one_column_per_run_and_denominators_in_every_cell(self):
        table = markdown_table(load_payload())
        lines = table.splitlines()
        self.assertIn("| Metric | baseline | improved |", lines)
        for line in lines[2:]:
            self.assertIn("/", line)

    def test_the_readme_quotes_the_rendered_report_verbatim(self):
        rendered = markdown_report(load_payload()).strip()
        self.assertIn(rendered, README.read_text(encoding="utf-8"))

    def test_the_detail_line_carries_the_interval_and_the_control(self):
        detail = markdown_detail(load_payload())
        self.assertIn("95% CI", detail)
        self.assertIn("negative control", detail)
        self.assertIn("separated = true", detail)

    def test_the_cli_prints_the_same_report(self):
        completed = subprocess.run(
            [sys.executable, "-m", "evalkit.report", str(RESULTS)],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout.strip(), markdown_report(load_payload()).strip())

    def test_the_cli_reformats_to_json(self):
        completed = subprocess.run(
            [sys.executable, "-m", "evalkit.report", str(RESULTS), "--json"],
            cwd=ROOT, capture_output=True, text=True, timeout=120,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["dataset"]["cases"], 33)


if __name__ == "__main__":
    unittest.main()
