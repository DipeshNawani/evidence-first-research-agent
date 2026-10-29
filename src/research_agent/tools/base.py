from typing import Any, Protocol

from pydantic import BaseModel

from research_agent.budget import Budget
from research_agent.schemas import PageData, SearchData
from research_agent.tracing import Trace


class Tool(Protocol):
    name: str
    cache_namespace: str

    @property
    def args_schema(self) -> type[BaseModel]: ...

    @property
    def result_schema(self) -> type[SearchData] | type[PageData]: ...

    async def run(self, args: BaseModel, *, budget: Budget, trace: Trace) -> Any: ...


class ToolError(Exception):
    def __init__(self, kind: str, *, transient: bool = False) -> None:
        super().__init__(kind)
        self.kind = kind
        self.transient = transient


class ToolRegistry:
    def __init__(self, tools: list[Tool]) -> None:
        self.tools = {tool.name: tool for tool in tools}

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)
