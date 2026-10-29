import asyncio
import time

from pydantic import ValidationError

from research_agent.budget import Budget, BudgetExceeded
from research_agent.cache import TTLCache
from research_agent.config import Settings
from research_agent.resilience import Resilience, classify
from research_agent.schemas import ToolCall, ToolResult
from research_agent.tools.base import ToolError, ToolRegistry
from research_agent.tracing import Trace


class Executor:
    def __init__(
        self,
        registry: ToolRegistry,
        settings: Settings,
        cache: TTLCache,
        resilience: Resilience,
        budget: Budget,
        trace: Trace,
    ) -> None:
        self.registry, self.settings, self.cache, self.resilience = (
            registry,
            settings,
            cache,
            resilience,
        )
        self.budget, self.trace = budget, trace
        self.semaphore = asyncio.Semaphore(settings.concurrency)
        self.results: list[ToolResult] = []

    async def execute(self, call: ToolCall) -> ToolResult:
        started = time.monotonic()
        result = ToolResult(ok=False)
        async with self.semaphore:
            self.trace.emit(
                "tool_start",
                "execute",
                tool=call.name,
                args=call.args,
                sub_question_id=call.sub_question_id,
            )
            try:
                self.budget.check()
                tool = self.registry.get(call.name)
                if tool is None:
                    raise ToolError("unknown_tool")
                args = tool.args_schema.model_validate(call.args)
                key = self.cache.key(tool.cache_namespace, args.model_dump())
                data = self.cache.get(key)
                if data is not None:
                    result.cached = True
                else:

                    async def action() -> dict:
                        raw = await tool.run(args, budget=self.budget, trace=self.trace)
                        parsed = tool.result_schema.model_validate(raw)
                        return parsed.model_dump(mode="json")

                    if call.name == "web_search":
                        data = await action()  # Provider retries each charge their own attempt.
                    else:
                        data = await self.resilience.run(
                            call.name,
                            action,
                            budget=self.budget,
                            trace=self.trace,
                            timeout=self.settings.tool_timeout_seconds,
                            before=lambda: self.budget.charge_tool(page=call.name == "fetch_page"),
                        )
                    self.cache.put(key, data)
                result.data = tool.result_schema.model_validate(data)
                result.ok = True
            except BudgetExceeded as exc:
                result.error_type = f"budget_{exc}"
                self.trace.emit("budget_exhausted", "execute", reason=str(exc))
            except ValidationError:
                result.error_type = "invalid_args_or_output"
            except Exception as exc:
                result.error_type = classify(exc).kind
        result.latency_ms = round((time.monotonic() - started) * 1000, 3)
        self.results.append(result)
        self.trace.emit(
            "tool_end", "execute", tool=call.name, **result.model_dump(exclude={"data"})
        )
        return result

    async def batch(self, calls: list[ToolCall]) -> list[ToolResult]:
        return list(await asyncio.gather(*(self.execute(call) for call in calls)))
