# Approved upgrade: executed NVIDIA checks

Executed locally on 30 October 2026 using the configured NVIDIA Nemotron provider and real web search. These are integration/regression observations from four runs, not a benchmark or a guarantee of factual accuracy. JSON, Markdown and redacted JSONL traces are stored beside this report. No API keys are included. Unconfigured pricing stays unknown.

## Initial checks

- `biography-initial`: completed in 15.0753 seconds, 4 retained findings, 1 source, 3,884 reported tokens, judge score 0.9325, no partial flag. Trace `716a83f700e54bc786fde8b5cb1d2405`.
- `memory-initial`: completed in 65.6106 seconds, 6 findings, 4 sources, 12,543 reported tokens, judge score 0.7875, no partial flag. Trace `d638b87e478941ea83c41195c6fcf32b`.

Manual inspection found overly broad secondary-source claims and uncited synthesis assumptions despite the judge score. This prompted explicit source-domain attribution for live findings and removal of synthesis assumptions from final answers. These initial files preserve the actual earlier output, not the final presentation policy.

## Follow-up checks with source attribution

- `biography`: completed in 68.7884 seconds, 3 findings, 1 source, 3,733 reported tokens, judge 0.9325, no partial flag. Trace `10dbba6b27434523ae7a3fcbcf1f9117`. All retained claims were explicitly attributed to `kids.britannica.com`; the source was available as search snippets. Search/fetch failures explain some of the additional latency. Confidence remained medium, and only the brief deterministic scope assumption was retained.
- `memory`: returned a valid partial draft at 100.0211 seconds, with 6 findings, 5 sources, 12,203 reported tokens, judge 0.7175. Trace `c9e9ef716a7f473c80e7fabdfb0a3038`. The optional revision consumed the remaining wall-clock budget. The UI/API correctly exposes `partial: true` and the budget limitation. Quote grounding was 1.0, which does not establish semantic entailment or completeness.

Manual review still found misleading model-written scope language, including an unrequested five-item target and historical-date assumption. The final code now uses application-owned scope assumptions for live plans, reinforces original-question scope in synthesis, and skips optional revision unless time for two full model-call allowances remains. The added time check and live presentation path passed the offline regression suite; no additional live run was made after those final two guard changes. The follow-up files remain unchanged records of the observed run.

## Interpretation

The upgrade preserves valid findings from a mixed-validity response, releases unused token reservations after known usage, handles short identity questions with a brief plan, and avoids treating an ordinary discussion of system prompts as an injection command. Unit and integration tests cover those boundaries.

Research quality remains provisional. Domain reputation, quote presence and model judging are imperfect signals. Secondary-source marketing, missing head-to-head benchmarks, search snippets, scope drift and provider latency still require human review. Configured wall-clock and token limits can produce partial results. The original 100-second local limit was preserved; no credentials or user budget settings were rewritten.
