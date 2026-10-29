"""Claude Messages API native JSON outputs, validated again at the boundary."""

from typing import Any

import httpx
from pydantic import BaseModel

from research_agent.llm.openai_client import strict_schema
from research_agent.schemas import LLMResponse


def claude_schema(schema: type[BaseModel]) -> dict[str, Any]:
    """Move unsupported constraints to descriptions; local validation stays strict."""
    result = strict_schema(schema)
    unsupported = {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "maxItems",
        "uniqueItems",
    }

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            removed = {
                key: node.pop(key)
                for key in list(node)
                if key in unsupported or (key == "minItems" and node[key] > 1)
            }
            if removed:
                node["description"] = (
                    node.get("description", "") + f" Constraints enforced by caller: {removed}"
                ).strip()
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(result)
    return result


class AnthropicClient:
    def __init__(self, http: httpx.AsyncClient, api_key: str) -> None:
        self.http = http
        self.api_key = api_key

    async def generate(
        self,
        *,
        purpose: str,
        system: str,
        user: str,
        schema: type[BaseModel],
        model: str,
        max_tokens: int,
    ) -> LLMResponse:
        response = await self.http.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
            json={
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
                "output_config": {
                    "format": {"type": "json_schema", "schema": claude_schema(schema)}
                },
            },
        )
        response.raise_for_status()
        body = response.json()
        if body.get("stop_reason") != "end_turn":
            raise ValueError("incomplete_or_refused_response")
        text = "".join(part["text"] for part in body["content"] if part["type"] == "text")
        return LLMResponse(
            text=text,
            model=body.get("model", model),
            input_tokens=body["usage"]["input_tokens"],
            output_tokens=body["usage"]["output_tokens"],
        )
