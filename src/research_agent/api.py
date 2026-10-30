"""Minimal local API. Bind to loopback; add auth/rate limiting before public use."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles

from research_agent.cache import TTLCache
from research_agent.config import Settings
from research_agent.renderer import render_markdown
from research_agent.runtime import build_agent
from research_agent.schemas import FinalAnswer, HealthResponse, ResearchRequest, TraceEvent
from research_agent.tracing import read_trace


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    answers = TTLCache(config.result_ttl_seconds, config.max_saved_results)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with build_agent(config) as agent:
            app.state.agent = agent
            yield

    app = FastAPI(title="Research Agent", version="0.1.0", lifespan=lifespan)
    web_directory = Path(__file__).parent / "web"
    app.mount("/static", StaticFiles(directory=web_directory), name="static")

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def homepage() -> HTMLResponse:
        return HTMLResponse(
            (web_directory / "index.html").read_text(encoding="utf-8"),
            headers={
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'"
            },
        )

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/health")
    async def health() -> HealthResponse:
        return HealthResponse(
            provider=config.llm_provider,
            model="Authored fixtures" if config.llm_provider == "mock" else config.model,
            max_wall_seconds=config.max_wall_seconds,
        )

    @app.post("/research", response_model=FinalAnswer)
    async def research(request: ResearchRequest) -> FinalAnswer:
        if request.scenario != "normal" and request.mode != "mock":
            raise HTTPException(422, "Failure demonstrations require offline mock mode.")
        if request.mode == "mock":
            offline = config.model_copy(update={"llm_provider": "mock", "retry_base_seconds": 0})
            async with build_agent(offline, request.scenario) as agent:
                answer = await agent.research(request.question)
        else:
            answer = await app.state.agent.research(request.question)
        answers.put(answer.meta.trace_id, answer.model_dump(mode="json"))
        return answer

    @app.get("/exports/{trace_id}/{format}", include_in_schema=False)
    async def export_answer(trace_id: str, format: str) -> Response:
        if format not in {"json", "markdown"}:
            raise HTTPException(404, "Unknown export format")
        payload = answers.get(trace_id)
        if payload is None:
            raise HTTPException(404, "Result expired or server restarted. Run the question again.")
        answer = FinalAnswer.model_validate(payload)
        extension = "json" if format == "json" else "md"
        headers = {
            "Content-Disposition": f'attachment; filename="research-{answer.meta.trace_id[:8]}.{extension}"',
            "Cache-Control": "no-store",
        }
        if format == "json":
            return JSONResponse(payload, headers=headers)
        return PlainTextResponse(render_markdown(answer), headers=headers)

    @app.post("/render/markdown", response_class=PlainTextResponse)
    async def markdown(answer: FinalAnswer) -> str:
        return render_markdown(answer)

    @app.get("/traces/{trace_id}", response_model=list[TraceEvent])
    async def traces(trace_id: str) -> list[TraceEvent]:
        try:
            return read_trace(config.trace_dir, trace_id)
        except (ValueError, FileNotFoundError):
            raise HTTPException(404, "Trace not found") from None

    return app


app = create_app()
