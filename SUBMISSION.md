# Submission checklist and handoff

This is a local source repository for the AI Research Agent assignment. Start with [README.md](README.md), inspect [the orchestrator](src/research_agent/agent.py), then review [actual evaluation results](EVALUATION.md). The project includes one planner/executor workflow, two tools, a separate optional judge, and a minimal homepage served by the existing FastAPI backend. Follow-up conversation memory is outside this implementation.

## Commands

For the approved browser demonstration, run `.\.venv\Scripts\python.exe -m research_agent.cli demo` from the repository root. It opens the homepage automatically. Use `demo --mock --port 8001` for an isolated offline demo. The updated recording walkthrough is in `DEMO_SCRIPT.md`.

After installing `.[dev]` into an activated Python 3.11+ virtual environment:

```sh
make test
make lint
make eval
make demo
make serve
research-agent research "Compare vector databases for a startup RAG product." --mock --scenario timeout --output answer.json
research-agent trace TRACE_ID
```

Windows without activation: `.\.venv\Scripts\make.exe test PYTHON=.venv/Scripts/python.exe`, with `lint`, `eval`, and `demo` as the other targets. Portable equivalents use `python scripts/tasks.py <target>`. Reproduce locked dependencies with `uv sync --extra dev --frozen`. Refresh the evaluation narrative with `python scripts/write_eval_report.py`. Create a clean source archive with `python scripts/package_submission.py`.

## Requirement-to-code checklist

| Requirement | Implementation / evidence |
| --- | --- |
| Working agentic workflow; visible bounded plan | `agent.py`, `pipeline/planner.py`, `pipeline/collector.py`; plan events and CLI |
| Two tools with typed arguments/results and registry | `tools/base.py`, `web_search.py`, `fetch_page.py`, `schemas.py` |
| Handwritten planner/executor; no LangChain/LangGraph | `pipeline/executor.py`, `agent.py`; rationale in README Q1/Q7 |
| Python 3.11+, Pydantic v2, async HTTP, pytest, Ruff, Make | `pyproject.toml`, `uv.lock`, `Makefile`, `.env.example`, `.gitignore` |
| OpenAI default live integration, Claude alternative, protocol | `llm/base.py`, `openai_client.py`, `anthropic_client.py`, `runtime.py`; mock is safe execution default |
| NVIDIA-hosted Nemotron alternative | `llm/nvidia_client.py`, `RA_NVIDIA_*` settings, `tests/test_nvidia.py`; JSON mode with local schema validation |
| Native structured outputs; local validation and repair | `llm/gateway.py`, provider schema adapters, `tests/test_providers.py` |
| Offline model/search/page fixtures | `llm/mock.py`, `fixtures.py`, `MockSearch`, `MockFetch`; no keys needed |
| Plan fields, question types, criteria, assumptions, stop condition | `schemas.Plan`, `SearchStep`, `pipeline/planner.py` |
| Vague, unsafe, out-of-scope, unknowable early exits | `pipeline/planner.py:early_exit`, regression tests; explicitly heuristic |
| Tavily search with independent fallback | `tools/web_search.py`; provider timeout/429/malformed tests |
| Async bounded concurrency, global run budgets | `pipeline/executor.py`, `budget.py`, `pipeline/collector.py` |
| Timeouts, transient retry/backoff/jitter, no 4xx retry | `resilience.py`, `tests/test_faults.py` |
| Provider/tool circuits and retry/fallback accounting | `Resilience`, `WebSearch`, `Budget`; traces and tests |
| Malformed/empty output becomes a recorded gap | `Executor`, tool result schemas, collection gap events |
| At most one adaptive gap round | `pipeline/collector.py`, `Settings.max_rounds <= 2` |
| Live-run regressions: fast dedupe, context packing, quote repair | `pipeline/context.py`, `filter.py`, `review.py`, `tests/test_live_regressions.py`; NVIDIA smoke report |
| Relevance/domain/recency/length scoring | `pipeline/filter.py:score_source`; weights and caveats in README |
| URL and near-text deduplication; drop reasons | `pipeline/filter.py`, `DroppedSource`, trace events |
| HTML extraction and bounded text | `FetchPage`, trafilatura, `evidence_chars`, byte/redirect/type limits |
| Fixed final schema and JSON/Markdown output | `schemas.FinalAnswer`, `renderer.py`, CLI `--json` |
| Finding citations and supporting snippets | `Finding`, synthesis prompt; samples and verifier tests |
| Citation grounding; bad findings removed | `pipeline/verifier.py`; positive, fabricated quote and missing-ID tests |
| No uncited free-form summary/comparison bypass | Verifier rebuilds both from retained findings; conservative comparison column |
| Separate judge and one bounded revision | `pipeline/judge.py`, `pipeline/review.py`; failure/revision tests |
| Deterministic confidence with explicit factors | `pipeline/confidence.py`; monotonic signal tests and README formula |
| Low-confidence guardrails | `agent.py`; mock cap, hedged short answer, verification next steps |
| Injection awareness, untrusted boundaries, quarantine | `safety/injection.py`, raw HTML checks, filter, versioned prompts; spy test proves fixture absent from model evidence |
| SSRF defense including DNS/redirect checks | `safety/url_guard.py`, pinned HTTP connection, no environment proxy; mixed DNS/private redirect tests |
| Common-secret/PII log redaction; env-only credentials | `tracing.py`, `Settings` SecretStr; redaction tests; limitations documented |
| TTL caching | `cache.py`, executor, repeated-run tests including stable retrieval timestamps |
| Trace IDs, stages, tools, LLM tokens/cost/latency, security | `tracing.py`, gateway/executor, source-kept/dropped events, sample JSONL traces |
| Trace timeline and per-stage summary | CLI `trace`, `AnswerMeta.stage_latency_s`, renderer |
| CLI and local HTTP endpoints | `cli.py`, `api.py`; `/research`, `/health`, `/traces/{trace_id}` tests |
| At least 8 queries and 5-query evaluation narrative | 12 cases in `eval/queries.yaml`; generated results and `EVALUATION.md` |
| Agent vs single-call no-tool baseline | `baseline.py`, `eval/run_eval.py`; comparison caveats explicit |
| Structured, grounding, quality, cost/latency and recovery metrics | `eval/run_eval.py:Metrics`; per-row JSON and Markdown table |
| Actual runs, honest mock labels, no fabricated metrics | `eval/results/mock/`, generated `EVALUATION.md`, `samples/`; live handoff section |
| Unit, integration, fault and security tests | `tests/`; offline suite covers all pipeline stages and interfaces |
| Seven required README Q&A headings | README sections 1-7, plus failure matrix/security/cost/roadmap |
| 3-5 minute video script and exact commands | `DEMO_SCRIPT.md`: happy path, timeout fallback, abstention, trace timeline |
| 2-3 executed sample outputs | Three JSON + Markdown pairs and trace snapshots in `samples/` |
| Clean setup and source handoff | Editable install, frozen lockfile, portable task runner, source archive script |

## Verification

The build was verified on Windows with Python 3.13.15. The expanded offline suite passes **88 tests**. Ruff and Pyright checks pass. The mock evaluation produces **24 valid final outputs**, agent checks **10/12**, baseline checks **4/12**. Two semantic-completeness checks fail for the intentionally first-sentence extractive mock; see EVALUATION.md. The suite currently emits one third-party Starlette/httpx deprecation warning. Executed NVIDIA checks and their limitations are preserved in `eval/results/approved-upgrade/REPORT.md`.

Additional clean-install, browser and local HTTP smoke-check results are recorded in `VERIFICATION.md`. The source archive excludes credentials, virtual environments, ignored run traces, caches and temporary verification directories. It includes selected sample and live-check redacted trace snapshots.

## Assumptions and outstanding handoff

- Offline fixtures are authored illustrations, not independently researched facts. The `samples/` and `eval/results/mock/` artifacts are mock executions. Separate NVIDIA runs under `eval/results/nvidia-smoke/` and `eval/results/approved-upgrade/` exercise real credentials and document quality/latency limitations; they are not an accuracy benchmark.
- Confidence is a documented heuristic, not a calibrated probability. Quote matching does not establish semantic entailment, truth, balance or source independence. The two failed quality probes demonstrate that distinction.
- Comparisons publish a conservative supported-observation column; richer multi-criteria cell citations remain future work.
- Security controls are meaningful but incomplete: heuristics can miss novel injection or unsafe intent, log redaction is not full DLP, and the API needs auth/admission control and an egress boundary before public exposure.
- The Python syntax targets 3.11+, but local execution was on 3.13; a cross-version CI matrix remains a recommended next step.
- No follow-up memory, public deployment, hosted Git remote, recorded demo video or video upload was created. The source, demonstration script, setup instructions, samples and evaluation are ready; recording/uploading the video and sharing the repository link are final submission handoff tasks.

## Repository tree

The complete generated file inventory is [REPO_TREE.txt](REPO_TREE.txt). Main structure:

```text
predictionaiproj/
  README.md, EVALUATION.md, DEMO_SCRIPT.md, SUBMISSION.md, VERIFICATION.md
  pyproject.toml, uv.lock, pyrightconfig.json, Makefile, .env.example, .gitignore
  src/research_agent/
    agent.py, config.py, schemas.py, runtime.py, prompts.py
    budget.py, cache.py, resilience.py, tracing.py, baseline.py, fixtures.py
    cli.py, api.py, renderer.py, demo.py
    web/         index.html, style.css, app.js
    llm/         base.py, gateway.py, openai_client.py, anthropic_client.py, nvidia_client.py, mock.py
    tools/       base.py, web_search.py, fetch_page.py
    safety/      injection.py, url_guard.py
    pipeline/    planner.py, executor.py, collector.py, filter.py, synthesizer.py
                 verifier.py, judge.py, review.py, confidence.py
  tests/         schemas, tools, pipeline, HTTP faults, guards, interfaces, providers, eval
  eval/          queries.yaml, run_eval.py, results/mock/{results.json,summary.md}
  samples/       {vector,hr_saas,failure}.{json,md,trace.jsonl}
  scripts/       tasks.py, write_eval_report.py, package_submission.py
```
