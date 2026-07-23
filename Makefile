.PHONY: venv test integration-test

VENV = .venv

venv:
	uv venv
	uv pip install -e .
	uv pip install pytest pytest-asyncio

test:
	$(VENV)/bin/python -m pytest tests/test_server.py -v

integration-test:
	$(VENV)/bin/python -m pytest tests/test_integration.py -v
