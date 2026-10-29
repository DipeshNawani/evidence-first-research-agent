"""Single structured model call, deliberately without tools or judge calls."""

import time

from research_agent import prompts
from research_agent.budget import Budget
from research_agent.config import Settings
from research_agent.llm.base import LLMClient
from research_agent.llm.gateway import Gateway
from research_agent.pipeline.planner import early_exit
from research_agent.resilience import Resilience
from research_agent.schemas import AnswerDraft, AnswerMeta, AnswerStatus, FinalAnswer
from research_agent.tracing import Trace


async def run_baseline(question: str, llm: LLMClient, settings: Settings) -> FinalAnswer:
    trace = Trace(settings.trace_dir, mode=settings.llm_provider)
    budget = Budget(settings)
    # No repair or transport retry: comparison really is one model invocation.
    baseline_settings = settings.model_copy(update={"retries": 0, "repair_retries": 0})
    gateway = Gateway(llm, baseline_settings, budget, trace, Resilience(baseline_settings))
    status: AnswerStatus = "insufficient_evidence"
    exit_reason = early_exit(question)
    if exit_reason:
        status, message = exit_reason
        draft = AnswerDraft(short_answer=message, key_findings=[])
    else:
        try:
            draft = await gateway.call(
                "baseline", prompts.BASELINE, {"question": question}, AnswerDraft
            )
        except Exception:
            draft = AnswerDraft(short_answer="Baseline model call unavailable.", key_findings=[])
    # No supplied evidence: no finding can claim to have a verified citation.
    draft.key_findings = []
    draft.comparison_table = None
    draft.limitations.append(
        "Non-agentic baseline: one call, no retrieved evidence; citation metrics are zero by construction."
    )
    meta = AnswerMeta(
        trace_id=trace.id,
        mode="mock" if settings.llm_provider == "mock" else "live",
        latency_s=round(time.monotonic() - budget.started, 4),
        tokens=budget.tokens,
        token_upper_bound_reserved=budget.reserved_tokens,
        est_cost_usd=budget.cost,
        models=sorted(budget.models),
        status=status,
    )
    trace.emit("run_end", "baseline", **meta.model_dump())
    return FinalAnswer(**draft.model_dump(), user_question=question, meta=meta)
