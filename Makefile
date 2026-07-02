# telemt-mgmt Makefile — wraps .opencode/project.jsonc commands.
# Usage: make <target>

.PHONY: install typecheck lint test build coverage

install:
	uv sync && cd frontend && npm ci

typecheck:
	uv run mypy --strict telemt_proxy api bot && cd frontend && npx tsc --noEmit

lint:
	uv run ruff check telemt_proxy api bot tests && cd frontend && npx eslint src

test:
	uv run pytest -q

build:
	cd frontend && npm run build

coverage:
	uv run pytest --cov=telemt_proxy --cov=api --cov=bot --cov-report=term-missing
