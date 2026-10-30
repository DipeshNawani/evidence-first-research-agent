# Compare approaches to adding memory in an AI support agent.

**LIVE RESEARCH**

Four distinct memory architectures have emerged: flat vector stores (Mem0, Zep), episodic page-in/page-out systems (Letta, MemGPT), knowledge-graph-backed stores (GraphRAG on Neo4j or TypeDB), and hybrid combinations. Vector databases retrieve semantically similar content via embedding search: fast, zero cold-start, and excellent for unstructured recall. Knowledge graphs traverse explicit entity relationships: deterministic, multi-hop, and explainable. Episodic systems use a context-resident working memory with long-term records in an external vector or structured store, but suffer from attentional dilution within the context window. Hybrid AI agents blend LLM generative responses with knowledge-graph-backed curated knowledge, enabling human-governed delivery alongside real-time generation.

**Confidence:** high (0.87; heuristic, not probability)

## Key findings

- Four distinct memory architectures have emerged: flat vector stores (Mem0, Zep), episodic page-in/page-out systems (Letta, MemGPT), knowledge-graph-backed stores (GraphRAG on Neo4j or TypeDB), and hybrid combinations. [S2; verified quote]
  > In the last twelve months, four distinct memory architectures have settled out of the noise: flat vector stores (Mem0, Zep), episodic page-in/page-out systems (Letta, MemGPT), knowledge-graph-backed stores (graph-RAG on Neo4j or TypeDB), and hybrid combinations that stitch two or three together.
- Vector databases retrieve semantically similar content via embedding search: fast, zero cold-start, and excellent for unstructured recall. [S1; verified quote]
  > Vector databases retrieve semantically similar content via embedding search: fast, zero cold-start, and excellent for unstructured recall.
- Knowledge graphs traverse explicit entity relationships: deterministic, multi-hop, and explainable. [S1; verified quote]
  > Knowledge graphs traverse explicit entity relationships: deterministic, multi-hop, and explainable.
- Episodic systems use a context-resident working memory with long-term records in an external vector or structured store, but suffer from attentional dilution within the context window. [S4; verified quote]
  > A less obvious but equally important limitation of context-resident memory is attentional dilution.
- Hybrid AI agents blend LLM generative responses with knowledge-graph-backed curated knowledge, enabling human-governed delivery alongside real-time generation. [S5; verified quote]
  > With this blended Hybrid AI Agent, enterprises and AI Agent builders can now leverage kama.ai's human-governed knowledge delivery alongside real-time LLM generative responses.
- Forgetting policies are under-evaluated; only MemoryAgentBench tests selective forgetting explicitly, and inability to discard outdated information gradually poisons retrieval precision. [S4; verified quote]
  > Nobody evaluates forgetting well. Only MemoryAgentBench tests selective forgetting explicitly. Yet in any long-running deployment, the inability to discard outdated information gradually poisons retrieval precision.

## Comparison

| Item | Supported observation | Sources |
| --- | --- | --- |
| Agent Memory Architectures: Vector vs Graph vs Episodic | Four distinct memory architectures have emerged: flat vector stores (Mem0, Zep), episodic page-in/page-out systems (Letta, MemGPT), knowledge-graph-backed stores (GraphRAG on Neo4j or TypeDB), and hybrid combinations. | S2 |
| Vector Database vs Knowledge Graph: Choosing for Agent Memory | Vector databases retrieve semantically similar content via embedding search: fast, zero cold-start, and excellent for unstructured recall. | S1 |
| Vector Database vs Knowledge Graph: Choosing for Agent Memory | Knowledge graphs traverse explicit entity relationships: deterministic, multi-hop, and explainable. | S1 |
| Memory for Autonomous LLM Agents:Mechanisms, Evaluation, and Emerging Frontiers | Episodic systems use a context-resident working memory with long-term records in an external vector or structured store, but suffer from attentional dilution within the context window. | S4 |
| Bringing Trust to AI: kama.ai Introduces GenAI’s Sober Second Mind® and Knowledge Administrator | Hybrid AI agents blend LLM generative responses with knowledge-graph-backed curated knowledge, enabling human-governed delivery alongside real-time generation. | S5 |
| Memory for Autonomous LLM Agents:Mechanisms, Evaluation, and Emerging Frontiers | Forgetting policies are under-evaluated; only MemoryAgentBench tests selective forgetting explicitly, and inability to discard outdated information gradually poisons retrieval precision. | S4 |

## Sources

- [S1] [Vector Database vs Knowledge Graph: Choosing for Agent Memory](https://atlan.com/know/vector-database-vs-knowledge-graph-agent-memory) - quality 0.74; page; retrieved 2026-10-30T03:53:18.799329+00:00
- [S2] [Agent Memory Architectures: Vector vs Graph vs Episodic](https://www.digitalapplied.com/blog/agent-memory-architectures-vector-graph-episodic) - quality 0.68; page; retrieved 2026-10-30T03:53:18.942902+00:00
- [S4] [Memory for Autonomous LLM Agents:Mechanisms, Evaluation, and Emerging Frontiers](https://arxiv.org/html/2603.07670v1) - quality 0.64; snippet; retrieved 2026-10-30T03:53:22.661870+00:00
- [S5] [Bringing Trust to AI: kama.ai Introduces GenAI’s Sober Second Mind® and Knowledge Administrator](https://finance.yahoo.com/news/bringing-trust-ai-kama-ai-170100880.html) - quality 0.60; snippet; retrieved 2026-10-30T03:53:18.181272+00:00

## Assumptions

- Benchmarks cited (Mem0, MemoryAgentBench) are vendor-reported or limited-scope; independent reproduction not verified.
- Privacy controls depend on specific deployment (self-hosted vs managed) and are not fully detailed in sources.
- Cost figures (90% token reduction, \<2s latency) come from Mem0 benchmarks via Valkey blog; real-world variance expected.
- Focus is on LLM-driven support agents (not rule-based bots).
- Evidence limited to publicly available documentation, blog posts, and papers up to 2026-10-30.
- Maximum of 6 fetched pages across all sub-questions.

## Limitations

- Sources do not provide head-to-head latency/cost numbers across all four architectures under identical workloads.
- Forgetting/eviction policies are noted as under-evaluated; no quantitative comparison available.
- Privacy and security details are mentioned but not specified per architecture.
- Evidence context was shortened to fit the model token budget; some source detail was omitted.
- The model judge flagged and removed 2 claim(s) not adequately supported by their cited evidence.
- Fetched evidence was truncated to the configured character budget; later context may be missing.
- Some sources were unavailable as full pages; search snippets were used where sufficient.
- Dropped 6 sources: evidence_budget, low_quality_or_relevance, near_duplicate_text.

## Suggested next steps

- Run controlled benchmarks comparing vector, episodic, graph, and hybrid stores on representative support-agent workloads (multi-turn, policy-constrained, long-horizon).
- Evaluate forgetting/eviction strategies (TTL, importance scoring, human-in-the-loop) with MemoryAgentBench or custom evals.
- Map data-governance requirements (PII, access control, audit) to each architecture's native controls and supplement with infrastructure-level controls.
- Prototype hybrid retrieval (vector + graph + episodic) for a high-value support use case and measure integration effort vs. reasoning quality gains.

## Run summary

Trace `d638b87e478941ea83c41195c6fcf32b` · 65.611s · 10 tool attempts · 12543 reported tokens · estimated model cost unknown (rates not configured) · partial: False

Stage latency: understand 0.001s, plan 12.694s, execute 6.317s, filter 0.062s, synthesize 40.998s, verify 0.005s, judge 5.527s, confidence 0.001s
