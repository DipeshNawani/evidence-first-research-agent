"""Bounded discover/read/filter loop; source content can never change the plan."""

from research_agent.budget import Budget
from research_agent.config import Settings
from research_agent.pipeline.executor import Executor
from research_agent.pipeline.filter import canonical_url, filter_sources, score_source
from research_agent.safety.injection import detect_injection
from research_agent.schemas import (
    CollectionResult,
    DroppedSource,
    PageData,
    Plan,
    SearchData,
    SearchHit,
    ToolCall,
)
from research_agent.tools.base import ToolError
from research_agent.tracing import Trace


class Collector:
    def __init__(
        self, settings: Settings, executor: Executor, budget: Budget, trace: Trace
    ) -> None:
        self.settings, self.executor, self.budget, self.trace = settings, executor, budget, trace
        self.hits: dict[str, tuple[SearchHit, list[str], bool]] = {}
        self.pages: dict[str, PageData] = {}
        self.attempted: set[str] = set()
        self.quarantined: set[str] = set()

    async def collect(self, question: str, plan: Plan) -> CollectionResult:
        result = CollectionResult(gaps=len(plan.sub_questions))
        for round_index in range(self.settings.max_rounds):
            if self.budget.remaining() <= 0 or self.budget.partial:
                break
            with self.trace.stage("execute"):
                await self.discover(plan, round_index)
                await self.read(question)
            with self.trace.stage("filter"):
                filtered = filter_sources(
                    self.candidates(),
                    question,
                    self.settings,
                    mock=self.settings.llm_provider == "mock",
                )
                dropped = filtered.dropped_sources + [
                    DroppedSource(url=key, reason="injection_quarantined")
                    for key in sorted(self.quarantined)
                ]
                for item in dropped:
                    self.trace.emit("dropped_source", "filter", **item.model_dump())
                gaps = sum(
                    len(
                        {
                            e.source.domain
                            for e in filtered.evidence
                            if step.id in e.sub_question_ids
                        }
                    )
                    < 2
                    for step in plan.sub_questions
                )
                result = CollectionResult(
                    evidence=filtered.evidence,
                    dropped_sources=dropped,
                    gaps=gaps,
                    snippet_sources_count=sum(
                        key not in self.pages for key in self.hits if key not in self.quarantined
                    ),
                    truncated_pages_count=sum(page.truncated for page in self.pages.values()),
                )
                for item in result.evidence:
                    self.trace.emit(
                        "source_kept",
                        "filter",
                        source_id=item.source.id,
                        url=item.source.url,
                        quality_score=item.source.quality_score,
                        provenance=item.source.provenance,
                        characters=len(item.text),
                    )
                self.trace.emit(
                    "gap_check",
                    "filter",
                    gaps=gaps,
                    round=round_index + 1,
                    kept=len(result.evidence),
                )
            if not result.gaps:
                break
        return result

    async def discover(self, plan: Plan, round_index: int) -> None:
        calls = [
            ToolCall(
                name=step.tool,
                args={
                    "query": (query + (" primary sources limitations" if round_index else ""))[
                        :1200
                    ],
                    "max_results": self.settings.max_search_results,
                },
                sub_question_id=step.id,
            )
            for step in plan.sub_questions
            for query in step.search_queries
        ]
        results = await self.executor.batch(calls)
        allowed = {step.id: step.fetch_pages for step in plan.sub_questions}
        for call, result in zip(calls, results, strict=True):
            if not result.ok or not isinstance(result.data, SearchData):
                continue
            for hit in result.data.hits:
                try:
                    key = canonical_url(hit.url)
                except ToolError:
                    key = hit.url
                if key in self.hits:
                    old, ids, read = self.hits[key]
                    self.hits[key] = (
                        old,
                        sorted(set(ids + [call.sub_question_id])),
                        read or allowed[call.sub_question_id],
                    )
                else:
                    self.hits[key] = hit, [call.sub_question_id], allowed[call.sub_question_id]

    async def read(self, question: str) -> None:
        ranked = sorted(
            self.hits.items(),
            key=lambda item: -score_source(item[1][0], item[1][0].snippet, question),
        )
        selected: list[tuple[str, SearchHit, list[str]]] = []
        for key, (hit, ids, read) in ranked:
            if detect_injection(hit.snippet) or detect_injection(hit.title):
                self.quarantined.add(key)
                self.trace.emit("security_event", "filter", url=key, reason="injection_quarantined")
            elif (
                read
                and key not in self.attempted
                and score_source(hit, hit.snippet, question) >= self.settings.source_threshold
            ):
                selected.append((key, hit, ids))
        selected = selected[: max(0, self.settings.max_pages - self.budget.pages)]
        results = await self.executor.batch(
            [
                ToolCall(name="fetch_page", args={"url": hit.url}, sub_question_id=ids[0])
                for _, hit, ids in selected
            ]
        )
        for (key, _, _), result in zip(selected, results, strict=True):
            self.attempted.add(key)
            if result.ok and isinstance(result.data, PageData):
                self.pages[key] = result.data
            elif result.error_type == "injection_quarantined":
                self.quarantined.add(key)

    def candidates(self) -> list[tuple[SearchHit, str, str, list[str]]]:
        candidates = []
        for key, (hit, ids, _) in self.hits.items():
            if key in self.quarantined:
                continue
            page = self.pages.get(key)
            if page:
                # A redirect cannot borrow the original domain's reputation.
                candidates.append(
                    (
                        hit.model_copy(update={"url": page.url, "retrieved_at": page.retrieved_at}),
                        page.text,
                        "page",
                        ids,
                    )
                )
            else:
                candidates.append((hit, hit.snippet, "snippet", ids))
        return candidates
