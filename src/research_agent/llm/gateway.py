"""All model calls share validation repair, accounting and transient retry rules."""

import json
import time
from typing import Any, TypeVar, cast

from pydantic import BaseModel, ValidationError

from research_agent.budget import Budget
from research_agent.config import Settings
from research_agent.llm.base import LLMClient
from research_agent.llm.validation import recover_draft
from research_agent.resilience import Resilience
from research_agent.schemas import AnswerDraft
from research_agent.tracing import Trace

S = TypeVar("S", bound=BaseModel)


class Gateway:
    def __init__(
        self,
        llm: LLMClient,
        settings: Settings,
        budget: Budget,
        trace: Trace,
        resilience: Resilience,
    ) -> None:
        self.llm, self.settings, self.budget, self.trace, self.resilience = (
            llm,
            settings,
            budget,
            trace,
            resilience,
        )

    def output_limit(self, purpose: str) -> int:
        return (
            self.settings.judge_output_tokens
            if purpose == "judge"
            else self.settings.llm_output_tokens
        )

    def reservation(
        self, purpose: str, system: str, payload: dict[str, Any], schema: type[BaseModel]
    ) -> int:
        user = json.dumps(payload, ensure_ascii=True)
        return (
            len((system + user + json.dumps(schema.model_json_schema())).encode())
            + 512
            + self.output_limit(purpose)
        )

    async def call(self, purpose: str, system: str, payload: dict[str, Any], schema: type[S]) -> S:
        data = dict(payload)
        model = self.settings.judge_model if purpose == "judge" else self.settings.model
        output_limit = self.output_limit(purpose)
        for repair in range(self.settings.repair_retries + 1):
            user = json.dumps(data, ensure_ascii=True)
            # UTF-8 byte count is a conservative tokenizer-independent reservation.
            # Include schema + framing, not just user content; timed-out attempts stay charged.
            upper = self.reservation(purpose, system, data, schema) - output_limit

            async def action(
                user_text: str = user, reservation_tokens: int = upper + output_limit
            ) -> str:
                started = time.monotonic()
                response = await self.llm.generate(
                    purpose=purpose,
                    system=system,
                    user=user_text,
                    schema=schema,
                    model=model,
                    max_tokens=output_limit,
                )
                self.budget.tokens += response.input_tokens + response.output_tokens
                self.budget.settle_llm(
                    reservation_tokens, response.input_tokens + response.output_tokens
                )
                self.budget.models.add(response.model)
                inp = (
                    self.settings.judge_input_usd_per_million
                    if purpose == "judge"
                    else self.settings.input_usd_per_million
                )
                out = (
                    self.settings.judge_output_usd_per_million
                    if purpose == "judge"
                    else self.settings.output_usd_per_million
                )
                cost = (
                    None
                    if inp is None or out is None
                    else (response.input_tokens * inp + response.output_tokens * out) / 1_000_000
                )
                if self.settings.llm_provider == "mock":
                    cost = 0.0
                if cost is not None and self.budget.cost is not None:
                    self.budget.cost += cost
                else:
                    self.budget.cost = None
                self.trace.emit(
                    "llm_call",
                    purpose,
                    model=response.model,
                    input_tokens=response.input_tokens,
                    output_tokens=response.output_tokens,
                    latency_s=time.monotonic() - started,
                    est_cost_usd=cost,
                )
                return response.text

            raw = await self.resilience.run(
                f"llm:{model}",
                action,
                budget=self.budget,
                trace=self.trace,
                timeout=self.settings.llm_timeout_seconds,
                before=lambda bound=upper: self.budget.reserve_llm(bound, output_limit),
            )
            try:
                return cast(S, schema.model_validate_json(raw))
            except ValidationError as exc:
                # Do not echo invalid text (could contain secrets or source instructions).
                errors = [
                    {"loc": list(e["loc"]), "type": e["type"]}
                    for e in exc.errors(include_input=False)
                ]
                self.trace.emit("validation_error", purpose, repair=repair, errors=errors)
                if schema is AnswerDraft:
                    recovered = recover_draft(raw)
                    if recovered:
                        answer, discarded = recovered
                        self.trace.emit(
                            "partial_draft_recovered",
                            purpose,
                            retained_findings=len(answer.key_findings),
                            discarded_findings=discarded,
                        )
                        return cast(S, answer)
                data["repair"] = {
                    "instruction": "Previous output failed validation. Return a complete valid object.",
                    "errors": errors,
                }
        raise ValueError("structured_output_invalid_after_repair")
