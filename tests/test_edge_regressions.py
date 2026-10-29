from pathlib import Path

import pytest

from research_agent.config import Settings
from research_agent.runtime import build_agent


@pytest.mark.parametrize(
    "question,status",
    [
        ("Which is best?", "needs_clarification"),
        (
            "Which unreleased HR tech startup will announce the largest funding round tomorrow?",
            "insufficient_evidence",
        ),
    ],
)
async def test_preflight_regressions(tmp_path: Path, question: str, status: str) -> None:
    async with build_agent(Settings(trace_dir=tmp_path, _env_file=None)) as agent:
        result = await agent.research(question)
    assert result.meta.status == status
    assert result.meta.tool_calls == result.meta.tokens == 0
    assert not result.key_findings


async def test_empty_search_cannot_fall_back_to_unrelated_fixture(tmp_path: Path) -> None:
    async with build_agent(Settings(trace_dir=tmp_path, _env_file=None), "empty") as agent:
        result = await agent.research("Compare vector databases for a RAG startup.")
    assert not result.sources
    assert result.meta.status == "insufficient_evidence"
