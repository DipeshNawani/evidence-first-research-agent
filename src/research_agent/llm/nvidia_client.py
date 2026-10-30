"""NVIDIA-hosted Nemotron through its OpenAI-compatible Chat Completions API.

Use NVIDIA's documented JSON mode and supply the original Pydantic schema as
trusted instructions. The shared gateway validates every output and bounds repair.
JSON mode ensures JSON syntax; it does not guarantee schema compliance.
"""

import json

import httpx
from pydantic import BaseModel

from research_agent.schemas import LLMResponse


class NvidiaClient:
    def __init__(self, http: httpx.AsyncClient, api_key: str) -> None:
        self.http, self.api_key = http, api_key

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
        schema_instruction = (
            "\nOUTPUT CONTRACT: Return one JSON object matching this JSON Schema. "
            "No Markdown, reasoning text, or extra keys.\n" + json.dumps(schema.model_json_schema())
        )
        response = await self.http.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Accept": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system + schema_instruction},
                    {"role": "user", "content": user},
                ],
                "response_format": {"type": "json_object"},
                "reasoning_effort": "none",
                "temperature": 0,
                "max_tokens": max_tokens,
                "stream": False,
            },
        )
        response.raise_for_status()
        if response.status_code != 200:
            raise ValueError("nvidia_response_pending_or_incomplete")
        body = response.json()
        choice = body["choices"][0]
        message = choice["message"]
        if choice.get("finish_reason") != "stop" or message.get("refusal"):
            raise ValueError("incomplete_or_refused_response")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("empty_model_response")
        # reasoning_content is intentionally neither returned nor logged.
        return LLMResponse(
            text=content,
            model=body.get("model", model),
            input_tokens=body["usage"]["prompt_tokens"],
            output_tokens=body["usage"]["completion_tokens"],
        )
