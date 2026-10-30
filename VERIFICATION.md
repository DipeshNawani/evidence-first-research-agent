# Executed verification

Local execution used Windows and Python 3.13.15. The project targets Python 3.11+ syntax. Commands below include Windows PowerShell and macOS/Linux forms; the latter are compatibility instructions, not a claim that a separate macOS/Linux runtime was tested.

## Offline checks and packaging

- The current offline suite has **88 passing tests**, with one third-party Starlette/httpx deprecation warning.
- Ruff check/format and Pyright passed in the recorded verification. The latest checks are rerun for this documentation/evidence update.
- The mock harness retains **24 valid final outputs**, with **10/12** agent behavior cases and **4/12** baseline cases. Two known completeness failures remain visible in EVALUATION.md.
- Initial installation used an isolated development environment and `uv.lock`. An independently installed clean source copy passed its original 61-test suite at that stage; that historical clean-install check predates the expanded 88-test suite.
- Wheel inspection confirmed inclusion of the local homepage HTML, CSS and JavaScript. The source packager includes reviewer documentation and screenshots while excluding credentials, runtime state, caches, temporary directories and local recording notes.

From the repository root, Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/tasks.py lint
.\.venv\Scripts\python.exe scripts/package_submission.py
npx --yes pyright
uv build --wheel
```

macOS / Linux:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/tasks.py lint
.venv/bin/python scripts/package_submission.py
npx --yes pyright
uv build --wheel
```

On either platform, `uv sync --extra dev --frozen` reproduces the locked development dependencies. Make is optional because the portable task runner invokes the same Python tasks. Uncertain or timed-out model attempts retain their token reservation; known successful usage settles to reported tokens.

## Browser and HTTP evidence

An actual mock server was started through the demo launcher. In an isolated Chrome session, the homepage rendered at 1280×900 and 390×844. The vector example displayed three cited findings. Offline search failure displayed insufficient evidence with zero sources. The plan/tool disclosure expanded, and both JSON and Markdown attachment links returned HTTP 200. Selected screenshots are committed under `docs/assets/`.

A separate actual NVIDIA UI request completed in 29.2552 seconds with five findings, three sources and judge score 0.75, trace `aa0e306df6da40bf8a5c863217be008c`. The live screenshot, visible result text and trace are preserved separately from the six-case harness. Its in-memory export cache was cleared by a development-server reload during editing; the preserved evidence is the actual rendered output and persistent trace, not a reconstructed final JSON response.

Start a local offline server, Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m research_agent.cli demo --mock --port 8001 --no-browser
```

macOS / Linux:

```bash
.venv/bin/python -m research_agent.cli demo --mock --port 8001 --no-browser
```

Then check it from another terminal, Windows PowerShell:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8001/health
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8001/research -ContentType 'application/json' -Body '{"question":"Compare vector databases for RAG products.","mode":"mock"}'
```

macOS / Linux:

```bash
curl http://127.0.0.1:8001/health
curl -X POST http://127.0.0.1:8001/research -H 'Content-Type: application/json' -d '{"question":"Compare vector databases for RAG products.","mode":"mock"}'
```

An earlier loopback smoke run on port 18429 observed status `ok`, provider `mock`, three findings and 38 trace events, trace `53fa7cd03a544a0fba00517ff3720901`. Temporary servers were stopped after their checks; separately started user servers were preserved.

## Live provider evidence and search provenance

The initial fixture evaluation did not call live providers. Later NVIDIA runs used real model inference and external web retrieval. An OpenAI attempt was rejected with HTTP 429 `insufficient_quota` / `credit_balance_exhausted`; no successful OpenAI research answer or Anthropic live run is asserted. Optional OpenAI/Anthropic adapters have offline HTTP contract tests and do not require their keys when NVIDIA is selected.

Historical NVIDIA outputs and redacted traces are preserved in `eval/results/nvidia-smoke/` and `eval/results/approved-upgrade/`. The initial smoke answer completed in 49.5872 seconds with five quote-verified findings and four sources, but its judge score was 0.45. Later biography and memory runs include completed and partial results. One memory revision reached the configured 100-second deadline; that observed failure motivated the final revision-time guard.

The older trace snapshots exclude tool result bodies and do not explicitly name the successful search provider. They contain successful uncached web searches and no search-provider fallback events. The runtime orders Tavily before DuckDuckGo, so those events are consistent with the primary Tavily path, but the snapshots do not contain a direct successful-provider field. They do not support the former blanket statement that live Tavily credentials were unavailable. New search completion events now include `search_provider`, allowing the current live evaluation to establish the provider directly rather than infer it.

The current NVIDIA harness produced **12/12 structurally valid outputs** over six queries: **4/6** agent behavior checks and **2/6** baseline checks. Two agent results were partial due to tool/page caps. Its twelve committed trace snapshots directly record **13 successful Tavily searches** and no successful DuckDuckGo searches. This establishes Tavily use for this run; it does not retroactively add missing provider fields to older snapshots.

See [EVALUATION.md](EVALUATION.md) for the current live harness results and [live assessment](eval/results/live/REVIEW.md) for per-case review. Model cost is unknown without configured rates; real inference and web retrieval do not establish that access is unlimited or free.

## Regression coverage and practical limits

Tests cover mixed-validity findings without citation invention, conservative budget accounting, brief planning, source ranking, benign system-prompt discussion versus injection commands, judge-directed removal, live-source attribution, application-owned scope assumptions, revision time headroom, SSRF guards, API modes, exports and launcher reuse. Search-provider metadata is now asserted in the API trace regression as well.

Quotation checks establish provenance rather than semantic entailment. Confidence is an uncalibrated heuristic, and model judging is fallible. Local verification is not a claim of public-deployment readiness, exhaustive security coverage, a cross-version operating-system matrix or broad live research accuracy.
