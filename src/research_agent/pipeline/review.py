"""Synthesize, verify and judge, with at most one bounded revision."""

from research_agent.config import Settings
from research_agent.llm.gateway import Gateway
from research_agent.pipeline.judge import judge
from research_agent.pipeline.synthesizer import extractive_fallback, synthesize
from research_agent.pipeline.verifier import verify
from research_agent.schemas import Evidence, Plan, ReviewResult


async def review(
    question: str, plan: Plan, evidence: list[Evidence], gateway: Gateway, settings: Settings
) -> ReviewResult:
    trace = gateway.trace
    with trace.stage("synthesize"):
        try:
            draft = await synthesize(question, plan, evidence, gateway)
        except Exception as exc:
            trace.emit("synthesis_fallback", "synthesize", error_type=type(exc).__name__)
            draft = extractive_fallback(evidence)
    with trace.stage("verify"):
        draft, rate, rejected = verify(draft, evidence)
        trace.emit("citation_verification", "verify", grounding_rate=rate, removed=len(rejected))
    result = ReviewResult(draft=draft, grounding_rate=rate)
    if not settings.judge_enabled or not draft.key_findings:
        return result
    with trace.stage("judge"):
        result.judgment = await judge(draft, plan, evidence, gateway)
    if (
        result.judgment is None
        or result.judgment.score >= settings.judge_threshold
        or gateway.budget.partial
    ):
        return result
    with trace.stage("revision"):
        try:
            revised = await synthesize(question, plan, evidence, gateway, result.judgment.issues)
            revised, revised_rate, _ = verify(revised, evidence)
            revised_judge = await judge(revised, plan, evidence, gateway)
            accepted = (
                revised_judge is not None
                and revised_judge.score >= result.judgment.score
                and revised_rate >= rate
            )
            if accepted:
                result = ReviewResult(
                    draft=revised, grounding_rate=revised_rate, judgment=revised_judge
                )
            trace.emit("revision", "revision", accepted=accepted)
        except Exception as exc:
            trace.emit("revision_failed", "revision", error_type=type(exc).__name__)
    return result
