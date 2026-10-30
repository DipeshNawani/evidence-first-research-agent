"""Regressions exposed by real hosted-model plans and web source volumes."""

from pathlib import Path

from research_agent.budget import Budget
from research_agent.cache import TTLCache
from research_agent.config import Settings
from research_agent.fixtures import fixture_hits
from research_agent.llm.gateway import Gateway
from research_agent.llm.mock import MockLLM
from research_agent.pipeline.collector import Collector
from research_agent.pipeline.confidence import compute_confidence
from research_agent.pipeline.context import citation_options, pack_context
from research_agent.pipeline.executor import Executor
from research_agent.pipeline.filter import filter_sources, near_duplicate, text_fingerprint
from research_agent.pipeline.planner import make_plan
from research_agent.pipeline.verifier import verify
from research_agent.resilience import Resilience
from research_agent.runtime import build_agent
from research_agent.schemas import AnswerDraft, Evidence, Finding, Plan, SearchStep, Source
from research_agent.tools.base import ToolRegistry
from research_agent.tools.web_search import MockSearch
from research_agent.tracing import Trace


def test_shingle_dedupe_across_domains_and_query_coverage() -> None:
    hit = fixture_hits("vector database")[0]
    copy = hit.model_copy(update={"url": "https://mirror.example/docs"})
    result = filter_sources(
        [
            (hit, hit.snippet, "page", ["q1"]),
            (copy, hit.snippet + " Small footer change.", "page", ["q2"]),
        ],
        "vector database RAG",
        Settings(_env_file=None),
    )
    assert len(result.evidence) == 1
    assert result.evidence[0].sub_question_ids == ["q1", "q2"]
    assert result.dropped_sources[0].reason == "near_duplicate_text"
    assert not near_duplicate(
        text_fingerprint(hit.snippet),
        text_fingerprint("An unrelated biography about painters and architecture."),
    )
    assert near_duplicate(text_fingerprint("vector " * 10000), text_fingerprint("vector " * 10000))


async def test_plan_receives_current_date_and_caps_searches(tmp_path: Path) -> None:
    class WidePlan(MockLLM):
        def _data(self, purpose: str, payload: dict) -> dict:
            if purpose == "plan":
                assert payload["current_date"].startswith("20")
                assert payload["limits"]["queries_per_sub_question"] == 1
                result = super()._data(purpose, payload)
                result["sub_questions"][0]["search_queries"] *= 2
                return result
            return super()._data(purpose, payload)

    settings = Settings(_env_file=None)
    gateway = Gateway(
        WidePlan(), settings, Budget(settings), Trace(tmp_path, mode="mock"), Resilience(settings)
    )
    plan = await make_plan("Compare vector databases for RAG products.", gateway, settings)
    assert len(plan.sub_questions[0].search_queries) == 1


async def test_discover_only_missing_subquestions(tmp_path: Path) -> None:
    settings = Settings(_env_file=None)
    resilience, budget, trace = Resilience(settings), Budget(settings), Trace(tmp_path, mode="mock")
    executor = Executor(
        ToolRegistry([MockSearch(settings, resilience)]),
        settings,
        TTLCache(),
        resilience,
        budget,
        trace,
    )
    collector = Collector(settings, executor, budget, trace)
    plan = Plan(
        restated_question="Compare vector databases",
        question_type="comparison",
        sub_questions=[
            SearchStep(
                id=f"q{i}",
                question="vector database",
                search_queries=["vector database"],
                rationale="Fixture",
            )
            for i in [1, 2]
        ],
        success_criteria=[],
        assumptions=[],
        stop_condition="Bounded",
    )
    await collector.discover(plan, 1, {"q2"})
    starts = [event for event in trace.events if event.event == "tool_start"]
    assert len(starts) == 1 and starts[0].data["sub_question_id"] == "q2"


def test_large_context_packed_without_spending_budget(tmp_path: Path) -> None:
    settings = Settings(_env_file=None, max_total_tokens=18000)
    budget = Budget(settings)
    gateway = Gateway(
        MockLLM(), settings, budget, Trace(tmp_path, mode="mock"), Resilience(settings)
    )
    evidence = [
        Evidence(
            source=Source(
                id=f"S{i}",
                title=f"Source {i}",
                url=f"https://example.com/{i}",
                domain="example.com",
                quality_score=0.8,
            ),
            text="Relevant source content about vector database operations. " * 300,
            sub_question_ids=["q1"],
        )
        for i in range(8)
    ]
    payload, changed = pack_context(
        evidence,
        gateway,
        "synthesize",
        "Return JSON",
        {"question": "Compare vector databases"},
        AnswerDraft,
        fraction=0.65,
    )
    assert changed and payload["evidence"]
    assert all(item["text"].endswith("</untrusted_evidence>") for item in payload["evidence"])
    assert gateway.reservation("synthesize", "Return JSON", payload, AnswerDraft) <= 18000 * 0.65
    assert budget.reserved_tokens == 0 and not budget.partial
    assert gateway.output_limit("judge") == 600


def test_citation_menu_quotes_are_literal_source_substrings() -> None:
    hit = fixture_hits("vector database")[0]
    evidence = Evidence(
        source=Source(
            id="S1", title=hit.title, url=hit.url, domain="qdrant.tech", quality_score=0.8
        ),
        text=hit.snippet,
        sub_question_ids=["q1"],
    )
    options = citation_options("vector search filtering", [evidence])
    assert options[0]["source_id"] == "S1"
    assert options[0]["quote"] in evidence.text


def test_verifier_prunes_only_unsupported_citations() -> None:
    source = Source(
        id="S1", title="Source", url="https://example.com", domain="example.com", quality_score=0.8
    )
    evidence = [
        Evidence(
            source=source,
            text="This exact source quote supports the finding.",
            sub_question_ids=["q1"],
        )
    ]
    finding = Finding(
        claim="A supported claim",
        source_ids=["S1", "missing"],
        supporting_quote="This exact source quote",
    )
    result, rate, rejected = verify(
        AnswerDraft(short_answer="Summary", key_findings=[finding]), evidence
    )
    assert result.key_findings[0].source_ids == ["S1"] and result.key_findings[0].verified
    assert rate == 1 and not rejected
    assert any("Removed 1 citation" in limitation for limitation in result.limitations)


async def test_one_bounded_citation_repair(tmp_path: Path) -> None:
    class BadQuotesOnce(MockLLM):
        def __init__(self) -> None:
            super().__init__()
            self.synthesis_calls = 0

        def _data(self, purpose: str, payload: dict) -> dict:
            result = super()._data(purpose, payload)
            if purpose == "synthesize":
                self.synthesis_calls += 1
                if self.synthesis_calls == 1:
                    for finding in result["key_findings"]:
                        finding["supporting_quote"] = "Fabricated quote absent from every source."
            return result

    settings = Settings(_env_file=None, trace_dir=tmp_path, max_total_tokens=150000)
    async with build_agent(settings) as agent:
        llm = BadQuotesOnce()
        agent.llm = llm
        answer = await agent.research("Compare vector databases for a startup RAG product.")
    assert answer.key_findings and all(finding.verified for finding in answer.key_findings)
    assert llm.synthesis_calls == 2
    assert "citation_repair" in (tmp_path / f"{answer.meta.trace_id}.jsonl").read_text()


def test_low_judge_score_caps_confidence_despite_quote_matches() -> None:
    source = Source(
        id="S1", title="Source", url="https://example.com", domain="example.com", quality_score=1
    )
    evidence = [Evidence(source=source, text="A real source quotation.", sub_question_ids=["q1"])]
    finding = Finding(
        claim="Claim needing entailment review",
        source_ids=["S1"],
        supporting_quote="A real source quotation.",
        verified=True,
    )
    confidence = compute_confidence(
        evidence, [finding], grounding_rate=1, judge_score=0.45, failure_rate=0, gaps=0
    )
    assert confidence.level == "low" and confidence.score <= 0.54
