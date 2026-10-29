"""Portable equivalents of Make targets for Windows installations without GNU Make."""

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMANDS: dict[str, list[list[str]]] = {
    "test": [["-m", "pytest", "-q"]],
    "lint": [["-m", "ruff", "check", "."], ["-m", "ruff", "format", "--check", "."]],
    "eval": [["eval/run_eval.py", "--mock"]],
    "demo": [
        [
            "-m",
            "research_agent.cli",
            "research",
            "Compare the top 3 open-source vector databases for a startup building RAG products.",
            "--mock",
        ]
    ],
    "serve": [["-m", "uvicorn", "research_agent.api:app", "--host", "127.0.0.1", "--port", "8000"]],
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=COMMANDS)
    options = parser.parse_args()
    for command in COMMANDS[options.task]:
        subprocess.run([sys.executable, *command], cwd=ROOT, check=True)
