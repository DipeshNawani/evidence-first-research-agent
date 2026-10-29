"""Authored fixture corpus, NOT retrieved facts. Never used in live mode."""

from research_agent.schemas import SearchHit

CORPUS: dict[str, list[tuple[str, str, str]]] = {
    "vector": [
        (
            "Qdrant",
            "https://qdrant.tech/documentation/",
            "Qdrant combines vector search with payload filtering. For a startup RAG product, evaluate filter selectivity and operational simplicity on your own corpus. Self-hosting still requires backups, monitoring and capacity planning; no universal top-three ranking follows from this fixture.",
        ),
        (
            "Weaviate",
            "https://docs.weaviate.io/weaviate",
            "Weaviate supports hybrid keyword and vector search. Its integration surface can help a startup building RAG products, while additional modules introduce configuration and operational choices. Benchmark retrieval relevance, memory use and recovery behavior before selecting an open-source vector database.",
        ),
        (
            "Milvus",
            "https://milvus.io/docs",
            "Milvus offers distributed vector retrieval for larger workloads. A startup should compare its scaling flexibility with the operational complexity of distributed components. For RAG products, measure latency, filtering and recovery on a representative dataset rather than accepting a generic database ranking.",
        ),
    ],
    "hr": [
        (
            "Darwinbox",
            "https://darwinbox.com/",
            "Darwinbox is positioned as an enterprise human capital management platform. In this Indian B2B SaaS HR tech fixture, its positioning spans employee lifecycle workflows. Verify headquarters, current modules and target segment directly before treating this as a current company profile.",
        ),
        (
            "Keka",
            "https://www.keka.com/",
            "Keka is positioned around HR and payroll software for businesses. This Indian B2B SaaS HR tech fixture highlights payroll and employee operations as a positioning lens. Current geography, customer segment and pricing require independent confirmation.",
        ),
        (
            "greytHR",
            "https://www.greythr.com/",
            "greytHR is positioned around payroll and core HR workflows. In this Indian B2B SaaS HR tech fixture, compliance and employee administration are the comparison criteria. Verify incorporation, headquarters and product scope with current primary sources.",
        ),
        (
            "Zimyo",
            "https://www.zimyo.com/",
            "Zimyo is positioned as an HR management software suite. This Indian B2B SaaS HR tech fixture uses employee operations and engagement as its positioning summary. Current company status and feature availability remain unverified in offline mode.",
        ),
        (
            "HROne",
            "https://hrone.cloud/",
            "HROne is positioned around unified HR operations software. This Indian B2B SaaS HR tech fixture describes employee lifecycle and payroll positioning. Validate present-day product claims, headquarters and commercial terms before making a shortlist.",
        ),
    ],
    "multi": [
        (
            "Agent orchestration reference",
            "https://docs.example.org/multi-agent",
            "Multi-agent customer support architectures can separate specialist tasks and tools. That specialization introduces coordination latency and additional failure boundaries. Compare task success and escalation quality against a single agent before introducing more agents for support automation.",
        ),
        (
            "Agent reliability study",
            "https://arxiv.org/abs/2401.00001",
            "Multi-agent customer support automation requires explicit handoff contracts and shared state ownership. Extra model calls increase latency and cost, while isolated permissions can limit tool access. This authored fixture is not a real paper and cannot establish empirical performance benefits.",
        ),
        (
            "Support workflow guide",
            "https://github.com/example/support-workflow",
            "A single orchestrator can route customer support tasks to bounded specialist agents. Human escalation remains necessary when tools fail or evidence is insufficient. Multi-agent pros and cons should be measured with end-to-end task completion rather than the number of agents.",
        ),
    ],
    "memory": [
        (
            "Context memory guide",
            "https://docs.example.org/context-memory",
            "Conversation-window memory keeps recent support dialogue directly in model context. It is simple to inspect but grows token cost and loses older context at the window boundary. Compare it with summaries and retrieval memory for an AI support agent under a fixed latency budget.",
        ),
        (
            "Summary memory guide",
            "https://github.com/example/summary-memory",
            "Summary memory compresses earlier support interactions into a smaller context. Compression can omit exceptions or preserve stale facts, so record provenance and allow correction. Evaluate customer intent retention and factual consistency when adding memory to an AI support agent.",
        ),
        (
            "Retrieval memory guide",
            "https://arxiv.org/abs/2402.00002",
            "Retrieval memory selects stored support records relevant to the current request. It requires access control, retention limits and retrieval evaluation to avoid stale or cross-user information. This authored fixture illustrates tradeoffs and is not evidence of a real paper's conclusions.",
        ),
    ],
}


def topic_for(question: str) -> str | None:
    text = question.lower()
    if "vector" in text or "rag" in text:
        return "vector"
    if "hr tech" in text or "hrtech" in text or "saas" in text:
        return "hr"
    if "multi-agent" in text or "multi agent" in text:
        return "multi"
    if "memory" in text:
        return "memory"
    return None


def fixture_hits(query: str) -> list[SearchHit]:
    return [
        SearchHit(title=title, url=url, snippet=text)
        for title, url, text in CORPUS.get(topic_for(query) or "", [])
    ]
