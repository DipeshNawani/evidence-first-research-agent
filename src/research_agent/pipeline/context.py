"""Pack evidence before reserving a model request, rather than failing oversized runs."""

import re
from typing import Any

from pydantic import BaseModel

from research_agent.budget import BudgetExceeded
from research_agent.llm.gateway import Gateway
from research_agent.pipeline.filter import words
from research_agent.safety.injection import untrusted_payload
from research_agent.schemas import Evidence


def evidence_payload(evidence: list[Evidence]) -> list[dict[str, Any]]:
    return [
        {"source": e.source.model_dump(mode="json"), "text": untrusted_payload(e.text)}
        for e in evidence
    ]


def citation_options(question: str, evidence: list[Evidence]) -> list[dict[str, str]]:
    """Give the model exact, relevant quote choices derived only from source text."""
    terms = words(question)
    options = []
    for item in evidence:
        candidates = [
            part.strip()
            for part in re.split(r"(?<=[.!?])\s+|\n+", item.text)
            if len(part.strip()) >= 12
        ]
        if not candidates:
            continue
        selected = max(candidates, key=lambda part: len(words(part) & terms))
        options.append({"source_id": item.source.id, "quote": selected[:160]})
    return options


def pack_context(
    evidence: list[Evidence],
    gateway: Gateway,
    purpose: str,
    system: str,
    base: dict[str, Any],
    schema: type[BaseModel],
    *,
    fraction: float = 1.0,
) -> tuple[dict[str, Any], bool]:
    remaining = gateway.settings.max_total_tokens - gateway.budget.reserved_tokens
    allowance = int(remaining * fraction)
    cap = gateway.settings.evidence_chars
    count = len(evidence)
    while count:
        packed = [item.model_copy(update={"text": item.text[:cap]}) for item in evidence[:count]]
        payload = {**base, "evidence": evidence_payload(packed)}
        if gateway.reservation(purpose, system, payload, schema) <= allowance:
            changed = count < len(evidence) or any(
                len(item.text) > cap for item in evidence[:count]
            )
            if changed:
                gateway.trace.emit(
                    "evidence_packed",
                    purpose,
                    kept_sources=count,
                    omitted_sources=len(evidence) - count,
                    chars_per_source=cap,
                    reserved_allowance=allowance,
                )
            return payload, changed
        if cap > 256:
            cap = max(256, int(cap * 0.7))
        else:
            count -= 1
    gateway.budget.partial = True
    raise BudgetExceeded("evidence_context")
