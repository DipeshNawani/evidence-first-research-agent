from research_agent import prompts
from research_agent.llm.gateway import Gateway
from research_agent.pipeline.context import pack_context
from research_agent.schemas import AnswerDraft, Evidence, JudgeScore, Plan


async def judge(
    answer: AnswerDraft, plan: Plan, evidence: list[Evidence], gateway: Gateway
) -> JudgeScore | None:
    try:
        cited = {source_id for finding in answer.key_findings for source_id in finding.source_ids}
        selected = [item for item in evidence if item.source.id in cited]
        payload, _ = pack_context(
            selected,
            gateway,
            "judge",
            prompts.JUDGE,
            {
                "answer": answer.model_dump(mode="json"),
                "success_criteria": plan.success_criteria,
                "finding_indices": list(range(len(answer.key_findings))),
            },
            JudgeScore,
        )
        result = await gateway.call("judge", prompts.JUDGE, payload, JudgeScore)
        gateway.trace.emit("judge_result", "judge", score=result.score, **result.model_dump())
        return result
    except Exception as exc:
        gateway.trace.emit("judge_unavailable", "judge", error_type=type(exc).__name__)
        return None
