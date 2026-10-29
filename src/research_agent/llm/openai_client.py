"""OpenAI Responses API via async HTTP, with native strict JSON Schema."""

from copy import deepcopy
from typing import Any

import httpx
from pydantic import BaseModel

from research_agent.schemas import LLMResponse


def strict_schema(schema: type[BaseModel]) -> dict[str, Any]:
    result = deepcopy(schema.model_json_schema())

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for value in node.values():
                visit(value)
        elif isinstance(node, list):
            for value in node:
                visit(value)

    visit(result)
    return result


class OpenAIClient:
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
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": model,
                "instructions": system,
                "input": user,
                "max_output_tokens": max_tokens,
                "store": False,
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": schema.__name__,
                        "strict": True,
                        "schema": strict_schema(schema),
                    }
                },
            },
        )
        response.raise_for_status()
        body = response.json()
        if body.get("status") != "completed":
            raise ValueError("incomplete_or_refused_response")
        text = "".join(
            part["text"]
            for item in body.get("output", [])
            for part in item.get("content", [])
            if part.get("type") == "output_text"
        )
        return LLMResponse(
            text=text,
            model=body.get("model", model),
            input_tokens=body["usage"]["input_tokens"],
            output_tokens=body["usage"]["output_tokens"],
        )
