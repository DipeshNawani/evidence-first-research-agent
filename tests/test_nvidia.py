"""NVIDIA integration tests are fully offline; no real credentials are needed."""

import json
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

from research_agent.budget import Budget
from research_agent.config import Settings
from research_agent.llm.gateway import Gateway
from research_agent.llm.nvidia_client import NvidiaClient
from research_agent.resilience import Resilience
from research_agent.runtime import build_agent
from research_agent.schemas import AnswerDraft
from research_agent.tracing import Trace, redact


async def test_nvidia_wire_format_and_usage() -> None:
    draft = AnswerDraft(short_answer="No evidence supplied.", key_findings=[])
    seen = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(
            200,
            json={
                "model": "nvidia/nemotron-3-ultra-550b-a55b",
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": draft.model_dump_json(),
                            "reasoning_content": "not to be exposed",
                        },
                    }
                ],
                "usage": {"prompt_tokens": 25, "completion_tokens": 12},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        result = await NvidiaClient(http, "nvapi-fixture").generate(
            purpose="synthesize",
            system="Use evidence only.",
            user="{}",
            schema=AnswerDraft,
            model="nvidia/nemotron-3-ultra-550b-a55b",
            max_tokens=100,
        )
    assert seen[0].url == "https://integrate.api.nvidia.com/v1/chat/completions"
    assert seen[0].headers["Authorization"] == "Bearer nvapi-fixture"
    body = json.loads(seen[0].content)
    assert body["response_format"] == {"type": "json_object"}
    assert body["reasoning_effort"] == "none" and body["stream"] is False
    assert "JSON Schema" in body["messages"][0]["content"]
    assert result.input_tokens == 25 and result.output_tokens == 12
    assert "not to be exposed" not in result.text
    assert AnswerDraft.model_validate_json(result.text) == draft


@pytest.mark.parametrize(
    "finish,content", [("length", "{}"), ("content_filter", "{}"), ("stop", None), ("stop", "")]
)
async def test_nvidia_incomplete_and_empty(finish: str, content: str | None) -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200, json={"choices": [{"finish_reason": finish, "message": {"content": content}}]}
            )
        )
    ) as http:
        with pytest.raises(ValueError):
            await NvidiaClient(http, "fixture").generate(
                purpose="plan",
                system="JSON",
                user="{}",
                schema=AnswerDraft,
                model="fixture",
                max_tokens=100,
            )


async def test_nvidia_json_mode_still_validates_and_repairs(tmp_path: Path) -> None:
    calls = 0
    valid = AnswerDraft(short_answer="Evidence unavailable.", key_findings=[])

    def respond(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        content = '{"wrong":"shape"}' if calls == 1 else valid.model_dump_json()
        return httpx.Response(
            200,
            json={
                "choices": [{"finish_reason": "stop", "message": {"content": content}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10},
            },
        )

    settings = Settings(_env_file=None, llm_provider="nvidia")
    trace = Trace(tmp_path, mode="live")
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        gateway = Gateway(
            NvidiaClient(http, "fixture"), settings, Budget(settings), trace, Resilience(settings)
        )
        result = await gateway.call("synthesize", "Return JSON", {}, AnswerDraft)
    assert result == valid and calls == 2
    assert any(event.event == "validation_error" for event in trace.events)


async def test_nvidia_runtime_and_missing_key() -> None:
    settings = Settings(_env_file=None, llm_provider="nvidia", nvidia_api_key="nvapi-fixture")
    async with build_agent(settings) as agent:
        assert isinstance(agent.llm, NvidiaClient)
    missing = Settings(_env_file=None, llm_provider="nvidia", nvidia_api_key="")
    with pytest.raises(ValueError, match="RA_NVIDIA_API_KEY"):
        async with build_agent(missing):
            pass


def test_nvidia_settings_and_redaction() -> None:
    settings = Settings(_env_file=None, llm_provider="nvidia")
    assert settings.model == settings.judge_model == "nvidia/nemotron-3-ultra-550b-a55b"
    assert redact("key nvapi-fixtureSecret") == "key [SECRET]"
    with pytest.raises(ValidationError):
        Settings(_env_file=None, llm_provider="unsupported")
