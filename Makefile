.PHONY: venv test

VENV = .venv

venv:
	uv venv
	uv pip install -e .
	uv pip install pytest pytest-asyncio

test:
	$(VENV)/bin/python -m pytest tests/ -v
