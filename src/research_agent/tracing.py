"""Redacted per-run JSONL events. Never record full prompts or retrieved bodies."""

import json
import re
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import uuid4

from research_agent.prompts import PROMPT_VERSION
from research_agent.schemas import TraceEvent


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            k: "[REDACTED]"
            if re.search(r"secret|password|api.?key|authorization|cookie", k, re.I)
            else redact(v)
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    if isinstance(value, str):
        value = re.sub(r"(https?://)[^/@\s]+:[^/@\s]+@", r"\1[USERINFO]@", value)
        value = re.sub(
            r"(?i)\b(api[_-]?key|password|token|secret)\s*[:=]\s*[^\s,;&]+", r"\1=[SECRET]", value
        )
        value = re.sub(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", "[EMAIL]", value)
        value = re.sub(r"\b(?:sk-|tvly-|sk-ant-|nvapi-)[A-Za-z0-9_-]+", "[SECRET]", value)
        value = re.sub(r"(?i)(bearer\s+)[^\s]+", r"\1[SECRET]", value)
        return re.sub(
            r"(?i)([?&](?:token|key|secret|signature|password)=)[^&#\s]+", r"\1[SECRET]", value
        )
    return value


class Trace:
    def __init__(self, directory: Path, *, mode: str) -> None:
        self.id = uuid4().hex
        self.directory = directory
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / f"{self.id}.jsonl"
        self.events: list[TraceEvent] = []
        self.stage_latencies: dict[str, float] = {}
        self.emit("run_start", "run", mode=mode, prompt_version=PROMPT_VERSION)

    def emit(self, event: str, stage: str, **data: Any) -> None:
        item = TraceEvent(trace_id=self.id, event=event, stage=stage, data=redact(data))
        self.events.append(item)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(item.model_dump_json() + "\n")

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        started = time.monotonic()
        self.emit("stage_start", name)
        try:
            yield
        finally:
            elapsed = round(time.monotonic() - started, 6)
            self.stage_latencies[name] = self.stage_latencies.get(name, 0) + elapsed
            self.emit("stage_end", name, latency_s=elapsed)


def read_trace(directory: Path, trace_id: str) -> list[TraceEvent]:
    if not re.fullmatch(r"[0-9a-f]{32}", trace_id):
        raise ValueError("Invalid trace id")
    with (directory / f"{trace_id}.jsonl").open(encoding="utf-8") as stream:
        return [TraceEvent.model_validate(json.loads(line)) for line in stream]
