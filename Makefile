PYTHON ?= python

.PHONY: install test lint format eval demo serve
install:
	$(PYTHON) -m pip install -e ".[dev]"
test:
	$(PYTHON) -m pytest -q
lint:
	$(PYTHON) -m ruff check .
	$(PYTHON) -m ruff format --check .
format:
	$(PYTHON) -m ruff check --fix .
	$(PYTHON) -m ruff format .
eval:
	$(PYTHON) eval/run_eval.py --mock
demo:
	$(PYTHON) -m research_agent.cli research "Compare the top 3 open-source vector databases for a startup building RAG products." --mock
serve:
	$(PYTHON) -m uvicorn research_agent.api:app --host 127.0.0.1 --port 8000
