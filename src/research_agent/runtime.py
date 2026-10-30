"""Build dependencies once; cache and provider circuit state survive local API calls."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from research_agent.agent import ResearchAgent
from research_agent.config import Settings
from research_agent.llm.anthropic_client import AnthropicClient
from research_agent.llm.base import LLMClient
from research_agent.llm.mock import MockLLM
from research_agent.llm.nvidia_client import NvidiaClient
from research_agent.llm.openai_client import OpenAIClient
from research_agent.resilience import Resilience
from research_agent.tools.base import ToolRegistry
from research_agent.tools.fetch_page import FetchPage, MockFetch
from research_agent.tools.web_search import DuckDuckGo, MockSearch, Tavily, WebSearch


@asynccontextmanager
async def build_agent(settings: Settings, scenario: str = "normal") -> AsyncIterator[ResearchAgent]:
    resilience = Resilience(settings)
    # Explicitly ignore proxy environment variables: SSRF-pinned fetches must go direct.
    async with httpx.AsyncClient(
        timeout=max(settings.tool_timeout_seconds, settings.llm_timeout_seconds),
        trust_env=False,
        follow_redirects=False,
    ) as http:
        if settings.llm_provider == "mock":
            llm: LLMClient = MockLLM()
            search = MockSearch(settings, resilience, scenario)
            fetch = MockFetch(scenario)
        else:
            keys = {
                "openai": settings.openai_api_key,
                "anthropic": settings.anthropic_api_key,
                "nvidia": settings.nvidia_api_key,
            }
            secret = keys[settings.llm_provider]
            if not secret.get_secret_value():
                raise ValueError(
                    f"RA_{settings.llm_provider.upper()}_API_KEY is required for live mode"
                )
            clients = {"openai": OpenAIClient, "anthropic": AnthropicClient, "nvidia": NvidiaClient}
            llm = clients[settings.llm_provider](http, secret.get_secret_value())
            search = WebSearch(
                [
                    Tavily(http, settings.tavily_api_key.get_secret_value()),
                    DuckDuckGo(settings.tool_timeout_seconds),
                ],
                settings,
                resilience,
            )
            fetch = FetchPage(http, settings)
        yield ResearchAgent(settings, llm, ToolRegistry([search, fetch]), resilience=resilience)
