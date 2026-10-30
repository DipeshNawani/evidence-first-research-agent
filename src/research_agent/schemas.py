"""Pydantic boundaries for model, tools, API, evaluation and persisted traces."""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

AnswerStatus = Literal["completed", "needs_clarification", "refused", "insufficient_evidence"]
SourceKind = Literal["page", "snippet", "fixture"]


def utcnow() -> datetime:
    return datetime.now(UTC)


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class SearchStep(Schema):
    id: str
    question: str
    tool: Literal["web_search"] = "web_search"
    search_queries: list[str] = Field(min_length=1, max_length=2)
    fetch_pages: bool = True
    rationale: str


class Plan(Schema):
    restated_question: str
    question_type: Literal["comparison", "list_finding", "pros_cons", "survey", "other"]
    sub_questions: list[SearchStep] = Field(min_length=1, max_length=5)
    success_criteria: list[str]
    assumptions: list[str]
    stop_condition: str
    effort: Literal["brief", "research"] = "research"


class SearchArgs(Schema):
    query: str = Field(min_length=3, max_length=1200)
    max_results: int = Field(default=5, ge=1, le=10)


class FetchArgs(Schema):
    url: str = Field(min_length=8, max_length=2048)


class ToolCall(Schema):
    name: str
    args: dict[str, Any]
    sub_question_id: str = "q1"


class SearchHit(Schema):
    title: str = Field(min_length=1, max_length=1000)
    url: str = Field(min_length=8, max_length=2048)
    snippet: str = Field(min_length=1, max_length=20000)
    published_at: datetime | None = None
    retrieved_at: datetime = Field(default_factory=utcnow)


class SearchData(Schema):
    hits: list[SearchHit] = Field(min_length=1, max_length=10)
    provider: str


class PageData(Schema):
    url: str
    text: str = Field(min_length=40, max_length=200000)
    truncated: bool = False
    retrieved_at: datetime = Field(default_factory=utcnow)


class ToolResult(Schema):
    ok: bool
    error_type: str | None = None
    data: SearchData | PageData | None = None
    latency_ms: float = 0
    cached: bool = False


class Source(Schema):
    id: str
    title: str
    url: str
    domain: str
    quality_score: float = Field(ge=0, le=1)
    retrieved_at: datetime = Field(default_factory=utcnow)
    provenance: SourceKind = "page"


class Evidence(Schema):
    source: Source
    text: str
    sub_question_ids: list[str]


class DroppedSource(Schema):
    url: str
    reason: str


class FilterResult(Schema):
    evidence: list[Evidence] = Field(default_factory=list)
    dropped_sources: list[DroppedSource] = Field(default_factory=list)


class CollectionResult(FilterResult):
    gaps: int = 1
    snippet_sources_count: int = 0
    truncated_pages_count: int = 0


class Finding(Schema):
    claim: str = Field(min_length=1, max_length=1500)
    source_ids: list[str] = Field(min_length=1, max_length=5)
    supporting_quote: str = Field(min_length=12, max_length=1000)
    verified: bool = False


class ComparisonRow(Schema):
    item: str
    cells: list[str]
    source_ids: list[str] = Field(min_length=1)


class ComparisonTable(Schema):
    columns: list[str]
    rows: list[ComparisonRow]


class AnswerDraft(Schema):
    short_answer: str
    key_findings: list[Finding] = Field(max_length=12)
    comparison_table: ComparisonTable | None = None
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    suggested_next_steps: list[str] = Field(default_factory=list)


class JudgeScore(Schema):
    faithfulness: float = Field(ge=0, le=1)
    completeness: float = Field(ge=0, le=1)
    source_quality: float = Field(ge=0, le=1)
    clarity: float = Field(ge=0, le=1)
    issues: list[str]
    unsupported_finding_indices: list[Annotated[int, Field(ge=0, le=11)]] = Field(
        default_factory=list, max_length=12
    )

    @property
    def score(self) -> float:
        return (self.faithfulness + self.completeness + self.source_quality + self.clarity) / 4


class ReviewResult(Schema):
    draft: AnswerDraft
    grounding_rate: float
    judgment: JudgeScore | None = None


class Confidence(Schema):
    level: Literal["low", "medium", "high"] = "low"
    score: float = Field(default=0, ge=0, le=1)
    factors: dict[str, float] = Field(default_factory=dict)


class AnswerMeta(Schema):
    trace_id: str
    mode: Literal["mock", "live"]
    latency_s: float = 0
    tool_calls: int = 0
    tokens: int = 0
    token_upper_bound_reserved: int = 0
    est_cost_usd: float | None = None
    models: list[str] = Field(default_factory=list)
    plan_summary: str = ""
    dropped_sources_count: int = 0
    grounding_rate: float = 0
    judge_score: float | None = None
    tool_failure_rate: float = 0
    partial: bool = False
    status: AnswerStatus = "completed"
    stage_latency_s: dict[str, float] = Field(default_factory=dict)


class FinalAnswer(AnswerDraft):
    user_question: str
    sources: list[Source] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    meta: AnswerMeta


class LLMResponse(Schema):
    text: str
    model: str
    input_tokens: int
    output_tokens: int


class TraceEvent(Schema):
    trace_id: str
    timestamp: datetime = Field(default_factory=utcnow)
    event: str
    stage: str
    data: dict[str, Any] = Field(default_factory=dict)


class ResearchRequest(Schema):
    question: str = Field(min_length=0, max_length=4000)
    mode: Literal["configured", "mock"] = "configured"
    scenario: Literal["normal", "timeout", "all_fail", "injection"] = "normal"


class HealthResponse(Schema):
    status: Literal["ok"] = "ok"
    service: Literal["research-agent"] = "research-agent"
    provider: str
    model: str
    ui_version: str = "1"
    max_wall_seconds: float


class EvalCase(Schema):
    id: str
    question: str
    scenario: str = "normal"
    expected_behavior: str
    must_have: list[str]
    failure_criteria: list[str]
