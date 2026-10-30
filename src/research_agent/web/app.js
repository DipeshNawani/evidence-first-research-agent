"use strict";
const $ = (id) => document.getElementById(id);
const examples = {
  vector: "Compare the top 3 open-source vector databases for a startup building RAG products.",
  memory: "Compare approaches to adding memory in an AI support agent.",
  hr: "Find 5 Indian B2B SaaS startups in HR tech and summarize their positioning.",
  bio: "Who is Mahendra Singh Dhoni?",
};
let health = null;

function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined && text !== null) element.textContent = String(text);
  if (className) element.className = className;
  return element;
}
function show(id, visible) { $(id).hidden = !visible; }
function list(id, values) {
  $(id).replaceChildren(...values.map((value) => node("li", value)));
}
function safeLink(label, url) {
  try {
    const parsed = new URL(url);
    if (!["https:", "http:"].includes(parsed.protocol)) return node("span", label);
    const link = node("a", label);
    link.href = parsed.href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    return link;
  } catch { return node("span", label); }
}
function setModeNote() {
  const mode = $("execution-mode").value;
  $("mode-note").textContent = mode === "configured"
    ? `Uses ${health?.provider || "the configured provider"}${health?.model ? " · " + health.model : ""}. Keys stay on the server.`
    : "OFFLINE DEMO · Authored fixtures, no API calls. Predefined topics only; unfamiliar questions may return insufficient evidence.";
}
async function loadHealth() {
  try {
    const response = await fetch("/health");
    if (!response.ok) throw new Error("Server unavailable");
    health = await response.json();
    $("connection").textContent = "Server ready · " + health.provider.toUpperCase();
    $("connection").classList.add("ready");
    $("execution-mode").options[0].textContent = `Configured provider (${health.provider})`;
    setModeNote();
  } catch {
    $("connection").textContent = "Server unavailable";
    $("mode-note").textContent = "Start the local server, then refresh this page.";
  }
}
function metric(label, value, detail) {
  const item = node("div", null, "metric");
  item.append(node("span", label, "metric-label"), node("span", value, "metric-value"));
  if (detail) item.append(node("span", detail, "metric-note"));
  return item;
}
function renderFindings(answer) {
  $("findings").replaceChildren();
  answer.key_findings.forEach((finding) => {
    const card = node("article", null, "finding");
    card.append(node("p", finding.claim));
    const references = node("div", null, "citation-row");
    references.append(node("span", finding.verified ? "Quote matched" : "Unverified quote", "quote-badge"));
    finding.source_ids.forEach((id) => {
      const index = answer.sources.findIndex((source) => source.id === id);
      const link = node("a", `[${id}]`);
      link.href = "#source-" + index;
      references.append(link);
    });
    card.append(references, node("blockquote", finding.supporting_quote));
    $("findings").append(card);
  });
  show("findings-section", answer.key_findings.length > 0);
}
function renderSources(answer) {
  $("sources").replaceChildren();
  if (!answer.sources.length) {
    $("sources").append(node("p", "No source-backed findings were produced in this run.", "empty-note"));
  }
  answer.sources.forEach((source, index) => {
    const item = node("article", null, "source");
    item.id = "source-" + index;
    item.append(node("span", `[${source.id}]`, "source-id"), safeLink(source.title, source.url));
    item.append(node("p", `${source.domain} · ${source.provenance} · source score ${source.quality_score.toFixed(2)}`, "source-meta"));
    $("sources").append(item);
  });
}
function renderComparison(table) {
  show("comparison-section", Boolean(table?.rows?.length));
  $("comparison").replaceChildren();
  if (!table?.rows?.length) return;
  const element = node("table");
  const head = node("thead");
  const header = node("tr");
  ["Item / source", ...table.columns, "Sources"].forEach((title) => {
    const cell = node("th", title); cell.scope = "col"; header.append(cell);
  });
  head.append(header);
  const body = node("tbody");
  table.rows.forEach((row) => {
    const line = node("tr");
    [row.item, ...row.cells, row.source_ids.join(", ")].forEach((text) => line.append(node("td", text)));
    body.append(line);
  });
  element.append(head, body);
  $("comparison").append(element);
}
function renderAnswer(answer) {
  $("download-json").href = `/exports/${encodeURIComponent(answer.meta.trace_id)}/json`;
  $("download-markdown").href = `/exports/${encodeURIComponent(answer.meta.trace_id)}/markdown`;
  const mode = answer.meta.mode;
  $("result-mode").textContent = mode === "mock" ? "OFFLINE MOCK RUN · AUTHORED FIXTURES" : "LIVE RESEARCH · SOURCE-BACKED DRAFT";
  const titles = {completed: "Your research draft", insufficient_evidence: "Not enough verified evidence", needs_clarification: "A little more detail is needed", refused: "This request cannot be completed"};
  $("result-heading").textContent = titles[answer.meta.status] || "Research result";
  const warnings = [];
  if (mode === "mock") warnings.push("Offline demo: these are authored examples, not current web research.");
  if (answer.meta.partial) warnings.push("Partial result: a configured run budget was reached. Review the limitations.");
  if (answer.confidence.level === "low") warnings.push("Low confidence: verify the sources before making a decision.");
  if (answer.meta.judge_score !== null && answer.meta.judge_score < 0.5) warnings.push("The model judge flagged weak answer quality.");
  $("result-warning").textContent = warnings.join(" ");
  show("result-warning", warnings.length > 0);
  const cost = answer.meta.est_cost_usd === null ? "cost not configured" : `$${answer.meta.est_cost_usd.toFixed(5)} est. model cost`;
  $("metrics").replaceChildren(
    metric("Confidence", answer.confidence.level, `${Math.round(answer.confidence.score * 100)}% heuristic`),
    metric("Elapsed", answer.meta.latency_s.toFixed(1) + "s", `${answer.meta.tool_calls} tool attempts`),
    metric("Sources used", answer.sources.length, `${Math.round(answer.meta.grounding_rate * 100)}% quote grounding`),
    metric("Model usage", answer.meta.tokens.toLocaleString(), `tokens · ${cost}`),
  );
  $("short-answer").textContent = answer.short_answer;
  renderFindings(answer);
  renderSources(answer);
  renderComparison(answer.comparison_table);
  list("next-steps", answer.suggested_next_steps);
  list("limitations", answer.limitations);
  list("assumptions", answer.assumptions);
  $("trace-id").textContent = answer.meta.trace_id;
  $("plan").replaceChildren();
  $("trace-timeline").replaceChildren(node("p", "Loading the recorded plan and tool activity…", "empty-note"));
  show("results", true);
  $("results").scrollIntoView({behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth", block: "start"});
}
function traceDetail(event) {
  const data = event.data;
  if (event.event === "tool_end") return `${data.tool}: ${data.ok ? "ok" : data.error_type}${data.cached ? " · cached" : ""} · ${Number(data.latency_ms).toFixed(0)}ms`;
  if (event.event === "citation_verification") return `${Math.round(data.grounding_rate * 100)}% quote grounding · ${data.removed} finding(s) removed`;
  if (event.event === "judge_result") return `Score ${Number(data.score).toFixed(2)} · ${(data.issues || []).join("; ")}`;
  if (event.event === "provider_fallback") return `Switched to ${data.provider} (${data.reason})`;
  if (event.event === "security_event") return `Untrusted source quarantined: ${data.url || "flagged source"}`;
  return JSON.stringify(data).slice(0, 600);
}
async function loadTrace(id) {
  try {
    const response = await fetch("/traces/" + encodeURIComponent(id));
    if (!response.ok) throw new Error("Trace unavailable");
    const events = await response.json();
    const plan = events.find((event) => event.event === "plan")?.data?.plan;
    if (plan) {
      $("plan").append(node("p", plan.effort === "brief" ? "Brief plan · one focused research question" : "Bounded research plan", "eyebrow"));
      plan.sub_questions.forEach((step) => {
        const item = node("div", null, "plan-step");
        item.append(node("strong", `${step.id}: ${step.question}`), node("p", step.rationale), node("p", `Search: ${step.search_queries.join("; ")} · read pages: ${step.fetch_pages ? "yes" : "no"}`));
        $("plan").append(item);
      });
    }
    const meaningful = new Set(["tool_end", "provider_fallback", "security_event", "partial_draft_recovered", "citation_verification", "judge_result", "judge_claims_removed", "revision_skipped", "budget_exhausted", "run_end"]);
    const start = new Date(events[0]?.timestamp).getTime();
    const timeline = node("ol", null, "timeline");
    events.filter((event) => meaningful.has(event.event)).forEach((event) => {
      const item = node("li");
      const seconds = (new Date(event.timestamp).getTime() - start) / 1000;
      item.append(node("time", seconds.toFixed(1) + "s"), node("strong", event.event.replaceAll("_", " ")), node("span", traceDetail(event), "timeline-detail"));
      timeline.append(item);
    });
    $("trace-timeline").replaceChildren(timeline);
  } catch {
    $("trace-timeline").replaceChildren(node("p", "The answer is available, but its trace could not be loaded. Check the server's traces directory.", "empty-note"));
  }
}
$("research-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const question = $("question").value.trim();
  if (!question) { $("question").focus(); return; }
  const mode = $("execution-mode").value;
  const request = {question, mode: mode === "configured" ? "configured" : "mock", scenario: ["configured", "mock"].includes(mode) ? "normal" : mode};
  $("run-button").disabled = true;
  $("run-button").textContent = "Researching…";
  show("run-status", true);
  show("error-message", false);
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), ((health?.max_wall_seconds || 90) + 20) * 1000);
  try {
    const response = await fetch("/research", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(request), signal: controller.signal});
    if (!response.ok) throw new Error(`The server could not complete this request (HTTP ${response.status}). Check the server terminal for details.`);
    const answer = await response.json();
    renderAnswer(answer);
    await loadTrace(answer.meta.trace_id);
  } catch (error) {
    $("error-message").textContent = error.name === "AbortError" ? "The browser stopped waiting after the configured run deadline. Check the server terminal or retry with a narrower question." : error.message;
    show("error-message", true);
  } finally {
    clearTimeout(timer);
    $("run-button").disabled = false;
    $("run-button").textContent = "Run research →";
    show("run-status", false);
  }
});
document.querySelectorAll("[data-example]").forEach((button) => button.addEventListener("click", () => {
  $("question").value = examples[button.dataset.example];
  $("question").focus();
}));
$("execution-mode").addEventListener("change", setModeNote);
loadHealth();
