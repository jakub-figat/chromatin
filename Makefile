.PHONY: test test-cov test-fast

test:
	uv run pytest -v

test-cov:
	uv run pytest --cov=chromatin --cov-report=html --cov-report=term

test-fast:
	uv run pytest -x --ff

lint:
	uv run ruff check

format:
	uv run ruff format