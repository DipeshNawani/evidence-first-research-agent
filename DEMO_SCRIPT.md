# Demo recording script (target length: 4 minutes 15 seconds)

Goal: show **one live happy path** and **two failure/edge cases** (search failure, prompt injection) in 3 to 5 minutes. Use the homepage for the recording. It is a thin interface over the same FastAPI backend, so the story stays: plan, tools, filtering, grounded answer, honest limits.

Total timing: 0:25 intro, 1:55 live run, 0:50 failure case, 0:25 injection case, 0:40 evaluation and limits. That is 4:15, which leaves buffer under the 5-minute limit.

## Before recording (do this once, off camera)

1. **Rotate any API key that was ever shared or zipped.** Never show `.env`, the terminal environment or API keys on screen.
2. Start the app. From the repository root:

   Windows PowerShell:
   ```powershell
   .\.venv\Scripts\python.exe -m research_agent.cli demo
   ```

   macOS / Linux:
   ```sh
   source .venv/bin/activate
   research-agent demo
   ```

   It opens `http://127.0.0.1:8000/`. For a fully offline rehearsal use `research-agent demo --mock --port 8001` (Windows: `.\.venv\Scripts\python.exe -m research_agent.cli demo --mock --port 8001`). Restart the server after any `.env` change.
3. **Pre-test the live question twice and pick the best one.** The homepage has three assignment-style examples: *Vector databases*, *Agent memory*, *Indian HR SaaS*. Use the one that (a) finishes without the "Partial result" banner and (b) shows a reasonable judge score. Past live runs on this project varied: one memory run hit the 100-second wall-clock limit and returned a labeled partial draft, and one vector-database run got a low judge score. If your chosen question times out, raise `RA_MAX_WALL_SECONDS` (for example to 150) in `.env` and restart. Do not use *A short biography* in the video; it is not a research-style question.
4. Open these tabs in the editor: README architecture diagram, `src/research_agent/agent.py`, `EVALUATION.md`.
5. Browser zoom so the question box, **Run research** button and the whole result are visible. Close notifications. Record at 1080p.

Keep the **live run honest**: say aloud that it is a live run, and show the elapsed time and tokens only from the run you see on screen.

## 0:00 to 0:25: Problem and architecture

**Show:** the homepage, then the README architecture diagram.

**Say:** "This is an evidence-first research agent. A question goes through a bounded plan, then two tools, web search and page fetch, then source filtering and a structured answer. Every quotation is checked against its cited source, and a separate model judge reviews the result. The orchestration is a small handwritten planner and executor, with no framework, and every run writes a trace."

## 0:25 to 2:20: Live happy path

**Do:** leave **Run mode** on **Configured provider**. Click your pre-tested example (for instance **Vector databases**), then **Run research**.

**While it runs (about 30 to 90 seconds), show `agent.py` and say:** "The planner splits the question into sub-questions and picks tools. The executor runs search and page fetch with timeouts, retries, caching and a global budget for calls, tokens and time. Then sources are scored, deduplicated and filtered before synthesis."

**When the result appears, scroll through each part of the answer in order:**
1. **Short answer** and the **confidence** label.
2. **Key findings**, each with its supporting quotation and the *quote matched* badge.
3. **Sources used**, with quality scores.
4. **Limitations** and **Assumptions**.
5. **Suggested next steps**.
6. Expand **Plan & tool activity** and point at the tool calls and timings.

**Say:** "Quote matched means the quotation exists in the cited source. It does not prove the claim is true. The judge is also a model, so it can flag and remove unsupported findings but it is not ground truth. Confidence is a heuristic, not a calibrated probability, and the limitations list says what the evidence could not support. This is a research draft that still needs human review."

**Optional:** click **Save JSON** or **Save Markdown** to show the structured output. Exports last one hour in the running process.

**If the "Partial result" banner appears:** do not hide it. Say: "The run reached its configured time or token budget, so the agent returned a clearly labeled partial draft instead of failing silently." That is a valid edge case, but record a second take if you want a complete happy path.

**Fallback if the live provider is down:** switch to **Offline demo**, click **Vector databases**, run it, and say clearly that it is an authored mock with fixture data and a low-confidence label. Do not describe mock latency, judge values or token counts as live measurements.

## 2:20 to 3:10: Failure case (search providers down)

**Do:** set **Run mode** to **Offline: search failure** and click **Run research** on the same question.

**Show:** the **Not enough verified evidence** heading, zero sources, low confidence, the limitations, and the error and fallback events under **Plan & tool activity**.

**Say:** "This is a controlled fault using offline providers. Both search providers fail, so the agent returns a valid structured response with no invented findings and no citations. The failure stays visible instead of turning into an authoritative-looking answer."

**If you have time:** run **Offline: timeout + fallback** and show the timeout, retry and fallback events. Say that a recovered failure still lowers the confidence score.

## 3:10 to 3:35: Edge case (prompt injection)

**Do:** set **Run mode** to **Offline: injection source** and run it.

**Show:** the security event in **Plan & tool activity** and that the injected source is not cited.

**Say:** "One fetched page contains instructions aimed at the model. The agent treats web content as untrusted data, flags the passage as a security event, and keeps it out of the evidence. This reduces the risk. It does not eliminate it, and the README lists that limit."

## 3:35 to 4:15: Evaluation and limitations

**Show:** `EVALUATION.md`.

**Say (current numbers, offline run):** "The offline harness runs twelve cases against the agent and a one-call, no-tool baseline. The agent passes ten behavior checks and the baseline passes four. Two cases fail because the mock copies only the first sentence of each source, and I kept those failures visible. These are mock results, not a measure of live model quality."

**If you ran the live evaluation (`python eval/run_eval.py --live`) and updated `EVALUATION.md`, replace the paragraph above with your real live numbers:** case count, schema validity, citation grounding rate, agent versus baseline comparison, and the failures you found. Say clearly which numbers are live and which are mock.

**Close with:** "For production I would add authentication, global rate limits, isolated network egress, human-labeled evaluation, and monitoring for latency, cost per query, tool error rates, grounding rate, judge scores and injection flags."

## Optional terminal view (only if you have spare time, or as the trace shot)

Windows PowerShell:
```powershell
.\.venv\Scripts\python.exe -m research_agent.cli research "Compare vector databases for a startup RAG product." --mock --scenario timeout --output demo-timeout.json
$researchTraceId = (Get-Content demo-timeout.json -Raw | ConvertFrom-Json).meta.trace_id
.\.venv\Scripts\python.exe -m research_agent.cli trace $researchTraceId
```

macOS / Linux:
```sh
research-agent research "Compare vector databases for a startup RAG product." --mock --scenario timeout --output demo-timeout.json
research-agent trace "$(python3 -c "import json;print(json.load(open('demo-timeout.json'))['meta']['trace_id'])")"
```

## After recording

1. Upload the video (unlisted link or a Drive link with view access) and make sure it plays in a private window.
2. Add the link to the top of `README.md` and to `SUBMISSION.md`.
3. Confirm the final video is between 3 and 5 minutes and shows one happy path and at least one failure or edge case.