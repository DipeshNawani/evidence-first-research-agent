"""Deterministic extractive model; validates plumbing, not model intelligence."""

import json
from typing import Any

from pydantic import BaseModel

from research_agent.fixtures import topic_for
from research_agent.schemas import LLMResponse


class MockLLM:
    def __init__(self, *, invalid_calls: int = 0, low_judge_once: bool = False) -> None:
        self.invalid_calls = invalid_calls
        self.low_judge_once = low_judge_once
        self.calls: list[str] = []

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
        self.calls.append(purpose)
        payload = json.loads(user)
        if self.invalid_calls:
            self.invalid_calls -= 1
            text = "{broken-json"
        else:
            data = self._data(purpose, payload)
            text = json.dumps(data)
        return LLMResponse(
            text=text,
            model="mock-extractive-v1",
            input_tokens=len(user) // 4,
            output_tokens=len(text) // 4,
        )

    def _data(self, purpose: str, payload: dict[str, Any]) -> dict[str, Any]:
        question = payload.get("question", "")
        if purpose == "plan":
            topic = topic_for(question)
            kind = {
                "vector": "comparison",
                "hr": "list_finding",
                "multi": "pros_cons",
                "memory": "comparison",
            }.get(topic or "", "survey")
            return {
                "restated_question": question,
                "question_type": kind,
                "sub_questions": [
                    {
                        "id": "q1",
                        "question": question,
                        "tool": "web_search",
                        "search_queries": [question],
                        "fetch_pages": True,
                        "rationale": "Discover primary sources and read the strongest candidates.",
                    },
                    {
                        "id": "q2",
                        "question": "Check limitations and operational tradeoffs",
                        "tool": "web_search",
                        "search_queries": [question + " limitations operational tradeoffs"],
                        "fetch_pages": True,
                        "rationale": "Look for counter-evidence and deployment constraints.",
                    },
                ],
                "success_criteria": [
                    "Address the requested items",
                    "Cite supporting text",
                    "Explain evidence gaps",
                ],
                "assumptions": [
                    "Offline fixture run; these are authored examples, not current web research."
                ],
                "stop_condition": "Stop after two rounds or when every sub-question has two sources.",
            }
        if purpose == "judge":
            low = self.low_judge_once
            self.low_judge_once = False
            score = 0.4 if low else 0.82
            return dict(
                faithfulness=score,
                completeness=score,
                source_quality=score,
                clarity=score,
                issues=["Add explicit caveats"] if low else [],
            )
        if purpose == "baseline":
            return dict(
                short_answer="Mock baseline has no tools or evidence; a current factual answer cannot be established.",
                key_findings=[],
                comparison_table=None,
                assumptions=["Single-call, no-tool mock baseline."],
                limitations=["No external evidence available."],
                suggested_next_steps=["Retrieve primary sources."],
            )
        evidence = payload.get("evidence", [])
        for item in evidence:
            item["text"] = (
                item["text"]
                .removeprefix("<untrusted_evidence>")
                .removesuffix("</untrusted_evidence>")
            )
        findings = [
            dict(
                claim=e["text"].split(". ")[0] + ".",
                source_ids=[e["source"]["id"]],
                supporting_quote=e["text"].split(". ")[0] + ".",
                verified=False,
            )
            for e in evidence
        ]
        comparison = None
        if payload.get("question_type") == "comparison" and findings:
            comparison = {
                "columns": ["Evidence-backed observation"],
                "rows": [
                    {
                        "item": e["source"]["title"],
                        "cells": [f["claim"]],
                        "source_ids": f["source_ids"],
                    }
                    for e, f in zip(evidence, findings, strict=True)
                ],
            }
        return dict(
            short_answer=" ".join(f["claim"] for f in findings),
            key_findings=findings,
            comparison_table=comparison,
            assumptions=[
                "Authored mock corpus; observations are not independently researched facts."
            ],
            limitations=[
                "Offline fixtures do not establish current rankings or real model quality."
            ],
            suggested_next_steps=[
                "Repeat with live providers and benchmark against your workload."
            ],
        )
