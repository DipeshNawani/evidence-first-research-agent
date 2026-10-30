# NVIDIA live integration check

This is an actual live run with `nvidia/nemotron-3-ultra-550b-a55b`, not a mock. The trace began at 2026-10-29 18:51 UTC (30 October, 00:21 IST). The question was: "Compare the top 3 open-source vector databases for a startup building RAG products."

## Integration result

- Application status: `completed`; partial: `false`.
- Total recorded latency: **49.5872 seconds**.
- Retained findings: **5**, from **4** cited sources.
- Quote-grounding rate before failed findings were removed: **5/6 = 83.33%**.
- Retained findings all have quotations found in their remaining cited source text.
- One finding was removed because its quotation did not verify; one individual unsupported citation was also removed.
- Reported model tokens: **8,537**, across planning, synthesis and judging.
- Conservative token reservations: **31,637 / 32,000**.
- Recorded judge score: **0.45**; an optional revision was skipped for insufficient token headroom.
- Estimated model cost: unknown because pricing rates were not configured.

Evidence: [raw answer JSON](answer.json), [readable draft](answer.md), and [redacted trace](trace.jsonl).

## Quality assessment: provisional draft

This run proves the NVIDIA API connection and full application workflow work. It **does not demonstrate a high-quality research answer**. The judge rated the answer poorly; several claims are broader than their supporting quotations. For example, a claim about all three databases' framework integrations cites an excerpt about Astra DB. Another ranking claim uses a short excerpt that does not substantiate a current adoption ranking. Do not treat these statements as verified facts merely because the quotations occur in source text.

The sources were mainly articles, vendor comparisons and snippets, rather than comparable independent benchmarks. Evidence packing shortened context. More source-specific research, richer supporting passages and claim-entailment evaluation remain needed for a strong database recommendation.

The raw recorded output reports heuristic confidence **0.7768 (medium)**. Those numbers are preserved exactly. This live failure motivated a subsequent deterministic guardrail: available judge scores below 0.5 now cap confidence at 0.54, trigger low-confidence wording, and add an explicit quality limitation. The guardrail was regression-tested; this saved live run predates that final guardrail and was not silently relabeled as a new API run.

## Earlier observed failures and fixes

Three preceding live outputs are preserved in [earlier-failures.json](earlier-failures.json):

1. A **100.0204-second** run exhausted wall time after expensive source comparison and retrieval. Replaced character alignment with bounded word-shingle hashes, narrowed the default query count, and reserved time before starting another gap round.
2. A **22.7831-second** run exceeded the conservative request-token allowance. Added budget-aware evidence packing, a smaller judge output cap, and optional-revision headroom checks.
3. A **51.4017-second** run generated a model draft but all five findings failed quotation verification. Added literal source-derived citation options and one bounded citation-repair path. Unsupported references are pruned; findings with no valid citation remain rejected.

The final trace records **0.072084 seconds** accumulated in filtering, with different retrieved inputs from the earlier attempts; this is an observed run measurement, not a controlled performance benchmark.

## Verification after fixes

The offline suite passed **77 tests**. It covers long/repeated-text deduplication, missing-subquestion retrieval, date/budget-aware planning, evidence packing, literal quote options, invalid-citation pruning, bounded citation repair, and the low-judge confidence cap. The existing 12-case mock evaluation continues to expose its two known extractive-mock completeness failures.

This single live integration run is separate from the full agent-versus-baseline live evaluation, which has not been executed. No broad live accuracy, calibration, pricing, or reliability claims follow from one example.
