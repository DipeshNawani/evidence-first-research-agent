"""CLI: research (Markdown/JSON), trace timeline, API entry point."""

import asyncio
import sys
from io import TextIOWrapper
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from research_agent.config import Settings
from research_agent.renderer import render_markdown
from research_agent.runtime import build_agent
from research_agent.tracing import read_trace

app = typer.Typer(no_args_is_help=True, help="Bounded, source-backed research. Offline by default.")


def configure_console() -> None:
    """Rich emits Unicode; redirected Windows streams may otherwise use cp1252."""
    if sys.platform == "win32":
        for stream in (sys.stdout, sys.stderr):
            if isinstance(stream, TextIOWrapper) and stream in (sys.__stdout__, sys.__stderr__):
                stream.reconfigure(encoding="utf-8")


@app.command()
def research(
    question: str,
    mock: Annotated[bool, typer.Option(help="Force offline fixtures.")] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Emit only final JSON on stdout.")
    ] = False,
    output: Annotated[Path | None, typer.Option(help="Save the final answer as JSON.")] = None,
    scenario: Annotated[
        str, typer.Option(help="Mock fault: timeout, all_fail, injection, spam, pages_fail.")
    ] = "normal",
) -> None:
    configure_console()
    settings = Settings()
    if mock:
        settings.llm_provider = "mock"
    if scenario != "normal" and settings.llm_provider != "mock":
        raise typer.BadParameter("Fault scenarios are available only in mock mode.")

    async def run() -> None:
        async with build_agent(settings, scenario) as agent:
            answer = await agent.research(question)
        if output:
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(answer.model_dump_json(indent=2), encoding="utf-8")
        if json_output:
            typer.echo(answer.model_dump_json(indent=2))
            return
        console = Console()
        events = read_trace(settings.trace_dir, answer.meta.trace_id)
        for event in events:
            if event.event == "plan":
                plan = event.data["plan"]
                console.print("[bold cyan]Plan[/bold cyan]")
                for step in plan["sub_questions"]:
                    console.print(
                        f"  {step['id']}: {step['search_queries']} -> fetch_pages={step['fetch_pages']}",
                        markup=False,
                    )
            if event.event in {
                "tool_end",
                "provider_fallback",
                "security_event",
                "gap_check",
                "citation_verification",
            }:
                console.print(f"{event.event}: {event.data}", markup=False)
        console.print(Markdown(render_markdown(answer)))

    try:
        asyncio.run(run())
    except (ValueError, OSError) as exc:
        typer.echo(
            f"Configuration or storage error: {type(exc).__name__}. Check keys and writable trace directory.",
            err=True,
        )
        raise typer.Exit(1) from None


@app.command()
def trace(trace_id: str) -> None:
    configure_console()
    try:
        events = read_trace(Settings().trace_dir, trace_id)
    except (ValueError, FileNotFoundError):
        raise typer.BadParameter("Trace not found or invalid trace id") from None
    table = Table(title=f"Trace {trace_id}")
    for column in ["Elapsed", "Stage", "Event", "Details"]:
        table.add_column(column)
    origin = events[0].timestamp if events else None
    for event in events:
        elapsed = (event.timestamp - origin).total_seconds() if origin else 0
        table.add_row(f"{elapsed:.3f}s", event.stage, event.event, str(event.data))
    Console().print(table)


if __name__ == "__main__":
    app()
