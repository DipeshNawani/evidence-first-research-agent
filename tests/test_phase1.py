import pytest
from pydantic import ValidationError

from research_agent.config import Settings
from research_agent.schemas import SearchArgs, ToolResult


def test_typed_settings_and_schemas() -> None:
    assert Settings(_env_file=None).max_rounds == 2
    assert ToolResult(ok=False, error_type="timeout").data is None
    with pytest.raises(ValidationError):
        SearchArgs(query="x")
    with pytest.raises(ValidationError):
        Settings(max_rounds=3, _env_file=None)
