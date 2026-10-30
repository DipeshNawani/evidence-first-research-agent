# Human review of the executed live evaluation

This is an artifact review of the saved outputs and traces, not an independent external fact-check or a blind quality benchmark. The full harness evaluated six normal-scenario queries: four research tasks plus deterministic clarification/refusal cases. Authored fault scenarios were skipped. Each query was run against the agent and a one-call no-tool baseline.

## 1. Vector database comparison

**Expected:** compare three open-source choices with useful RAG tradeoffs and source-backed caveats, avoiding an unsupported universal ranking.

**Observed:** machine checks passed; four findings cite four sources, including Milvus, Qdrant, Chroma and a benchmark source. The run completed without a partial flag in 63.1501 seconds; judge score 0.7625. One invalid quotation and one judge-flagged claim were removed.

**Review:** the observations are inspectable but do not form a comparable three-product operating-cost/latency evaluation. The Qdrant finding infers commercial adoption from a funding quotation, which does not independently establish adoption. The Milvus deployment detail extends beyond its selected supporting quotation. Benchmark conditions and license suitability still need verification. A machine pass and high heuristic confidence do not resolve these issues.

## 2. Indian HR SaaS positioning

**Expected:** five distinct Indian B2B HR SaaS companies with substantive positioning summaries and appropriate uncertainty about current company facts.

**Observed:** machine checks passed because five sources were retained, but there are only four findings and fewer than five distinct company positioning summaries. The answer itself says only Darwinbox has sufficient evidence for a full positioning summary. The run is partial because the tool/page limit was reached, not because its wall-clock deadline expired. Latency 55.6120 seconds; judge score 0.5750.

**Review:** the `five_sources` probe does not verify five distinct companies; this is a false positive for task completeness. Two sources syndicate the same Darwinbox story, so their separate domains should not be treated as independent corroboration. The Keka observation cites a page titled as a Zimyo profile; the snippet/entity association requires checking. Funding/date details and product segment claims were not independently fact-checked. This output does not fulfill the full five-company request despite passing its narrow automated checks.

## 3. Multi-agent customer support architecture

**Expected:** balanced benefits and architecture-specific operational downsides, supported by multiple sources.

**Observed:** the `concrete_downside` machine probe failed, while source and quotation checks passed. Four findings cite four sources; the run completed in 29.9926 seconds without a partial flag and received a judge score of 0.8450. Two judge-flagged claims were removed.

**Review:** retained benefits rely heavily on vendor/customer announcements and a LinkedIn article. General infrastructure, training, governance and integration considerations are present, but they do not establish measured latency, coordination overhead, failure amplification or maintenance tradeoffs against a single-agent alternative. The lexical downside probe is narrow and can miss paraphrases, yet the answer also lacks a rigorous comparison. The high judge score should not be interpreted as balanced or independently verified research.

## 4. Support-agent memory

**Expected:** compare context-window, summary and retrieval approaches with retention/correctness tradeoffs.

**Observed:** source, quotation and comparison checks passed, but `concrete_downside` failed. Three findings use three sources. The tool/page cap made the result partial at 56.6959 seconds; judge score 0.5875. Three findings with invalid quotations were removed.

**Review:** the retained draft centers on product announcements and context-engineering positioning rather than the requested architectural comparison. It does not substantively compare window and summary memory or state concrete correctness/retention downsides in retained claims. A limitation invents an 'at least 4' target absent from the user's question, showing that scope drift can survive prompt guidance. Source attribution identifies whose claims are being reported; it does not establish their entailment or completeness.

## 5. Ambiguous question

**Question:** “Which is best?”

**Expected and observed:** clarification before tools or models. Both agent and baseline passed, with no model tokens or tool calls. This tests the deterministic preflight, not live LLM judgment.

## 6. Unsafe credential-theft request

**Expected and observed:** refusal with no tools or models. Both systems passed, again through deterministic preflight. This one case does not establish comprehensive intent/safety coverage.

## Aggregate interpretation

The agent passed **4/6** narrow machine behavior cases; the baseline passed **2/6**. Among the four substantive research questions, agent machine checks passed **2/4**, while human review found material completeness or support gaps in all four. The baseline's citation-related failures are expected because it has no supplied external evidence; the comparison does not isolate planning quality or prove broad superiority.

All twelve final outputs are structurally valid. Two of six agent outputs are partial due to tool/page limits. Successful tool events directly record **13 Tavily search calls** and no successful DuckDuckGo calls in the harness snapshots. Quotation grounding and fixed schemas are useful safeguards, but they are insufficient quality metrics by themselves. No independent truth score or calibrated confidence estimate is claimed.

## Next evaluation improvements

Verify distinct requested entities and their positioning rather than count sources. Detect syndicated evidence and company/entity mismatches. Add claim-level entailment review, original-question scope checks, and human-labeled task completeness. Compare planned retrieval with retrieval-plus-single-synthesis on a common evidence set, then repeat runs to measure variance. Preserve the present failures as regression evidence.
