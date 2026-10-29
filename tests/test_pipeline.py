from pathlib import Path

from research_agent.config import Settings
from research_agent.llm.mock import MockLLM
from research_agent.pipeline.confidence import compute_confidence
from research_agent.pipeline.filter import canonical_url, filter_sources
from research_agent.pipeline.planner import make_plan
from research_agent.pipeline.verifier import verify
from research_agent.runtime import build_agent
from research_agent.schemas import AnswerDraft, Evidence, Finding, Source


async def test_happy_path(tmp_path: Path) -> None:
    settings = Settings(trace_dir=tmp_path, _env_file=None)
    async with build_agent(settings) as agent:
        answer = await agent.research(
            "Compare the top 3 open-source vector databases for RAG products."
        )
    assert len(answer.key_findings) == 3
    assert all(f.verified for f in answer.key_findings)
    assert answer.meta.grounding_rate == 1
    assert answer.comparison_table
    assert answer.confidence.level == "low"  # honest fixture confidence cap
    assert answer.meta.tool_calls <= settings.max_tool_calls


async def test_all_search_fails(tmp_path: Path) -> None:
    settings = Settings(trace_dir=tmp_path, retry_base_seconds=0, _env_file=None)
    async with build_agent(settings, "all_fail") as agent:
        answer = await agent.research("Compare vector databases for a startup RAG product.")
    assert not answer.key_findings
    assert not answer.sources
    assert answer.meta.status == "insufficient_evidence"
    assert answer.confidence.score <= 0.2


async def test_plan_repair_and_fallback(tmp_path: Path) -> None:
    settings = Settings(trace_dir=tmp_path, _env_file=None, max_total_tokens=100000)
    async with build_agent(settings) as agent:
        agent.llm = MockLLM(invalid_calls=1)
        answer = await agent.research("Compare vector databases for RAG products.")
        assert len(answer.key_findings) == 3
        assert agent.llm.calls[:2] == ["plan", "plan"]
        from research_agent.budget import Budget
        from research_agent.llm.gateway import Gateway
        from research_agent.tracing import Trace

        gateway = Gateway(
            MockLLM(invalid_calls=10),
            settings,
            Budget(settings),
            Trace(tmp_path, mode="mock"),
            agent.resilience,
        )
        plan = await make_plan("Compare vector databases for RAG products.", gateway, settings)
        assert len(plan.sub_questions) == 1
        assert "fallback" in plan.sub_questions[0].rationale.lower()


def test_verifier_rejects_unknown_wrong_quote_and_rebuilds_summary() -> None:
    source = Source(
        id="S1", title="test", url="https://example.com", domain="example.com", quality_score=0.8
    )
    evidence = [
        Evidence(
            source=source,
            text="This is an exact supporting quote from a source.",
            sub_question_ids=["q1"],
        )
    ]
    good = Finding(
        claim="Supported observation",
        source_ids=["S1"],
        supporting_quote="This is an exact supporting quote",
    )
    bad = good.model_copy(update={"source_ids": ["S999"]})
    fabricated = good.model_copy(
        update={"supporting_quote": "This quotation was fabricated completely"}
    )
    answer, rate, removed = verify(
        AnswerDraft(short_answer="Invented summary", key_findings=[good, bad, fabricated]), evidence
    )
    assert rate == 1 / 3 and len(removed) == 2
    assert answer.key_findings[0].verified
    assert "Invented" not in answer.short_answer
    low = compute_confidence(
        evidence, [good], grounding_rate=0.3, judge_score=0.5, failure_rate=0.5, gaps=2
    )
    high = compute_confidence(
        evidence, [good], grounding_rate=1, judge_score=0.9, failure_rate=0, gaps=0
    )
    assert high.score > low.score


def test_filter_dedupe_and_spam() -> None:
    from research_agent.fixtures import fixture_hits

    hit = fixture_hits("vector databases")[0]
    duplicate = hit.model_copy(update={"url": hit.url + "?utm_source=x"})
    bad = hit.model_copy(
        update={"title": "Top 100 buy now affiliate", "url": "https://spam.example/top-100"}
    )
    filtered = filter_sources(
        [
            (hit, hit.snippet, "page", ["q1"]),
            (duplicate, hit.snippet, "page", ["q2"]),
            (bad, "buy now sponsored affiliate " * 30, "snippet", ["q1"]),
        ],
        "vector databases RAG startup",
        Settings(_env_file=None),
    )
    assert len(filtered.evidence) == 1
    assert filtered.evidence[0].sub_question_ids == ["q1", "q2"]
    assert len(filtered.dropped_sources) == 2
    assert (
        canonical_url("https://example.com/a?utm_source=x&version=2#top")
        == "https://example.com/a?version=2"
    )
