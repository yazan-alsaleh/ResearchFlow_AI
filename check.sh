#!/usr/bin/env bash
# Local equivalent of .github/workflows/ci.yml — run before every commit.
# Usage: ./check.sh   (requires bash, uv, and Node 20+)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "==> Backend (backend/)"
cd "$ROOT/backend"
uv sync --extra dev --locked
uv run ruff check .
uv run mypy app
uv run pytest -q

echo "==> Frontend (frontend/)"
cd "$ROOT/frontend"
npm ci
npm run typecheck
npm run test
npm run build
# Optional, slower smoke tests (boots a production server; browsers needed):
# npm run test:e2e

echo "==> All checks passed"
