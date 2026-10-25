#!/usr/bin/env python3
"""AI Scientist - a transparent hypothesis and experiment loop.

The tool generates business hypotheses for a research question, runs a
deterministic simulated experiment loop, and updates the probability of every
hypothesis with Bayesian inference. Its main value is the decision loop: test,
observe, update, and recommend.

This is a simulation. The claims are configurable illustrative priors, not
measured causal effects.

Examples:
    python ai_scientist.py domains
    python ai_scientist.py run "How can we improve checkout conversion?"
    python ai_scientist.py run "How do we reduce churn?" --format json
    python ai_scientist.py run "How do we cut latency?" --rounds 6 --seed 7

License: MIT
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__version__ = "1.0.0"

DOMAINS: dict[str, tuple[tuple[str, float], ...]] = {
    "conversion": (
        ("Add social proof (reviews, user counts)", 0.12),
        ("Simplify the checkout flow", 0.18),
        ("Show limited-time discounts", 0.22),
        ("Personalize recommendations", 0.15),
    ),
    "retention": (
        ("Send weekly digest emails", 0.10),
        ("Gamify progress with streaks", 0.16),
        ("Add in-app onboarding tour", 0.09),
        ("Introduce tiered rewards", 0.20),
    ),
    "performance": (
        ("Add a CDN for static assets", 0.25),
        ("Cache hot database queries", 0.30),
        ("Move to edge compute", 0.35),
        ("Compress images with AVIF", 0.12),
    ),
    "reliability": (
        ("Add automated failover", 0.40),
        ("Implement circuit breakers", 0.28),
        ("Add retry with exponential backoff", 0.15),
        ("Run chaos experiments weekly", 0.32),
    ),
    "satisfaction": (
        ("Reduce first-response time", 0.20),
        ("Add proactive status updates", 0.14),
        ("Personalize the reply tone", 0.10),
        ("Add a self-serve help center", 0.18),
    ),
}

KEYWORD_MAP: dict[str, tuple[str, ...]] = {
    "conversion": ("conversion", "checkout", "buy", "purchase", "signup", "sign-up"),
    "retention": ("retention", "churn", "engagement", "stickiness", "return", "come back"),
    "performance": ("performance", "latency", "speed", "load time", "slow", "fast"),
    "reliability": ("reliability", "uptime", "availability", "outage", "failover", "error rate"),
    "satisfaction": ("satisfaction", "nps", "csat", "support", "complaint", "happiness"),
}

DEFAULT_DOMAIN = "conversion"


@dataclass(frozen=True)
class Hypothesis:
    """A testable action with an illustrative expected lift."""

    id: int
    action: str
    claim: float
    domain: str


@dataclass(frozen=True)
class Round:
    """The state transition produced by one simulated experiment."""

    round: int
    tested_hypothesis_id: int
    tested_action: str
    observed: float
    posteriors_before: tuple[float, ...]
    posteriors_after: tuple[float, ...]


@dataclass(frozen=True)
class Result:
    """A complete experiment loop result."""

    question: str
    domain: str
    hypotheses: tuple[Hypothesis, ...]
    rounds: tuple[Round, ...]
    priors: tuple[float, ...]
    posteriors: tuple[float, ...]
    true_hypothesis_id: int
    seed: int
    converged: bool
    convergence_threshold: float

    @property
    def best_index(self) -> int:
        return max(
            range(len(self.posteriors)),
            key=lambda index: (self.posteriors[index], -index),
        )

    @property
    def best_hypothesis(self) -> Hypothesis:
        return self.hypotheses[self.best_index]

    @property
    def best_posterior(self) -> float:
        return self.posteriors[self.best_index]


def classify(question: str) -> str:
    """Map a free-text question to the closest supported domain."""
    normalized = question.lower()
    scores = {
        domain: sum(1 for keyword in keywords if keyword in normalized)
        for domain, keywords in KEYWORD_MAP.items()
    }
    best_domain = max(scores, key=lambda domain: (scores[domain], -list(DOMAINS).index(domain)))
    return best_domain if scores[best_domain] > 0 else DEFAULT_DOMAIN


def generate_hypotheses(
    question: str,
    n: int = 4,
    domain: str | None = None,
) -> tuple[Hypothesis, ...]:
    """Create up to ``n`` hypotheses for the selected or inferred domain."""
    if n < 1:
        raise ValueError("n must be >= 1")

    selected_domain = (domain or classify(question)).lower()
    pool = DOMAINS.get(selected_domain)
    if pool is None:
        raise KeyError(f"unknown domain: {selected_domain}")
    if n > len(pool):
        raise ValueError(
            f"domain '{selected_domain}' has only {len(pool)} templates; requested {n}"
        )

    return tuple(
        Hypothesis(id=index + 1, action=action, claim=claim, domain=selected_domain)
        for index, (action, claim) in enumerate(pool[:n])
    )


def _log_gaussian(x: float, mu: float, sigma: float) -> float:
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    if not all(math.isfinite(value) for value in (x, mu, sigma)):
        raise ValueError("x, mu, and sigma must be finite")
    return -0.5 * math.log(2 * math.pi * sigma * sigma) - ((x - mu) ** 2) / (2 * sigma * sigma)


def update_bayes(
    priors: Sequence[float],
    claims: Sequence[float],
    tested_idx: int,
    observed: float,
    sigma: float,
) -> tuple[float, ...]:
    """Return normalized posteriors after one observation.

    The tested hypothesis predicts its claimed lift; all other hypotheses
    predict zero lift. The observed value is compared against both predictions.
    """
    if len(priors) != len(claims) or not priors:
        raise ValueError("priors and claims must have the same non-zero length")
    if not 0 <= tested_idx < len(priors):
        raise ValueError("tested_idx out of range")
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    if not math.isfinite(observed):
        raise ValueError("observed must be finite")

    log_posteriors: list[float] = []
    for index, (prior, claim) in enumerate(zip(priors, claims, strict=True)):
        if not math.isfinite(prior) or prior <= 0:
            raise ValueError("every prior must be finite and > 0")
        if not math.isfinite(claim):
            raise ValueError("every claim must be finite")
        expected = claim if index == tested_idx else 0.0
        log_likelihood = _log_gaussian(observed, expected, sigma)
        log_posteriors.append(math.log(prior) + log_likelihood)

    maximum = max(log_posteriors)
    if maximum == -math.inf:
        raise ValueError("all posteriors underflowed to zero")

    weights = [math.exp(value - maximum) for value in log_posteriors]
    total = math.fsum(weights)
    if total == 0:
        raise ValueError("posterior normalization failed")
    return tuple(weight / total for weight in weights)


def run_loop(
    question: str,
    n_hypotheses: int = 4,
    rounds: int = 8,
    seed: int = 42,
    sigma: float = 0.08,
    domain: str | None = None,
    convergence_threshold: float = 0.85,
) -> Result:
    """Run a deterministic hypothesis + simulated experiment loop."""
    if rounds < 1:
        raise ValueError("rounds must be >= 1")
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    if not 0 < convergence_threshold <= 1:
        raise ValueError("convergence_threshold must be in (0, 1]")

    hypotheses = generate_hypotheses(question, n=n_hypotheses, domain=domain)
    rng = random.Random(seed)
    true_index = rng.randrange(len(hypotheses))

    priors = tuple(1.0 / len(hypotheses) for _ in hypotheses)
    posteriors = priors
    history: list[Round] = []
    converged = False

    for round_number in range(1, rounds + 1):
        if round_number <= len(hypotheses):
            tested_index = round_number - 1
        else:
            tested_index = max(
                range(len(posteriors)),
                key=lambda index: (posteriors[index], -index),
            )

        before = posteriors
        expected = hypotheses[true_index].claim if tested_index == true_index else 0.0
        observed = rng.gauss(expected, sigma)

        posteriors = update_bayes(
            priors=posteriors,
            claims=tuple(hypothesis.claim for hypothesis in hypotheses),
            tested_idx=tested_index,
            observed=observed,
            sigma=sigma,
        )

        history.append(
            Round(
                round=round_number,
                tested_hypothesis_id=hypotheses[tested_index].id,
                tested_action=hypotheses[tested_index].action,
                observed=observed,
                posteriors_before=before,
                posteriors_after=posteriors,
            )
        )

        if max(posteriors) >= convergence_threshold:
            converged = True
            break

    return Result(
        question=question,
        domain=hypotheses[0].domain,
        hypotheses=hypotheses,
        rounds=tuple(history),
        priors=priors,
        posteriors=posteriors,
        true_hypothesis_id=hypotheses[true_index].id,
        seed=seed,
        converged=converged,
        convergence_threshold=convergence_threshold,
    )


def _escape_table(value: str) -> str:
    return value.replace("|", "\\|")


def render_markdown(result: Result) -> str:
    """Render a human-readable experiment report."""
    best = result.best_hypothesis
    lines = [
        "# AI Scientist Report",
        "",
        f"**Question:** {result.question}",
        f"**Domain:** {result.domain}",
        f"**Seed:** {result.seed}",
        f"**Rounds run:** {len(result.rounds)}",
        f"**Converged:** {'yes' if result.converged else 'no'}",
        f"**Convergence threshold:** {result.convergence_threshold:.0%}",
        f"**Ground truth (simulation only):** H{result.true_hypothesis_id}",
        "",
        "## Hypotheses",
        "",
        "| # | Action | Claimed lift | Prior |",
        "|---|---|---|---|",
    ]

    for hypothesis, prior in zip(result.hypotheses, result.priors, strict=True):
        lines.append(
            f"| H{hypothesis.id} | {_escape_table(hypothesis.action)} | "
            f"{hypothesis.claim:+.0%} | {prior:.3f} |"
        )

    lines.extend(
        [
            "",
            "## Experiment log",
            "",
            "| Round | Tested | Observed | Top posterior |",
            "|---|---|---|---|",
        ]
    )
    for entry in result.rounds:
        top_index = max(
            range(len(entry.posteriors_after)),
            key=lambda index: (entry.posteriors_after[index], -index),
        )
        lines.append(
            f"| {entry.round} | H{entry.tested_hypothesis_id} | "
            f"{entry.observed:+.1%} | H{result.hypotheses[top_index].id} "
            f"({entry.posteriors_after[top_index]:.1%}) |"
        )

    lines.extend(
        [
            "",
            "## Final posteriors",
            "",
            "| # | Action | Posterior |",
            "|---|---|---|",
        ]
    )
    for hypothesis, posterior in zip(result.hypotheses, result.posteriors, strict=True):
        marker = " (recommended)" if hypothesis.id == best.id else ""
        lines.append(
            f"| H{hypothesis.id} | {_escape_table(hypothesis.action)} | {posterior:.1%}{marker} |"
        )

    lines.extend(
        [
            "",
            "## Recommendation",
            "",
            f"Run **H{best.id}: {best.action}**",
            "",
            f"- Confidence: {result.best_posterior:.1%}",
            f"- Expected lift: {best.claim:+.0%}",
            "",
            "## Method",
            "",
            (
                "Each hypothesis predicts either its claimed lift (when tested) or zero "
                "lift (when not tested). Gaussian likelihoods with the configured sigma "
                "update a uniform prior. The loop tests every hypothesis once, then "
                "repeatedly tests the current maximum-a-posteriori hypothesis until it "
                "converges."
            ),
            "",
            (
                "> This is a simulated decision loop. The claims are illustrative priors, "
                "not measured causal effects."
            ),
        ]
    )
    return "\n".join(lines)


def render_json(result: Result) -> dict[str, Any]:
    """Render a machine-readable experiment report."""
    best = result.best_hypothesis
    return {
        "schema_version": "1.0",
        "simulation": True,
        "question": result.question,
        "domain": result.domain,
        "seed": result.seed,
        "converged": result.converged,
        "convergence_threshold": result.convergence_threshold,
        "rounds_run": len(result.rounds),
        "hypotheses": [
            {
                "id": hypothesis.id,
                "action": hypothesis.action,
                "claim": hypothesis.claim,
                "prior": prior,
                "posterior": posterior,
            }
            for hypothesis, prior, posterior in zip(
                result.hypotheses, result.priors, result.posteriors, strict=True
            )
        ],
        "rounds": [
            {
                "round": entry.round,
                "tested_hypothesis_id": entry.tested_hypothesis_id,
                "tested_action": entry.tested_action,
                "observed": entry.observed,
                "posteriors_before": list(entry.posteriors_before),
                "posteriors_after": list(entry.posteriors_after),
            }
            for entry in result.rounds
        ],
        "recommendation": {
            "hypothesis_id": best.id,
            "action": best.action,
            "posterior": result.best_posterior,
            "expected_lift": best.claim,
        },
        "ground_truth": {
            "hypothesis_id": result.true_hypothesis_id,
            "action": result.hypotheses[result.true_hypothesis_id - 1].action,
        },
    }


def _emit(text: str, out_path: Path | None) -> None:
    if out_path is None:
        print(text)
        return

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text + "\n", encoding="utf-8")
    print(f"Wrote {out_path}", file=sys.stderr)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai_scientist",
        description=(
            "Generate hypotheses, run a simulated experiment loop, and recommend an action."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python ai_scientist.py run "How can we improve checkout conversion?"\n'
            '  python ai_scientist.py run "How do we reduce churn?" --format json\n'
            '  python ai_scientist.py run "How do we cut latency?" --rounds 6 --seed 7'
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    commands = parser.add_subparsers(dest="command", required=True)

    commands.add_parser("domains", help="list supported domains")

    run_cmd = commands.add_parser("run", help="run a hypothesis and experiment loop")
    run_cmd.add_argument("question", nargs="+", help="research question")
    run_cmd.add_argument("--n", type=int, default=4, metavar="N", help="number of hypotheses")
    run_cmd.add_argument("--rounds", type=int, default=8, metavar="N", help="maximum rounds")
    run_cmd.add_argument("--seed", type=int, default=42, help="random seed")
    run_cmd.add_argument("--sigma", type=float, default=0.08, help="observation noise")
    run_cmd.add_argument(
        "--domain",
        choices=tuple(DOMAINS),
        default=None,
        help="force a domain instead of inferring it",
    )
    run_cmd.add_argument(
        "--threshold",
        type=float,
        default=0.85,
        metavar="P",
        help="convergence threshold in (0, 1]",
    )
    run_cmd.add_argument(
        "--format",
        "-f",
        choices=("markdown", "json"),
        default="markdown",
        help="output format",
    )
    run_cmd.add_argument("--out", type=Path, metavar="PATH", help="write output to a file")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "domains":
        width = max(len(domain) for domain in DOMAINS)
        for domain, templates in DOMAINS.items():
            print(f"{domain:<{width}}  {len(templates)} templates")
        return 0

    question = " ".join(args.question).strip()
    if not question:
        parser.error("question must not be empty")

    try:
        result = run_loop(
            question=question,
            n_hypotheses=args.n,
            rounds=args.rounds,
            seed=args.seed,
            sigma=args.sigma,
            domain=args.domain,
            convergence_threshold=args.threshold,
        )
    except (ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        output = json.dumps(render_json(result), ensure_ascii=False, indent=2)
    else:
        output = render_markdown(result)

    _emit(output, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
