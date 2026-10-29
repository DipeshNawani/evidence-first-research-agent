# Four-minute demo recording script

Use the activated project virtual environment. This is an **offline mock demo**, not a claim of live research. Fixture confidence is deliberately capped. Increase terminal width to about 120 columns. Keep README, `agent.py`, and `eval/results/mock/summary.md` ready in editor tabs.

## 0:00-0:30 - Problem and architecture

**Show:** README Mermaid diagram, then `src/research_agent/agent.py`.

**Say:** "This agent turns a research question into a bounded plan, searches and reads sources, filters noise, synthesizes typed findings, verifies quotations, and uses an optional judge. The orchestrator is handwritten so transitions and failure paths are easy to inspect. All content retrieved from the web is untrusted."

## 0:30-1:40 - Happy workflow with verified evidence

**Run:**

```sh
research-agent research "Compare the top 3 open-source vector databases for a startup building RAG products." --mock --output demo-happy.json
```

**Show:** the two sub-questions and search/fetch choices; successful tool events; three retained sources; comparison observations; quotation checks; confidence factors and run metadata. The CLI prints its compact event summary after the run; trace events were persisted during the run.

**Say:** "These are deterministic authored fixtures. The content demonstrates citation plumbing; it is not an independently verified current ranking. Each finding has a source ID and supporting quote. Code checks quote presence and drops failed citations. A real quote does not itself prove the claim is true, which is why the separate judge and human review still matter. The low-confidence guard keeps mock evidence from appearing authoritative."

## 1:40-2:40 - Provider timeout and graceful recovery

**Run:**

```sh
research-agent research "Compare vector databases for a startup RAG product." --mock --scenario timeout --output demo-timeout.json
```

**Say:** "The primary search provider now times out. Only transient failures retry. Attempts consume the shared budget, a circuit opens after repeated failures, and the second provider supplies evidence. Recovered failures remain visible in confidence factors."

**Show trace, PowerShell:**

```powershell
$researchTraceId = (Get-Content demo-timeout.json -Raw | ConvertFrom-Json).meta.trace_id
research-agent trace $researchTraceId
```

**Show trace, POSIX alternative:**

```sh
research-agent trace "$(python -c 'import json; print(json.load(open("demo-timeout.json"))["meta"]["trace_id"])')"
```

Point out `attempt_error`, `retry`, `circuit_open` when present, `provider_fallback`, and `citation_verification`. Concurrency can change the exact ordering and number of retries; caps remain fixed.

## 2:40-3:15 - Fail closed when no source exists

**Run:**

```sh
research-agent research "Compare vector databases for a startup RAG product." --mock --scenario all_fail --output demo-no-evidence.json
```

**Say:** "When both providers fail, there are no findings or invented URLs. The answer stays structurally valid, reports insufficient evidence and gives a verification next step. The same boundary rejects private-IP fetches and quarantines injection fixtures."

Optional alternate edge demo: replace `all_fail` with `injection` and highlight `security_event` plus the dropped-source limitation.

## 3:15-4:00 - Evaluation, limitations and next step

**Show:** `eval/results/mock/summary.md`, `EVALUATION.md`, and the tests.

```sh
make test
make lint
```

If Make is unavailable, run `python scripts/tasks.py test` and `python scripts/tasks.py lint`.

**Say:** "The evaluation runs twelve cases against the agent and a one-call no-tool baseline. It records real failures: our extractive mock omits concrete downsides in two cases, despite perfect quote matches. That demonstrates why grounding alone is insufficient. Mock judge scores are fixed values, not evidence of model quality. With real keys, the live harness writes a separate result directory. Before public deployment I would add auth, quotas, isolated egress, persistent workers, and human-labeled semantic evals."

## Recording handoff

The repository provides the script and runnable demonstration; an actual recorded video and upload link are still needed for the assignment submission. Record the commands above in a 3-5 minute screen capture. Do not present the mock corpus or synthetic token counts as live-provider measurements.
