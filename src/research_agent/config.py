"""One typed configuration surface. Secrets never enter traces."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="RA_", env_file=".env", extra="ignore")

    def __init__(self, **values: Any) -> None:
        # BaseSettings accepts runtime-only options such as _env_file; keep that
        # boundary explicit for static checkers. Pydantic still validates every field.
        super().__init__(**values)

    llm_provider: Literal["mock", "openai", "anthropic"] = "mock"
    openai_api_key: SecretStr = SecretStr("")
    anthropic_api_key: SecretStr = SecretStr("")
    tavily_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-4o-mini"
    openai_judge_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-sonnet-4-5"
    anthropic_judge_model: str = "claude-haiku-4-5"
    judge_enabled: bool = True
    judge_threshold: float = Field(0.72, ge=0, le=1)
    low_confidence_threshold: float = Field(0.55, ge=0, le=1)
    source_threshold: float = Field(0.38, ge=0, le=1)
    max_sub_questions: int = Field(3, ge=1, le=5)
    max_rounds: int = Field(2, ge=1, le=2)
    max_tool_calls: int = Field(16, ge=1, le=100)
    max_pages: int = Field(6, ge=0, le=30)
    max_total_tokens: int = Field(32000, ge=100)
    max_wall_seconds: float = Field(90, gt=0, le=600)
    tool_timeout_seconds: float = Field(12, gt=0)
    llm_timeout_seconds: float = Field(25, gt=0)
    retries: int = Field(2, ge=0, le=5)
    repair_retries: int = Field(1, ge=0, le=2)
    retry_base_seconds: float = Field(0.2, ge=0, le=5)
    circuit_failures: int = Field(3, ge=1)
    circuit_cooldown_seconds: float = Field(30, gt=0)
    concurrency: int = Field(4, ge=1, le=16)
    max_search_results: int = Field(5, ge=1, le=10)
    max_response_bytes: int = Field(1_000_000, ge=100)
    max_redirects: int = Field(3, ge=0, le=5)
    evidence_chars: int = Field(3500, ge=100, le=15000)
    max_evidence: int = Field(8, ge=1, le=20)
    llm_output_tokens: int = Field(2500, ge=100)
    cache_ttl_seconds: float = Field(3600, ge=0)
    cache_max_entries: int = Field(512, ge=1)
    trace_dir: Path = Path("traces")
    input_usd_per_million: float | None = Field(None, ge=0)
    output_usd_per_million: float | None = Field(None, ge=0)
    judge_input_usd_per_million: float | None = Field(None, ge=0)
    judge_output_usd_per_million: float | None = Field(None, ge=0)

    @property
    def model(self) -> str:
        return self.anthropic_model if self.llm_provider == "anthropic" else self.openai_model

    @property
    def judge_model(self) -> str:
        return (
            self.anthropic_judge_model
            if self.llm_provider == "anthropic"
            else self.openai_judge_model
        )
