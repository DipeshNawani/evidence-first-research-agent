"""Stable Markdown output. External text is escaped before entering tables."""

import re

from research_agent.schemas import FinalAnswer


def safe(text: str) -> str:
    text = text.replace("\n", " ").replace("|", "\\|")
    return re.sub(r"([<>\[\]`])", r"\\\1", text)


def render_markdown(answer: FinalAnswer) -> str:
    mode = (
        "MOCK RUN - authored fixtures, not live research"
        if answer.meta.mode == "mock"
        else "LIVE RESEARCH"
    )
    lines = [
        f"# {safe(answer.user_question)}",
        "",
        f"**{mode}**",
        "",
        answer.short_answer,
        "",
        f"**Confidence:** {answer.confidence.level} ({answer.confidence.score:.2f}; heuristic, not probability)",
        "",
        "## Key findings",
        "",
    ]
    lines.extend(
        f"- {safe(f.claim)} [{', '.join(f.source_ids)}; {'verified quote' if f.verified else 'unverified'}]\n  > {safe(f.supporting_quote)}"
        for f in answer.key_findings
    )
    if answer.comparison_table:
        table = answer.comparison_table
        lines += [
            "",
            "## Comparison",
            "",
            "| Item | " + " | ".join(safe(c) for c in table.columns) + " | Sources |",
            "| --- | " + " | ".join("---" for _ in table.columns) + " | --- |",
        ]
        lines += [
            "| "
            + safe(row.item)
            + " | "
            + " | ".join(safe(c) for c in row.cells)
            + " | "
            + ", ".join(row.source_ids)
            + " |"
            for row in table.rows
        ]
    lines += ["", "## Sources", ""]
    lines += [
        f"- [{s.id}] [{safe(s.title)}]({s.url}) - quality {s.quality_score:.2f}; {s.provenance}; retrieved {s.retrieved_at.isoformat()}"
        for s in answer.sources
    ]
    for title, items in [
        ("Assumptions", answer.assumptions),
        ("Limitations", answer.limitations),
        ("Suggested next steps", answer.suggested_next_steps),
    ]:
        lines += ["", f"## {title}", ""] + [f"- {safe(item)}" for item in items]
    cost = (
        "unknown (rates not configured)"
        if answer.meta.est_cost_usd is None
        else f"${answer.meta.est_cost_usd:.6f}"
    )
    lines += [
        "",
        "## Run summary",
        "",
        f"Trace `{answer.meta.trace_id}` · {answer.meta.latency_s:.3f}s · {answer.meta.tool_calls} tool attempts · {answer.meta.tokens} reported tokens · estimated model cost {cost} · partial: {answer.meta.partial}",
        "",
        "Stage latency: "
        + ", ".join(
            f"{stage} {elapsed:.3f}s" for stage, elapsed in answer.meta.stage_latency_s.items()
        ),
        "",
    ]
    return "\n".join(lines)
