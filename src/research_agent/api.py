"""Minimal local API. Bind to loopback; add auth/rate limiting before public use."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from research_agent.config import Settings
from research_agent.runtime import build_agent
from research_agent.schemas import FinalAnswer, ResearchRequest, TraceEvent
from research_agent.tracing import read_trace


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with build_agent(config) as agent:
            app.state.agent = agent
            yield

    app = FastAPI(title="Research Agent", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "provider": config.llm_provider}

    @app.post("/research", response_model=FinalAnswer)
    async def research(request: ResearchRequest) -> FinalAnswer:
        return await app.state.agent.research(request.question)

    @app.get("/traces/{trace_id}", response_model=list[TraceEvent])
    async def traces(trace_id: str) -> list[TraceEvent]:
        try:
            return read_trace(config.trace_dir, trace_id)
        except (ValueError, FileNotFoundError):
            raise HTTPException(404, "Trace not found") from None

    return app


app = create_app()
