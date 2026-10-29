"""Reproducible contract evaluation, not a substitute for blind human judging.

Run --mock for all fault fixtures; --live runs normal queries only and never mixes
authored fixtures into live results. Each case receives a fresh cache/circuit state.
"""

import argparse
import asyncio
import json
from pathlib import Path
from statistics import mean
from typing import Any

import yaml

from research_agent.baseline import run_baseline
from research_agent.config import Settings
from research_agent.renderer import render_markdown
from research_agent.runtime import build_agent
from research_agent.schemas import EvalCase, FinalAnswer, Schema, TraceEvent, utcnow
from research_agent.tracing import read_trace

ROOT = Path(__file__).resolve().parents[1]


class Metrics(Schema):
    schema_valid: bool
    grounding_rate: float
    source_count: int
    avg_source_quality: float
    verified_claim_fraction: float
    judge_score: float | None
    latency_s: float
    tokens: int
    est_cost_usd: float | None
    tool_calls: int
    tool_failure_rate: float
    recoveries: int
    validation_errors: int
    checks: dict[str, bool]
    behavior_pass: bool


class EvalRow(Schema):
    case: EvalCase
    system: str
    metrics: Metrics
    answer: FinalAnswer


def behavior_checks(
    case: EvalCase, answer: FinalAnswer, events: list[TraceEvent]
) -> dict[str, bool]:
    claims = " ".join(f.claim.lower() for f in answer.key_findings)
    limitations = " ".join(answer.limitations).lower()
    catalog = {
        "three_sources": len(answer.sources) >= 3,
        "five_sources": len(answer.sources) >= 5,
        "verified_findings": bool(answer.key_findings)
        and all(f.verified for f in answer.key_findings),
        "comparison": bool(answer.comparison_table and answer.comparison_table.rows),
        "limitations": bool(answer.limitations),
        "concrete_downside": any(
            word in claims for word in ["latency", "cost", "omit", "stale", "complexity", "failure"]
        ),
        "clarification": answer.meta.status == "needs_clarification",
        "no_tools": answer.meta.tool_calls == 0,
        "abstention": answer.meta.status == "insufficient_evidence",
        "low_confidence": answer.confidence.level == "low",
        "no_findings": not answer.key_findings and not answer.sources,
        "spam_dropped": any(
            e.event == "dropped_source" and "best-tools" in str(e.data.get("url")) for e in events
        )
        and not any("best-tools" in s.url for s in answer.sources),
        "injection_quarantined": any(e.event == "security_event" for e in events)
        and not any("injection" in s.url for s in answer.sources),
        "fallback_recorded": any(e.event == "provider_fallback" for e in events),
        "refused": answer.meta.status == "refused",
        "snippet_limitation": "snippets" in limitations,
    }
    return {criterion: catalog[criterion] for criterion in case.must_have}


def measure(case: EvalCase, answer: FinalAnswer, events: list[TraceEvent]) -> Metrics:
    checks = behavior_checks(case, answer, events)
    return Metrics(
        schema_valid=FinalAnswer.model_validate_json(answer.model_dump_json()) == answer,
        grounding_rate=answer.meta.grounding_rate,
        source_count=len(answer.sources),
        avg_source_quality=mean(s.quality_score for s in answer.sources) if answer.sources else 0,
        verified_claim_fraction=sum(f.verified for f in answer.key_findings)
        / len(answer.key_findings)
        if answer.key_findings
        else 0,
        judge_score=answer.meta.judge_score,
        latency_s=answer.meta.latency_s,
        tokens=answer.meta.tokens,
        est_cost_usd=answer.meta.est_cost_usd,
        tool_calls=answer.meta.tool_calls,
        tool_failure_rate=answer.meta.tool_failure_rate,
        recoveries=sum(e.event == "provider_fallback" for e in events),
        validation_errors=sum(e.event == "validation_error" for e in events),
        checks=checks,
        behavior_pass=all(checks.values()),
    )


def markdown(rows: list[EvalRow], mode: str) -> str:
    lines = [
        f"# Evaluation results - {mode.upper()} RUN",
        "",
        "Measured contract checks, not a research-quality benchmark. Mock judge scores are fixed fixture values. Zero citation metrics for the no-tool baseline follow from having no supplied evidence. No-findings cases have grounding 0, not vacuous 100%.",
        "",
        "| Query | System | Checks | Sources | Grounding | Judge | Latency (s) | Tokens | Model cost (USD) |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        m = row.metrics
        cost = "unknown" if m.est_cost_usd is None else f"{m.est_cost_usd:.6f}"
        judge_value = "n/a" if m.judge_score is None else f"{m.judge_score:.2f}"
        lines.append(
            f"| {row.case.id} | {row.system} | {'PASS' if m.behavior_pass else 'FAIL'} | {m.source_count} | {m.grounding_rate:.0%} | {judge_value} | {m.latency_s:.4f} | {m.tokens} | {cost} |"
        )
    lines += ["", "## Observed failed checks", ""]
    for row in rows:
        failed = [key for key, passed in row.metrics.checks.items() if not passed]
        if failed:
            lines.append(f"- {row.case.id} / {row.system}: {', '.join(failed)}")
    return "\n".join(lines) + "\n"


async def evaluate(mock: bool, output_dir: Path) -> list[EvalRow]:
    settings = Settings()
    if mock:
        settings.llm_provider = "mock"
        settings.retry_base_seconds = 0
    elif settings.llm_provider == "mock":
        raise ValueError("--live requires RA_LLM_PROVIDER=openai or anthropic")
    cases = [
        EvalCase.model_validate(case)
        for case in yaml.safe_load((ROOT / "eval/queries.yaml").read_text(encoding="utf-8"))
    ]
    rows: list[EvalRow] = []
    skipped = []
    for case in cases:
        if not mock and case.scenario != "normal":
            skipped.append(case.id)
            continue
        async with build_agent(settings, case.scenario) as agent:
            answer = await agent.research(case.question)
            baseline = await run_baseline(case.question, agent.llm, settings)
        for system, result in [("agent", answer), ("baseline", baseline)]:
            events = read_trace(settings.trace_dir, result.meta.trace_id)
            rows.append(
                EvalRow(
                    case=case, system=system, metrics=measure(case, result, events), answer=result
                )
            )
        print(
            f"{case.id}: agent checks {'PASS' if rows[-2].metrics.behavior_pass else 'FAIL'}",
            flush=True,
        )
    await asyncio.to_thread(output_dir.mkdir, parents=True, exist_ok=True)
    data: dict[str, Any] = {
        "mode": "mock" if mock else "live",
        "executed_at": utcnow().isoformat(),
        "skipped_fixture_cases": skipped,
        "rows": [row.model_dump(mode="json") for row in rows],
    }
    (output_dir / "results.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
    (output_dir / "summary.md").write_text(markdown(rows, data["mode"]), encoding="utf-8")
    # Samples and their redacted traces are generated only from executed mock runs.
    if mock:
        samples = ROOT / "samples"
        await asyncio.to_thread(samples.mkdir, exist_ok=True)
        for name, case_id in [
            ("vector", "vector_comparison"),
            ("hr_saas", "indian_hr_saas"),
            ("failure", "all_providers_down"),
        ]:
            answer = next(
                row.answer for row in rows if row.case.id == case_id and row.system == "agent"
            )
            (samples / f"{name}.json").write_text(
                answer.model_dump_json(indent=2), encoding="utf-8"
            )
            (samples / f"{name}.md").write_text(render_markdown(answer), encoding="utf-8")
            (samples / f"{name}.trace.jsonl").write_text(
                "\n".join(
                    event.model_dump_json()
                    for event in read_trace(settings.trace_dir, answer.meta.trace_id)
                )
                + "\n",
                encoding="utf-8",
            )
    return rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--mock", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    destination = args.output_dir or ROOT / "eval/results" / ("mock" if args.mock else "live")
    asyncio.run(evaluate(args.mock, destination))
