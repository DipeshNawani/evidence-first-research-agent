"""Bounded HTML retrieval. Every redirect is revalidated and DNS-pinned."""

from urllib.parse import urljoin

import httpx
import trafilatura
from pydantic import BaseModel

from research_agent.budget import Budget
from research_agent.config import Settings
from research_agent.fixtures import CORPUS
from research_agent.safety.injection import detect_injection
from research_agent.safety.url_guard import pinned_target
from research_agent.schemas import FetchArgs, PageData
from research_agent.tools.base import ToolError
from research_agent.tracing import Trace


class FetchPage:
    name = "fetch_page"
    args_schema = FetchArgs
    result_schema = PageData
    cache_namespace = "fetch:v1"

    def __init__(self, http: httpx.AsyncClient, settings: Settings) -> None:
        self.http, self.settings = http, settings

    async def run(self, args: BaseModel, *, budget: Budget, trace: Trace) -> PageData:
        url = FetchArgs.model_validate(args.model_dump()).url
        for hop in range(self.settings.max_redirects + 1):
            target, authority, hostname = await pinned_target(url)
            async with self.http.stream(
                "GET",
                target,
                headers={
                    "Host": authority,
                    "User-Agent": "ResearchAgent/0.1 (+assignment prototype)",
                    "Accept-Encoding": "identity",
                },
                extensions={"sni_hostname": hostname},
                follow_redirects=False,
            ) as response:
                if response.status_code in {301, 302, 303, 307, 308}:
                    if hop == self.settings.max_redirects:
                        raise ToolError("redirect_limit")
                    url = urljoin(url, response.headers.get("location", ""))
                    continue
                response.raise_for_status()
                if response.headers.get("content-encoding", "identity").lower() != "identity":
                    raise ToolError("compressed_response_rejected")
                kind = response.headers.get("content-type", "").split(";")[0].lower()
                if kind not in {"text/html", "application/xhtml+xml", "text/plain"}:
                    raise ToolError("content_type")
                raw = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(raw) + len(chunk) > self.settings.max_response_bytes:
                        raise ToolError("response_too_large")
                    raw.extend(chunk)
                html = raw.decode(response.encoding or "utf-8", errors="replace")
                flags = detect_injection(html)
                if flags:
                    trace.emit("security_event", "execute", url=url, flags=flags)
                    raise ToolError("injection_quarantined")
                text = (
                    html
                    if kind == "text/plain"
                    else (
                        trafilatura.extract(html, include_comments=False, include_tables=True) or ""
                    )
                )
                if len(text.strip()) < 40:
                    raise ToolError("empty_output")
                return PageData(
                    url=url,
                    text=text[: self.settings.evidence_chars],
                    truncated=len(text) > self.settings.evidence_chars,
                )
        raise ToolError("redirect_limit")


class MockFetch:
    name = "fetch_page"
    args_schema = FetchArgs
    result_schema = PageData

    def __init__(self, scenario: str = "normal") -> None:
        self.scenario = scenario
        self.cache_namespace = f"fixture-fetch:{scenario}"

    async def run(self, args: BaseModel, *, budget: Budget, trace: Trace) -> PageData:
        url = FetchArgs.model_validate(args.model_dump()).url
        if self.scenario == "pages_fail":
            raise ToolError("http_403")
        for rows in CORPUS.values():
            for _, fixture_url, text in rows:
                if fixture_url == url:
                    return PageData(url=url, text=text)
        raise ToolError("fixture_not_found")
