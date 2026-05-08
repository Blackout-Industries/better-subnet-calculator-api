.PHONY: lockfile test build up down dev logs clean rebuild lint typecheck

lockfile:
	docker run --rm -v "$(PWD):/app" -w /app ghcr.io/astral-sh/uv:python3.12-bookworm \
		uv lock

test:
	docker build --target test -t subnet-api:test .

build:
	docker compose build app

up:
	docker compose up -d --build app
	@echo "API at http://localhost:8000/docs"

down:
	docker compose down

dev:
	docker compose --profile dev up --build dev

logs:
	docker compose logs -f app

lint:
	docker run --rm -v "$(PWD):/app" -w /app ghcr.io/astral-sh/uv:python3.12-bookworm \
		sh -c "uv sync --frozen --extra dev && uv run ruff check src tests"

typecheck:
	docker run --rm -v "$(PWD):/app" -w /app ghcr.io/astral-sh/uv:python3.12-bookworm \
		sh -c "uv sync --frozen --extra dev && uv run mypy src"

clean:
	docker compose down -v
	docker rmi subnet-api:latest subnet-api:test 2>/dev/null || true

rebuild: clean up
