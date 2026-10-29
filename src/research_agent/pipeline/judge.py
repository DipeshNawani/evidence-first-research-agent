from research_agent import prompts
from research_agent.llm.gateway import Gateway
from research_agent.pipeline.synthesizer import evidence_payload
from research_agent.schemas import AnswerDraft, Evidence, JudgeScore, Plan


async def judge(
    answer: AnswerDraft, plan: Plan, evidence: list[Evidence], gateway: Gateway
) -> JudgeScore | None:
    try:
        return await gateway.call(
            "judge",
            prompts.JUDGE,
            {
                "answer": answer.model_dump(mode="json"),
                "success_criteria": plan.success_criteria,
                "evidence": evidence_payload(evidence),
            },
            JudgeScore,
        )
    except Exception as exc:
        gateway.trace.emit("judge_unavailable", "judge", error_type=type(exc).__name__)
        return None
