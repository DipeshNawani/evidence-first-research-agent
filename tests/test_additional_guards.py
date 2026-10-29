import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from research_agent.budget import Budget
from research_agent.config import Settings
from research_agent.llm.mock import MockLLM
from research_agent.pipeline.confidence import compute_confidence
from research_agent.runtime import build_agent
from research_agent.schemas import Evidence, FetchArgs, Finding, LLMResponse, Source
from research_agent.tools.base import ToolError
from research_agent.tools.fetch_page import FetchPage
from research_agent.tracing import Trace


async def test_injection_never_reaches_synthesis(tmp_path: Path) -> None:
    class Spy(MockLLM):
        def __init__(self) -> None:
            super().__init__()
            self.evidence_payloads: list[str] = []

        async def generate(self, **kwargs: Any) -> LLMResponse:
            if kwargs["purpose"] in {"synthesize", "judge"}:
                self.evidence_payloads.append(json.dumps(json.loads(kwargs["user"])["evidence"]))
            return await super().generate(**kwargs)

    async with build_agent(Settings(trace_dir=tmp_path, _env_file=None), "injection") as agent:
        spy = Spy()
        agent.llm = spy
        answer = await agent.research("Compare vector databases for RAG products.")
    assert answer.key_findings and spy.evidence_payloads
    assert all(
        "ignore previous instructions" not in payload.lower() for payload in spy.evidence_payloads
    )


async def test_cache_preserves_retrieval_time(tmp_path: Path) -> None:
    async with build_agent(Settings(trace_dir=tmp_path, _env_file=None)) as agent:
        first = await agent.research("Compare vector databases for RAG products.")
        second = await agent.research("Compare vector databases for RAG products.")
    assert second.meta.tool_calls == 0
    assert {s.url: s.retrieved_at for s in first.sources} == {
        s.url: s.retrieved_at for s in second.sources
    }


async def test_compressed_page_is_rejected(tmp_path: Path, monkeypatch) -> None:
    async def target(url: str) -> tuple[str, str, str]:
        return "https://8.8.8.8/", "example.com", "example.com"

    monkeypatch.setattr("research_agent.tools.fetch_page.pinned_target", target)
    # A predecoded response simulates a server ignoring Accept-Encoding: identity.
    response = httpx.Response(200, headers={"content-type": "text/html"}, text="x" * 100)
    response.headers["content-encoding"] = "gzip"
    settings = Settings(_env_file=None)
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r: response)) as http:
        with pytest.raises(ToolError, match="compressed_response_rejected"):
            await FetchPage(http, settings).run(
                FetchArgs(url="https://example.com"),
                budget=Budget(settings),
                trace=Trace(tmp_path, mode="mock"),
            )


@pytest.mark.parametrize("signal", ["grounding_rate", "judge_score", "failure_rate", "gaps"])
def test_confidence_monotonic_per_signal(signal: str) -> None:
    source = Source(
        id="S1", title="Fixture", url="https://example.com", domain="example.com", quality_score=0.8
    )
    evidence = [
        Evidence(source=source, text="Support text for a verified claim.", sub_question_ids=["q1"])
    ]
    findings = [
        Finding(
            claim="Claim",
            source_ids=["S1"],
            supporting_quote="Support text for a verified claim.",
            verified=True,
        )
    ]
    args: dict[str, Any] = {
        "grounding_rate": 0.5,
        "judge_score": 0.5,
        "failure_rate": 0.5,
        "gaps": 2,
    }
    before = compute_confidence(evidence, findings, **args)
    args[signal] = 0 if signal in {"failure_rate", "gaps"} else 1
    after = compute_confidence(evidence, findings, **args)
    assert after.score > before.score
