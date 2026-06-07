.PHONY: install up down dev worker migrate revision test fmt lint typecheck clean smoke-llm smoke-tts frontend-install frontend-build

install:
	uv sync

up:
	docker compose up -d

down:
	docker compose down

dev:
	uv run uvicorn app.main:app --reload --port 8000

worker:
	uv run arq app.workers.arq_settings.WorkerSettings

migrate:
	uv run alembic upgrade head

revision:
	@test -n "$(m)" || (echo "Usage: make revision m=<message>"; exit 1)
	uv run alembic revision --autogenerate -m "$(m)"

test:
	uv run pytest

fmt:
	uv run ruff format .
	uv run ruff check --fix .

lint:
	uv run ruff check .

typecheck:
	uv run mypy app

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov

smoke-llm:
	ALGOREEL_ALLOW_LIVE_LLM=1 uv run python -m scripts.smoke_llm $(args)

smoke-tts:
	ALGOREEL_ALLOW_LIVE_TTS=1 uv run python -m scripts.smoke_tts $(args)

frontend-install:
	cd frontend && npm install

frontend-build:
	cd frontend && npm run build
