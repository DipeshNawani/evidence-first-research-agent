"""Assert provider wire formats and refusal handling without spending API credits."""

import json

import httpx
import pytest

from research_agent.llm.anthropic_client import AnthropicClient, claude_schema
from research_agent.llm.openai_client import OpenAIClient, strict_schema
from research_agent.schemas import AnswerDraft


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
async def test_structured_provider_wire_format(provider: str) -> None:
    draft = AnswerDraft(short_answer="Evidence unavailable.", key_findings=[])
    seen = []

    def respond(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        if provider == "openai":
            return httpx.Response(
                200,
                json={
                    "status": "completed",
                    "model": "fixture-model",
                    "output": [
                        {"content": [{"type": "output_text", "text": draft.model_dump_json()}]}
                    ],
                    "usage": {"input_tokens": 12, "output_tokens": 5},
                },
            )
        return httpx.Response(
            200,
            json={
                "stop_reason": "end_turn",
                "model": "fixture-model",
                "content": [{"type": "text", "text": draft.model_dump_json()}],
                "usage": {"input_tokens": 12, "output_tokens": 5},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as http:
        client = (
            OpenAIClient(http, "fixture")
            if provider == "openai"
            else AnthropicClient(http, "fixture")
        )
        result = await client.generate(
            purpose="synthesize",
            system="Fixture instructions",
            user="{}",
            schema=AnswerDraft,
            model="fixture-model",
            max_tokens=100,
        )
    assert AnswerDraft.model_validate_json(result.text) == draft
    assert result.input_tokens == 12
    if provider == "openai":
        assert seen[0]["text"]["format"]["strict"] is True
        assert seen[0]["store"] is False
    else:
        assert seen[0]["output_config"]["format"]["type"] == "json_schema"


async def test_openai_incomplete_response_is_rejected() -> None:
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"status": "incomplete"}))
    ) as http:
        with pytest.raises(ValueError, match="incomplete"):
            await OpenAIClient(http, "fixture").generate(
                purpose="plan",
                system="fixture",
                user="{}",
                schema=AnswerDraft,
                model="fixture-model",
                max_tokens=100,
            )


def test_native_schema_required_nullable_fields() -> None:
    schema = strict_schema(AnswerDraft)
    assert set(schema["required"]) == set(schema["properties"])
    assert schema["additionalProperties"] is False
    assert "default" not in schema["properties"]["comparison_table"]


def test_claude_schema_strips_unsupported_constraints() -> None:
    schema = claude_schema(AnswerDraft)
    finding = schema["$defs"]["Finding"]
    assert "maxLength" not in finding["properties"]["claim"]
    assert "maxItems" not in finding["properties"]["source_ids"]
    assert "Constraints enforced by caller" in finding["properties"]["claim"]["description"]
