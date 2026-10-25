from __future__ import annotations

import contextlib
import io
import json
import math
import tempfile
import unittest
from pathlib import Path

from three_ai_suite import scientist as ai_scientist


class ClassificationTests(unittest.TestCase):
    def test_domains_are_inferred(self) -> None:
        self.assertEqual(
            ai_scientist.classify("How do we improve checkout conversion?"),
            "conversion",
        )
        self.assertEqual(ai_scientist.classify("How do we reduce churn?"), "retention")
        self.assertEqual(ai_scientist.classify("How do we cut latency?"), "performance")
        self.assertEqual(ai_scientist.classify("The site had an outage"), "reliability")

    def test_default_domain_is_used_when_unknown(self) -> None:
        self.assertEqual(ai_scientist.classify("A completely unrelated question"), "conversion")


class HypothesisTests(unittest.TestCase):
    def test_generate_hypotheses(self) -> None:
        hypotheses = ai_scientist.generate_hypotheses("How do we improve conversion?", n=2)
        self.assertEqual(len(hypotheses), 2)
        self.assertEqual(hypotheses[0].id, 1)
        self.assertEqual(hypotheses[0].domain, "conversion")

    def test_generate_hypotheses_validates_n(self) -> None:
        with self.assertRaises(ValueError):
            ai_scientist.generate_hypotheses("conversion", n=0)
        with self.assertRaises(ValueError):
            ai_scientist.generate_hypotheses("conversion", n=99)

    def test_unknown_domain_is_rejected(self) -> None:
        with self.assertRaises(KeyError):
            ai_scientist.generate_hypotheses("conversion", domain="unknown")


class BayesianTests(unittest.TestCase):
    def test_posteriors_are_normalized(self) -> None:
        posteriors = ai_scientist.update_bayes(
            priors=[0.5, 0.5],
            claims=[0.2, 0.1],
            tested_idx=0,
            observed=0.2,
            sigma=0.05,
        )
        self.assertAlmostEqual(sum(posteriors), 1.0)
        self.assertGreater(posteriors[0], 0.99)

    def test_invalid_inputs_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ai_scientist.update_bayes([0.5, 0.5], [0.2, 0.1], tested_idx=0, observed=0.1, sigma=0)
        with self.assertRaises(ValueError):
            ai_scientist.update_bayes([0.5, 0.5], [0.2, 0.1], tested_idx=5, observed=0.1, sigma=0.1)
        with self.assertRaises(ValueError):
            ai_scientist.update_bayes([0.0, 1.0], [0.2, 0.1], tested_idx=0, observed=0.1, sigma=0.1)

    def test_run_loop_is_deterministic(self) -> None:
        first = ai_scientist.run_loop("How do we improve conversion?", seed=11)
        second = ai_scientist.run_loop("How do we improve conversion?", seed=11)
        self.assertEqual(first, second)
        self.assertTrue(math.isclose(sum(first.posteriors), 1.0))
        self.assertLessEqual(len(first.rounds), 8)
        self.assertEqual(first.best_hypothesis.id, first.best_index + 1)

    def test_convergence_threshold(self) -> None:
        result = ai_scientist.run_loop(
            "How do we reduce churn?",
            seed=3,
            convergence_threshold=0.99,
        )
        self.assertLessEqual(max(result.posteriors), 1.0)
        if result.converged:
            self.assertGreaterEqual(max(result.posteriors), 0.99)


class RenderingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.result = ai_scientist.run_loop("How do we improve conversion?", seed=5)

    def test_markdown_contains_key_sections(self) -> None:
        report = ai_scientist.render_markdown(self.result)
        self.assertIn("# AI Scientist Report", report)
        self.assertIn("## Recommendation", report)
        self.assertIn("## Experiment log", report)
        self.assertIn("simulated decision loop", report)

    def test_json_is_serializable(self) -> None:
        payload = ai_scientist.render_json(self.result)
        serialized = json.dumps(payload)
        self.assertIn("recommendation", serialized)
        self.assertTrue(payload["simulation"])

    def test_cli_json_output(self) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = ai_scientist.main(["run", "reduce", "churn", "--format", "json"])
        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["domain"], "retention")
        self.assertIn("posteriors_after", payload["rounds"][0])

    def test_cli_writes_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            out_path = Path(directory) / "reports" / "report.md"
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                code = ai_scientist.main(["run", "latency", "--out", str(out_path)])
            self.assertEqual(code, 0)
            self.assertTrue(out_path.exists())
            self.assertIn("AI Scientist Report", out_path.read_text(encoding="utf-8"))
            self.assertIn("Wrote", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
