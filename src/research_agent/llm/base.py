from typing import Protocol

from pydantic import BaseModel

from research_agent.schemas import LLMResponse


class LLMClient(Protocol):
    async def generate(
        self,
        *,
        purpose: str,
        system: str,
        user: str,
        schema: type[BaseModel],
        model: str,
        max_tokens: int,
    ) -> LLMResponse: ...
