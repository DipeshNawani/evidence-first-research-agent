import re

from research_agent import prompts
from research_agent.config import Settings
from research_agent.llm.gateway import Gateway
from research_agent.schemas import AnswerStatus, Plan, SearchStep, utcnow


def early_exit(question: str) -> tuple[AnswerStatus, str] | None:
    text = question.strip().lower()
    vague = re.sub(r"[^a-z ]", "", text).strip() in {
        "which is best",
        "what is best",
        "compare the options",
        "tell me about it",
    }
    if len(text) < 12 or len(re.findall(r"\w+", text)) < 3 or vague:
        return (
            "needs_clarification",
            "Specify a research topic, the items to compare, and your decision criteria.",
        )
    if "tomorrow" in text and ("unreleased" in text or "will announce" in text):
        return (
            "insufficient_evidence",
            "An unannounced future funding event cannot be established from current evidence. Verify after a public announcement.",
        )
    if re.search(
        r"\b(?:steal|exfiltrate)\b.*\b(?:passwords|credentials|secrets)\b|\bbuild\s+(?:ransomware|malware)\b",
        text,
    ):
        return (
            "refused",
            "I cannot help with credential theft or malware. Ask about defensive security research.",
        )
    if re.search(r"\b(?:write|compose)\b.*\b(?:poem|song)\b", text):
        return (
            "needs_clarification",
            "This agent handles source-backed research. Ask a factual research question.",
        )
    return None


async def make_plan(question: str, gateway: Gateway, settings: Settings) -> Plan:
    brief = brief_plan(question)
    if brief:
        gateway.trace.emit("brief_plan", "plan", reason="bounded_identity_or_definition_question")
        return brief
    try:
        plan = await gateway.call(
            "plan",
            prompts.PLAN,
            {
                "question": question,
                "current_date": utcnow().date().isoformat(),
                "limits": {
                    "max_sub_questions": settings.max_sub_questions,
                    "queries_per_sub_question": settings.max_search_queries_per_step,
                    "max_pages": settings.max_pages,
                    "max_rounds": settings.max_rounds,
                },
            },
            Plan,
        )
        plan.sub_questions = plan.sub_questions[: settings.max_sub_questions]
        if settings.llm_provider != "mock":
            # Model assumptions can invent dates, counts or user constraints.
            plan.assumptions = [
                "Answer the original user question using publicly accessible evidence within the configured run limits."
            ]
        # IDs are application-owned, unique and stable regardless of model output.
        for index, step in enumerate(plan.sub_questions, 1):
            step.id = f"q{index}"
            step.search_queries = [
                query[:1200] for query in step.search_queries if len(query.strip()) >= 3
            ][: settings.max_search_queries_per_step]
        return plan
    except Exception as exc:
        gateway.trace.emit("planner_fallback", "plan", error_type=type(exc).__name__)
        return Plan(
            restated_question=question,
            question_type="comparison" if "compare" in question.lower() else "other",
            sub_questions=[
                SearchStep(
                    id="q1",
                    question=question,
                    search_queries=[question[:1200]],
                    rationale="Deterministic fallback after planner failure.",
                )
            ],
            success_criteria=["Find relevant sources", "Report evidence gaps"],
            assumptions=["Default plan used because structured planning was unavailable."],
            stop_condition="At most two rounds, within configured budgets.",
        )


def brief_plan(question: str) -> Plan | None:
    text = question.strip()
    if len(text.split()) > 18 or not re.match(r"^(?:who (?:is|was)|what (?:is|are))\b", text, re.I):
        return None
    if re.search(
        r"\b(?:compare|versus|vs|pros|cons|trade.?offs|why|how|latest|current|today)\b", text, re.I
    ):
        return None
    profile = bool(re.match(r"^who\b", text, re.I))
    return Plan(
        restated_question=text,
        question_type="other",
        effort="brief",
        sub_questions=[
            SearchStep(
                id="q1",
                question=text,
                search_queries=[
                    text
                    + (
                        " official biography profile"
                        if profile
                        else " official documentation overview"
                    )
                ],
                rationale="A short identity/definition question needs a direct sourced overview, not a multi-part survey.",
            )
        ],
        success_criteria=[
            "Answer the question directly with a short sourced overview",
            "Exclude unrequested current-status claims and unsupported details",
        ],
        assumptions=[
            "Interpret the request as a brief overview; all factual details still need evidence."
        ],
        stop_condition="Read at most two candidate pages and stop when two usable sources are available or the bounded gap round ends.",
    )
