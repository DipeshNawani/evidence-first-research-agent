from research_agent import prompts
from research_agent.llm.gateway import Gateway
from research_agent.safety.injection import untrusted_payload
from research_agent.schemas import AnswerDraft, Evidence, Plan


def evidence_payload(evidence: list[Evidence]) -> list[dict]:
    return [
        {"source": e.source.model_dump(mode="json"), "text": untrusted_payload(e.text)}
        for e in evidence
    ]


async def synthesize(
    question: str,
    plan: Plan,
    evidence: list[Evidence],
    gateway: Gateway,
    feedback: list[str] | None = None,
) -> AnswerDraft:
    return await gateway.call(
        "synthesize",
        prompts.SYNTHESIZE,
        {
            "question": question,
            "question_type": plan.question_type,
            "success_criteria": plan.success_criteria,
            "evidence": evidence_payload(evidence),
            "feedback": feedback or [],
        },
        AnswerDraft,
    )


def extractive_fallback(evidence: list[Evidence]) -> AnswerDraft:
    # If synthesis fails, do not manufacture an apparently model-written answer.
    return AnswerDraft(
        short_answer="Could not synthesize a validated answer from the collected evidence.",
        key_findings=[],
        limitations=["Synthesis was unavailable or output failed schema validation."],
        suggested_next_steps=["Inspect the sources and retry with a working model provider."],
    )
