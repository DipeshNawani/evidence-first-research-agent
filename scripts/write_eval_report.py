"""Render the evaluation narrative from the executed results, never invented metrics."""

import json
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]


def live_report() -> str:
    """Keep live evidence separate and regenerate its actual denominators."""
    path = ROOT / "eval/results/live/results.json"
    if not path.exists():
        return """## Live provider evidence

Executed NVIDIA integration records are preserved under [the initial smoke check](eval/results/nvidia-smoke/REPORT.md) and [the follow-up checks](eval/results/approved-upgrade/REPORT.md). They include successful and partial runs. Full agent-versus-baseline metrics will be reported here only after the live harness writes its result file.
"""
    data = json.loads(path.read_text(encoding="utf-8"))
    if data["mode"] != "live":
        raise ValueError("Live report requires explicitly live results")
    agent = [row for row in data["rows"] if row["system"] == "agent"]
    baseline = [row for row in data["rows"] if row["system"] == "baseline"]
    substantive = [row for row in agent if row["metrics"]["source_count"] > 0]
    providers: dict[str, int] = {}
    for trace_path in sorted((path.parent / "traces").glob("*.jsonl")):
        for line in trace_path.read_text(encoding="utf-8").splitlines():
            event = json.loads(line)
            fields = event.get("data", {})
            provider = fields.get("search_provider")
            if event["event"] == "tool_end" and fields.get("ok") and provider:
                providers[provider] = providers.get(provider, 0) + 1
    provider_text = (
        ", ".join(
            f"{name}: {count} successful search calls" for name, count in sorted(providers.items())
        )
        or "Successful provider names were not recorded in the available snapshots."
    )
    models = sorted({model for row in data["rows"] for model in row["answer"]["meta"]["models"]})
    failures = [
        f"- **{row['case']['id']} / {row['system']}**: "
        + ", ".join(name for name, passed in row["metrics"]["checks"].items() if not passed)
        + "."
        for row in data["rows"]
        if not row["metrics"]["behavior_pass"]
    ]
    grounding = mean(row["metrics"]["grounding_rate"] for row in substantive) if substantive else 0
    verified = (
        mean(row["metrics"]["verified_claim_fraction"] for row in substantive) if substantive else 0
    )
    return f"""## Executed live evaluation

Executed at **{data["executed_at"]}**, separately from the authored mock evaluation. Sources: [raw live outputs](eval/results/live/results.json), [per-query summary](eval/results/live/summary.md), and [redacted trace snapshots](eval/results/live/traces/).

- Evaluated **{len(agent)} normal-scenario queries** against both systems, producing **{len(data["rows"])} outputs**. Deterministic clarification/refusal cases are included in that denominator; synthetic fault scenarios are skipped: {", ".join(data["skipped_fixture_cases"])}.
- Schema-valid final outputs: **{sum(row["metrics"]["schema_valid"] for row in data["rows"])}/{len(data["rows"])}**. This includes application recovery, not just raw model compliance.
- Agent behavior checks: **{sum(row["metrics"]["behavior_pass"] for row in agent)}/{len(agent)}**; no-tool baseline: **{sum(row["metrics"]["behavior_pass"] for row in baseline)}/{len(baseline)}**.
- Agent answers with cited findings: **{len(substantive)}/{len(agent)}**. Mean pre-removal quotation grounding on those answers: **{grounding:.1%}**; mean retained verified-claim fraction: **{verified:.1%}**.
- Partial agent runs: **{sum(row["answer"]["meta"]["partial"] for row in agent)}/{len(agent)}**. Mean recorded agent latency across all cases: **{mean(row["metrics"]["latency_s"] for row in agent):.2f} s**; baseline: **{mean(row["metrics"]["latency_s"] for row in baseline):.2f} s**. Preflight exits make these averages smaller than a substantive research request.
- Reported tokens: agent **{sum(row["metrics"]["tokens"] for row in agent):,}**, baseline **{sum(row["metrics"]["tokens"] for row in baseline):,}**. Timed-out calls may consume unreported tokens; these totals cover responses whose usage was returned.
- Model IDs returned: {", ".join(f"`{model}`" for model in models)}.
- Explicit search-provider evidence from successful tool events: **{provider_text}**.
- Model cost remains unknown where rates are not configured; search and infrastructure costs are not measured. No zero-cost inference claim is made.

### Live failed checks

{chr(10).join(failures) if failures else "No machine behavior checks failed in this run."}

### Live interpretation and human review

The no-tool baseline cannot supply verified external citations by design. Behavior checks are narrow contracts, not accuracy scores. Quote matches do not establish semantic entailment, independence or factual correctness; the model judge is not ground truth. Review [the live assessment](eval/results/live/REVIEW.md) for per-case expected behavior, observed findings, missing criteria and output limitations. Historical integration failures remain under the earlier NVIDIA reports rather than being replaced by this run.

### Reproduce the live harness

Windows PowerShell:

```powershell
.\\.venv\\Scripts\\python.exe eval/run_eval.py --live
.\\.venv\\Scripts\\python.exe scripts/write_eval_report.py
```

macOS / Linux:

```bash
.venv/bin/python eval/run_eval.py --live
.venv/bin/python scripts/write_eval_report.py
```

Configure the selected provider locally before running. New runs overwrite the live harness outputs, so preserve evidence needed for a submission first.
"""


def write_report() -> None:
    results = json.loads((ROOT / "eval/results/mock/results.json").read_text(encoding="utf-8"))
    groups = {
        name: [r for r in results["rows"] if r["system"] == name] for name in ["agent", "baseline"]
    }
    agent, baseline = groups["agent"], groups["baseline"]
    substantive = [row for row in agent if row["metrics"]["source_count"] > 0]
    case_count = len(agent)
    agent_pass = sum(row["metrics"]["behavior_pass"] for row in agent)
    baseline_pass = sum(row["metrics"]["behavior_pass"] for row in baseline)
    valid = sum(row["metrics"]["schema_valid"] for row in results["rows"])
    failures = [
        f"- **{row['case']['id']}**: "
        + ", ".join(key for key, passed in row["metrics"]["checks"].items() if not passed)
        + "."
        for row in agent
        if not row["metrics"]["behavior_pass"]
    ]
    report = f"""# Evaluation: offline fixtures and live provider runs

The offline evaluation was executed at **{results["executed_at"]}**. Its metrics below come from `eval/results/mock/results.json`; the separate **Executed live evaluation** section uses the live result files and traces. Per-case metrics and full validated answers are committed. The two modes are not combined into an accuracy score.

## Method and denominators

The harness executes {case_count} queries against both the agent and a one-call no-tool baseline ({len(results["rows"])} outputs). Each case starts with fresh cache/circuit state. Mock retries use zero backoff for reproducibility; real timeout/cancellation tests use actual short sleeps separately. Fault providers follow the same retry/fallback/executor paths as live providers. The baseline shares the deterministic preflight and makes one model invocation only when preflight allows it; there are no baseline judge or retrieval calls.

Machine checks in `must_have` are implemented in `behavior_checks`. The YAML `failure_criteria` additionally guides human review; it is not a claim that all semantic failure modes are automatically detectable. Schema validity measures the **final application contract**, including recovery paths, rather than the raw model's JSON compliance. Raw validation errors and repairs have their own trace events and metrics. No-findings cases get a grounding rate of zero, rather than a misleading vacuous 100%.

The mock is deliberately extractive: it copies the first sentence of each retained fixture. Its judge returns 0.82 for ordinary answers. These fixed values test orchestration, **not** research quality, semantic faithfulness or model judgment. Fixture URLs include real vendor URLs and explicitly synthetic example references; the corpus is authored text and is never fetched in mock mode. Provenance is `fixture`, and mock confidence cannot exceed 0.5.

## Observed results

- Structured final-output validity: **{valid}/{len(results["rows"])}**.
- Agent behavior checks: **{agent_pass}/{case_count}**; baseline: **{baseline_pass}/{case_count}**. These are task/contract checks, not an accuracy score.
- Agent answers with cited findings: **{len(substantive)}/{case_count}**. Mean pre-removal grounding rate on that subset: **{mean(row["metrics"]["grounding_rate"] for row in substantive):.0%}**. Mean retained verified-claim fraction: **{mean(row["metrics"]["verified_claim_fraction"] for row in substantive):.0%}**.
- Mean source count across **all** agent cases: **{mean(row["metrics"]["source_count"] for row in agent):.2f}**. Mean of per-answer source quality over cited answers: **{mean(row["metrics"]["avg_source_quality"] for row in substantive):.3f}** (heuristic, not an external rating).
- Mean recorded agent run latency: **{mean(row["metrics"]["latency_s"] for row in agent):.4f} seconds**; baseline **{mean(row["metrics"]["latency_s"] for row in baseline):.4f} seconds**. This excludes dependency construction/process startup and has no predictive value for live network/model latency.
- Total synthetic reported tokens: agent **{sum(row["metrics"]["tokens"] for row in agent)}**, baseline **{sum(row["metrics"]["tokens"] for row in baseline)}**. Mock token counts use character estimates; they are not provider usage.
- Estimated model spend in this offline run: **$0**. Live estimates are unknown unless configured input/output rates are supplied; search and infrastructure billing are excluded.

For every query's expected behavior, source count, grounding, judge value, latency, tokens and observed checks, see [the generated results table](eval/results/mock/summary.md). Tool failure and recovery metrics, every answer and failed-check details are in [the machine-readable results](eval/results/mock/results.json).

## What worked

The vector-database case returned three separately cited observations and a comparison structure. The Indian HR SaaS fixture case returned five sourced positioning observations; company freshness and incorporation are explicitly unverified. This tests item count and provenance, not the real-world accuracy of the company list.

The ambiguous question was handled before any model/tool spend. The unknowable future funding question abstained. SEO affiliate material was excluded; the injected source generated a security event and was not cited. The timeout fixture recovered through an independent provider. With every provider down, the agent returned no findings or sources. Denied page fetches degraded to snippets and disclosed that limitation. Unsafe credential-theft research was refused without tools.

## What did not work

{chr(10).join(failures)}

Both failures have matching quotations and a fixed mock judge score of 0.82. The first-sentence mock omits concrete negative tradeoffs from later source sentences. This is a useful failure: quotation matching does not measure completeness or balanced reasoning. The harness does not hide these rows or relabel them as success. The unit suite checks that this quality probe remains detectable.

Earlier exploratory evaluation also exposed a vague-question preflight miss and an empty-provider fallback that could return an unrelated populated fixture. Those implementation defects were fixed and covered by regression tests before this recorded run. The remaining failed quality checks concern the intentionally limited mock, not a measured live-model performance result.

## Agent versus baseline: interpretation

The agent pays for planning, source retrieval, synthesis and optional judging. The baseline is one call with no supplied evidence and consequently cannot have verified citations; its zero citation scores are expected **by design**, not evidence that all no-tool models are inaccurate. It passes abstention/preflight cases and fails source-requiring task checks. The comparison shows the benefit and cost of evidence infrastructure. A fair semantic-quality comparison still needs blind human review, real model outputs and a separate retrieval-plus-single-synthesis baseline to isolate planning's added value.

## Fault and boundary tests beyond these queries

The offline pytest suite exercises actual cancellation, exponential retry classification for HTTP 400/403/429/500, circuit opening, malformed JSON and wrong tool shapes, empty output, garbage HTML, oversized responses, private-IP redirects, mixed DNS responses, quote fabrication, unknown source IDs, deduplication, injection detection/quarantine, cache expiry, bounded tool concurrency, token/call/page/time limits, validation repair/default planning, one revision, judge failure, CLI JSON and API/traces. These tests do not establish exhaustive security coverage.

## Next improvements

1. Repeat the four live research examples across runs and add a blind human rubric for balance, factual correctness, usefulness and missing criteria.
2. Replace or supplement the extractive mock with hand-authored expected-output variants for judge/revision tests; keep authored fixtures clearly separated from research results.
3. Add cell-level evidence to richer comparison matrices and evaluate entailment rather than quotation presence alone.
4. Expand ambiguous/unsafe/future-intent coverage beyond the deliberately small preflight rules; test contradictions and subtle injection attempts.
5. Calibrate confidence and source heuristics with labeled data, audit domain independence and add real publication dates.
6. Compare single-call, retrieval-only synthesis, and planned retrieval on the same evidence/task set; evaluate repeated runs and variance.

{live_report()}

"""
    (ROOT / "EVALUATION.md").write_text(report.rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    write_report()
