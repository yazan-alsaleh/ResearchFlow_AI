FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
COPY backend /app/backend
COPY data /app/data
COPY config /app/config

WORKDIR /app/backend
RUN uv sync --no-dev

ENV PYTHONPATH=/app/backend
EXPOSE 8000

CMD ["sh", "-c", "uv run alembic upgrade head && uv run python -m scripts.seed && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
