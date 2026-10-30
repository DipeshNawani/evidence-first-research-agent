from research_agent import prompts
from research_agent.llm.gateway import Gateway
from research_agent.pipeline.context import citation_options, pack_context
from research_agent.schemas import AnswerDraft, Evidence, Plan


async def synthesize(
    question: str,
    plan: Plan,
    evidence: list[Evidence],
    gateway: Gateway,
    feedback: list[str] | None = None,
    budget_fraction: float | None = None,
) -> AnswerDraft:
    payload, shortened = pack_context(
        evidence,
        gateway,
        "synthesize",
        prompts.SYNTHESIZE,
        {
            "question": question,
            "question_type": plan.question_type,
            "success_criteria": plan.success_criteria,
            "feedback": feedback or [],
            "citation_options": citation_options(question, evidence),
        },
        AnswerDraft,
        fraction=budget_fraction
        if budget_fraction is not None
        else (0.65 if gateway.settings.judge_enabled else 1.0),
    )
    answer = await gateway.call("synthesize", prompts.SYNTHESIZE, payload, AnswerDraft)
    if shortened:
        answer.limitations.append(
            "Evidence context was shortened to fit the model token budget; some source detail was omitted."
        )
    return answer


def extractive_fallback(evidence: list[Evidence]) -> AnswerDraft:
    # If synthesis fails, do not manufacture an apparently model-written answer.
    return AnswerDraft(
        short_answer="Could not synthesize a validated answer from the collected evidence.",
        key_findings=[],
        limitations=["Synthesis was unavailable or output failed schema validation."],
        suggested_next_steps=["Inspect the sources and retry with a working model provider."],
    )
