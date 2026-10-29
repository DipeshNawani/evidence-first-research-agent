"""Shared transient-only retry and provider-specific circuit state."""

import asyncio
import random
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from research_agent.budget import Budget, BudgetExceeded
from research_agent.config import Settings
from research_agent.tools.base import ToolError
from research_agent.tracing import Trace

T = TypeVar("T")


def classify(exc: Exception) -> ToolError:
    if isinstance(exc, ToolError):
        return exc
    if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        return ToolError("timeout", transient=True)
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        return ToolError(f"http_{status}", transient=status == 429 or status >= 500)
    if isinstance(exc, httpx.TransportError):
        return ToolError("network", transient=True)
    return ToolError(
        "malformed_output"
        if isinstance(exc, (ValueError, TypeError, KeyError))
        else "internal_error"
    )


class Circuit:
    def __init__(self) -> None:
        self.failures = 0
        self.opened_at = 0.0


class Resilience:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.circuits: dict[str, Circuit] = {}

    async def run(
        self,
        name: str,
        action: Callable[[], Awaitable[T]],
        *,
        budget: Budget,
        trace: Trace,
        timeout: float,  # noqa: ASYNC109 - asyncio.timeout is enforced in this wrapper
        before: Callable[[], None],
    ) -> T:
        circuit = self.circuits.setdefault(name, Circuit())
        if circuit.failures >= self.settings.circuit_failures:
            if time.monotonic() - circuit.opened_at < self.settings.circuit_cooldown_seconds:
                trace.emit("circuit_open", "execute", provider=name)
                raise ToolError("circuit_open")
            circuit.failures = 0
        for attempt in range(self.settings.retries + 1):
            budget.check()
            before()
            try:
                async with asyncio.timeout(min(timeout, budget.remaining())):
                    result = await action()
                circuit.failures = 0
                return result
            except BudgetExceeded:
                raise
            except Exception as exc:
                error = classify(exc)
                trace.emit(
                    "attempt_error",
                    "execute",
                    provider=name,
                    attempt=attempt + 1,
                    error_type=error.kind,
                )
                if not error.transient:
                    raise error from None
                circuit.failures += 1
                if circuit.failures >= self.settings.circuit_failures:
                    circuit.opened_at = time.monotonic()
                if (
                    attempt == self.settings.retries
                    or circuit.failures >= self.settings.circuit_failures
                ):
                    raise error from None
                delay = self.settings.retry_base_seconds * 2**attempt * (1 + random.random() / 4)
                trace.emit("retry", "execute", provider=name, attempt=attempt + 1, delay_s=delay)
                await asyncio.sleep(min(delay, budget.remaining()))
        raise AssertionError("unreachable")
