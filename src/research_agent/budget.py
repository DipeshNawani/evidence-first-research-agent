"""Per-run budgets; charge every network attempt, including retries and fallback."""

import time

from research_agent.config import Settings


class BudgetExceeded(Exception):
    pass


class Budget:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.started = time.monotonic()
        self.deadline = self.started + settings.max_wall_seconds
        self.tool_calls = 0
        self.pages = 0
        self.reserved_tokens = 0
        self.tokens = 0
        rates_known = (
            settings.input_usd_per_million is not None
            and settings.output_usd_per_million is not None
        )
        judge_rates_known = not settings.judge_enabled or (
            settings.judge_input_usd_per_million is not None
            and settings.judge_output_usd_per_million is not None
        )
        self.cost: float | None = (
            0 if settings.llm_provider == "mock" or (rates_known and judge_rates_known) else None
        )
        self.models: set[str] = set()
        self.partial = False

    def remaining(self) -> float:
        return max(0, self.deadline - time.monotonic())

    def check(self) -> None:
        if self.remaining() <= 0:
            self.partial = True
            raise BudgetExceeded("wall_clock")

    def charge_tool(self, *, page: bool = False) -> None:
        self.check()
        if self.tool_calls >= self.settings.max_tool_calls or (
            page and self.pages >= self.settings.max_pages
        ):
            self.partial = True
            raise BudgetExceeded("tool_or_page_limit")
        self.tool_calls += 1
        self.pages += int(page)

    def reserve_llm(self, input_upper_bound: int, output_limit: int) -> None:
        self.check()
        if self.reserved_tokens + input_upper_bound + output_limit > self.settings.max_total_tokens:
            self.partial = True
            raise BudgetExceeded("tokens")
        # Keep reservations spent even when providers time out: billing is uncertain.
        self.reserved_tokens += input_upper_bound + output_limit

    def settle_llm(self, reservation: int, actual_tokens: int) -> None:
        """Release unused allowance only after a provider reports actual usage.

        Failed/timed-out attempts never settle: their billing remains uncertain.
        """
        self.reserved_tokens += actual_tokens - reservation
        if self.reserved_tokens > self.settings.max_total_tokens:
            self.partial = True
