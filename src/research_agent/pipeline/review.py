"""Synthesize, verify and judge, with at most one bounded revision."""

from research_agent.config import Settings
from research_agent.llm.gateway import Gateway
from research_agent.pipeline.judge import judge
from research_agent.pipeline.synthesizer import extractive_fallback, synthesize
from research_agent.pipeline.verifier import verify
from research_agent.schemas import (
    AnswerDraft,
    ComparisonTable,
    Evidence,
    JudgeScore,
    Plan,
    ReviewResult,
)
from research_agent.tracing import Trace


def remove_judge_flagged_claims(
    answer: AnswerDraft, evidence: list[Evidence], judgment: JudgeScore | None, trace: Trace
) -> AnswerDraft:
    if judgment is None:
        return answer
    unsupported = {
        index for index in judgment.unsupported_finding_indices if index < len(answer.key_findings)
    }
    if not unsupported:
        return answer
    revised = answer.model_copy(deep=True)
    revised.key_findings = [
        finding for index, finding in enumerate(answer.key_findings) if index not in unsupported
    ]
    revised, _, _ = verify(revised, evidence)
    revised.limitations.append(
        f"The model judge flagged and removed {len(unsupported)} claim(s) not adequately supported by their cited evidence."
    )
    trace.emit(
        "judge_claims_removed",
        "judge",
        finding_indices=sorted(unsupported),
        retained_findings=len(revised.key_findings),
    )
    return revised


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
        if plan.question_type == "comparison" and draft.comparison_table is None:
            draft.comparison_table = ComparisonTable(columns=["Supported observation"], rows=[])
        draft, rate, rejected = verify(draft, evidence)
        trace.emit("citation_verification", "verify", grounding_rate=rate, removed=len(rejected))
    result = ReviewResult(draft=draft, grounding_rate=rate)
    citation_repair_used = False
    if rejected and not draft.key_findings and not gateway.budget.partial:
        with trace.stage("citation_repair"):
            citation_repair_used = True
            try:
                repaired = await synthesize(
                    question,
                    plan,
                    evidence,
                    gateway,
                    [
                        "Every previous citation failed. Copy each supporting_quote and exactly one source_id literally from the same citation_options entry. Make claims only supported by that quote."
                    ],
                    budget_fraction=1.0,
                )
                repaired, repaired_rate, repaired_rejected = verify(repaired, evidence)
                if repaired.key_findings:
                    draft, rate = repaired, repaired_rate
                    result = ReviewResult(draft=draft, grounding_rate=rate)
                trace.emit(
                    "citation_verification",
                    "citation_repair",
                    grounding_rate=repaired_rate,
                    removed=len(repaired_rejected),
                )
            except Exception as exc:
                trace.emit(
                    "citation_repair_failed", "citation_repair", error_type=type(exc).__name__
                )
    if not settings.judge_enabled or not draft.key_findings:
        return result
    with trace.stage("judge"):
        result.judgment = await judge(draft, plan, evidence, gateway)
        result.draft = remove_judge_flagged_claims(draft, evidence, result.judgment, trace)
    if (
        result.judgment is None
        or result.judgment.score >= settings.judge_threshold
        or gateway.budget.partial
        or citation_repair_used
    ):
        return result
    if (
        settings.max_total_tokens - gateway.budget.reserved_tokens
        < settings.llm_output_tokens + settings.judge_output_tokens + 3000
    ):
        trace.emit("revision_skipped", "revision", reason="insufficient_token_headroom")
        return result
    if gateway.budget.remaining() < 2 * settings.llm_timeout_seconds:
        trace.emit(
            "revision_skipped", "revision", reason="insufficient_time_for_revision_and_judge"
        )
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
                    draft=remove_judge_flagged_claims(revised, evidence, revised_judge, trace),
                    grounding_rate=revised_rate,
                    judgment=revised_judge,
                )
            trace.emit("revision", "revision", accepted=accepted)
        except Exception as exc:
            trace.emit("revision_failed", "revision", error_type=type(exc).__name__)
    return result
