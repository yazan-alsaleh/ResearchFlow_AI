.PHONY: dev down logs seed test lint eval

dev:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f api

seed:
	docker compose exec api uv run python -m scripts.seed

test:
	docker compose exec api uv run pytest -q

lint:
	docker compose exec api uv run ruff check .
	docker compose exec api uv run mypy app

eval:
	cd backend && uv run python -m scripts.eval --write ../docs/evaluation/results.json
