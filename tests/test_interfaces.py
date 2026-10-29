from pathlib import Path

from fastapi.testclient import TestClient
from typer.testing import CliRunner

from research_agent.api import create_app
from research_agent.cli import app
from research_agent.config import Settings


def test_api_and_trace(tmp_path: Path) -> None:
    with TestClient(create_app(Settings(trace_dir=tmp_path, _env_file=None))) as client:
        assert client.get("/health").status_code == 200
        response = client.post(
            "/research", json={"question": "Compare vector databases for RAG products."}
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["sources"]) == 3
        assert client.get(f"/traces/{body['meta']['trace_id']}").status_code == 200
        assert client.get("/traces/..%2F.env").status_code == 404
        assert client.get("/traces/not-a-trace").status_code == 404
        assert client.post("/research", json={"question": "x" * 4001}).status_code == 422


def test_cli_json_and_clarification(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("RA_TRACE_DIR", str(tmp_path))
    result = CliRunner().invoke(app, ["research", "hi", "--mock", "--json"])
    assert result.exit_code == 0, result.output
    import json

    body = json.loads(result.output)
    assert body["meta"]["status"] == "needs_clarification"
    assert body["meta"]["tool_calls"] == 0
    timeline = CliRunner().invoke(app, ["trace", body["meta"]["trace_id"]])
    assert timeline.exit_code == 0
    assert "early_exit" in timeline.output
