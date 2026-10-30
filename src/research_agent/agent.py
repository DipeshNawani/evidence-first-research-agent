"""Visible state machine. Dependencies are injected; mutable run state is isolated."""

import time
from typing import Literal

from research_agent.budget import Budget
from research_agent.cache import TTLCache
from research_agent.config import Settings
from research_agent.llm.base import LLMClient
from research_agent.llm.gateway import Gateway
from research_agent.pipeline.collector import Collector
from research_agent.pipeline.confidence import compute_confidence
from research_agent.pipeline.executor import Executor
from research_agent.pipeline.planner import early_exit, make_plan
from research_agent.pipeline.review import review
from research_agent.pipeline.verifier import attribute_source_claims
from research_agent.resilience import Resilience
from research_agent.schemas import (
    AnswerDraft,
    AnswerMeta,
    CollectionResult,
    FinalAnswer,
    JudgeScore,
)
from research_agent.tools.base import ToolRegistry
from research_agent.tracing import Trace


class ResearchAgent:
    def __init__(
        self,
        settings: Settings,
        llm: LLMClient,
        registry: ToolRegistry,
        *,
        cache: TTLCache | None = None,
        resilience: Resilience | None = None,
    ) -> None:
        self.settings, self.llm, self.registry = settings, llm, registry
        self.cache = cache or TTLCache(settings.cache_ttl_seconds, settings.cache_max_entries)
        self.resilience = resilience or Resilience(settings)

    async def research(self, question: str) -> FinalAnswer:
        mode: Literal["mock", "live"] = "mock" if self.settings.llm_provider == "mock" else "live"
        trace, budget = Trace(self.settings.trace_dir, mode=mode), Budget(self.settings)
        gateway = Gateway(self.llm, self.settings, budget, trace, self.resilience)
        executor = Executor(
            self.registry, self.settings, self.cache, self.resilience, budget, trace
        )
        meta = AnswerMeta(trace_id=trace.id, mode=mode)
        collected, grounding, judgment = CollectionResult(), 0.0, None
        draft = AnswerDraft(
            short_answer="Could not gather sufficient evidence.",
            key_findings=[],
            suggested_next_steps=["Clarify the scope or retry with working search providers."],
        )
        with trace.stage("understand"):
            exit_reason = early_exit(question)
        if exit_reason:
            meta.status, draft.short_answer = exit_reason
            trace.emit("early_exit", "understand", status=meta.status)
        else:
            # PLAN: only trusted user input, never fetched content.
            with trace.stage("plan"):
                plan = await make_plan(question, gateway, self.settings)
                trace.emit("plan", "plan", plan=plan.model_dump(mode="json"))
                meta.plan_summary = plan.restated_question
            # EXECUTE -> FILTER -> optional one gap round.
            collected = await Collector(self.settings, executor, budget, trace).collect(
                question, plan
            )
            # SYNTHESIZE -> VERIFY -> JUDGE -> optional one revision.
            if collected.evidence:
                reviewed = await review(question, plan, collected.evidence, gateway, self.settings)
                draft, grounding, judgment = (
                    reviewed.draft,
                    reviewed.grounding_rate,
                    reviewed.judgment,
                )
            if not draft.key_findings:
                meta.status = "insufficient_evidence"
                draft.limitations.append(
                    "Could not gather and synthesize verified evidence; no factual answer is established."
                )
            # Synthesis assumptions have no citation contract. Keep only the scope
            # assumptions made before retrieval, so they cannot bypass verification.
            draft.assumptions = list(dict.fromkeys(plan.assumptions))
            if mode == "live" and draft.key_findings:
                draft = attribute_source_claims(draft, collected.evidence)
            self.add_limitations(draft, collected, judgment)
        # CONFIDENCE + GUARD: deterministic and observable.
        failure_rate = self.failure_rate(executor, trace, budget)
        with trace.stage("confidence"):
            confidence = compute_confidence(
                collected.evidence,
                draft.key_findings,
                grounding_rate=grounding,
                judge_score=judgment.score if judgment else None,
                failure_rate=failure_rate,
                gaps=collected.gaps,
                mock=mode == "mock",
            )
            if (
                confidence.level == "low"
                or confidence.score < self.settings.low_confidence_threshold
            ) and meta.status == "completed":
                draft.short_answer = (
                    "Low confidence; provisional evidence only. " + draft.short_answer
                )
                draft.suggested_next_steps.insert(
                    0,
                    "Verify the cited primary sources and missing criteria before making a decision.",
                )
            trace.emit("confidence", "confidence", **confidence.model_dump())
        if budget.partial:
            draft.limitations.append("Budget exhausted: this is a partial best-effort result.")
        used = {source_id for finding in draft.key_findings for source_id in finding.source_ids}
        meta.latency_s = round(time.monotonic() - budget.started, 4)
        meta.tool_calls, meta.tokens, meta.token_upper_bound_reserved = (
            budget.tool_calls,
            budget.tokens,
            budget.reserved_tokens,
        )
        meta.est_cost_usd, meta.models = budget.cost, sorted(budget.models)
        meta.grounding_rate, meta.judge_score = grounding, judgment.score if judgment else None
        meta.dropped_sources_count, meta.tool_failure_rate, meta.partial = (
            len(collected.dropped_sources),
            failure_rate,
            budget.partial,
        )
        meta.stage_latency_s = trace.stage_latencies
        answer = FinalAnswer(
            **draft.model_dump(),
            user_question=question,
            sources=[e.source for e in collected.evidence if e.source.id in used],
            confidence=confidence,
            meta=meta,
        )
        trace.emit(
            "run_end",
            "run",
            status=meta.status,
            latency_s=meta.latency_s,
            tokens=meta.tokens,
            tool_calls=meta.tool_calls,
            est_cost_usd=meta.est_cost_usd,
        )
        return answer

    @staticmethod
    def failure_rate(executor: Executor, trace: Trace, budget: Budget) -> float:
        failed = sum(not result.ok for result in executor.results)
        attempt_errors = sum(
            event.event == "attempt_error"
            for event in trace.events
            if event.stage == "execute"
            and not str(event.data.get("provider", "")).startswith("llm:")
        )
        return min(1, max(failed, attempt_errors) / max(1, budget.tool_calls))

    @staticmethod
    def add_limitations(
        draft: AnswerDraft, collected: CollectionResult, judgment: JudgeScore | None
    ) -> None:
        if collected.truncated_pages_count:
            draft.limitations.append(
                "Fetched evidence was truncated to the configured character budget; later context may be missing."
            )
        if collected.snippet_sources_count:
            draft.limitations.append(
                "Some sources were unavailable as full pages; search snippets were used where sufficient."
            )
        if collected.dropped_sources:
            draft.limitations.append(
                f"Dropped {len(collected.dropped_sources)} sources: "
                + ", ".join(sorted({d.reason for d in collected.dropped_sources}))
                + "."
            )
        if collected.gaps:
            draft.limitations.append(
                f"{collected.gaps} sub-question(s) lack two independent candidate domains."
            )
        if judgment is None:
            draft.limitations.append(
                "Independent model judge unavailable or disabled; confidence uses a conservative default."
            )
        elif judgment.score < 0.5:
            draft.limitations.append(
                "The model judge flagged low answer quality. Quote matches do not establish that every claim follows from its source; verify before use."
            )
