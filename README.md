# ResearchFlow AI

Evidence-backed job market intelligence for Qatar.

Type a job title. ResearchFlow AI selects relevant Qatar job ads, extracts requirements with
verbatim evidence, aggregates the results in SQL, and writes a market report where every claim
cites an evidence ID that maps back to real ads and source links.

> **Status: MVP scaffold.** The demo corpus is a set of clearly labeled sample fixtures, not live
> Qatar market coverage. The pipeline, API, report validator, and UI are functional end to end.

The public demo is designed for a fresh CS graduate's AI/ML portfolio: no login, no CV upload,
English UI, and a strictly $0 hosting target.

---

## What it does

1. **Collect** — robots-aware source policy, URL canonicalization, and a seeded cross-sector corpus
   for offline development.
2. **Extract** — required vs preferred skills, degrees, certifications, experience, and languages.
   Every extracted item carries a verbatim quote from the ad.
3. **Aggregate** — deterministic SQL builds an evidence pack: counts, percentages, companies,
   degree levels, experience buckets, and evidence references.
4. **Report** — an optional LLM narrative is validated against the evidence pack. Unsupported claims
   are rejected, and a deterministic template becomes the fallback.
5. **Explore** — click any evidence chip in the report to inspect the ads behind the claim.

Coverage is intentionally cross-sector: software/data, finance, engineering, marketing, HR,
healthcare, education, sales, administration, legal, logistics, project management, business,
design, customer service, operations, and procurement.

---

## Architecture

```
Next.js 16 (Vercel Hobby)
        │  REST
        ▼
FastAPI + SQLAlchemy 2 async (Oracle Cloud Always Free / Render Free)
        │
        ├── Postgres 16 (Supabase Free)
        │     jobs, skills, runs, extractions, evidence, reports, LLM calls
        │
        ├── Pipeline orchestrator
        │     collect → dedupe → extract → aggregate → report
        │
        ├── Gemini free tier (Flash-Lite extraction, Flash report)
        │     └── deterministic fallback when unavailable
        │
        └── Validator
              every claim → evidence_ref → job_ids → source URL
```

Key design choices:

- **No LangChain or CrewAI.** The pipeline is a small, inspectable state machine.
- **Postgres-backed queue** using `SELECT ... FOR UPDATE SKIP LOCKED`, so a worker can be restarted
  without losing queued runs.
- **Deterministic analytics first.** The LLM writes prose, not the numbers.
- **Evidence is stored with the report**, including a hash of the evidence pack.
- **Graceful degradation.** With no `GEMINI_API_KEY`, extraction and reports still work end to end.

---

## Quick start

### Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Node.js 20+ and npm
- PostgreSQL 16 (or Docker)

### Option A — Docker Compose (one command)

```bash
cp .env.example .env
docker compose up --build
```

Open <http://localhost:3000>. The API runs migrations and seeds the sample corpus on startup.
API docs are at <http://localhost:8000/docs>.

The database is exposed on host port **5433** by default so it does not collide with a local
PostgreSQL install. Change `POSTGRES_PORT` in `.env` if you need a different port.

### Option B — local development

```bash
cp .env.example .env

# Start only Postgres if you do not already have it
docker compose up -d db

cd backend
uv sync --extra dev
uv run alembic upgrade head
uv run python -m scripts.seed
uv run uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open <http://localhost:3000>.

### Useful commands

```bash
# Backend
cd backend
uv run pytest -q              # 37 tests: taxonomy, dedupe, extraction, validator, API, pipeline
uv run ruff check .
uv run mypy app

# Frontend
cd frontend
npm run typecheck
npm run build

# Quality gate
docker compose exec api uv run pytest -q
```

---

## Configuration

Copy `.env.example` to `.env`. The backend reads both the repository root `.env` and
`backend/.env` (root first, backend overrides).

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5433/researchflow` | Async SQLAlchemy DSN |
| `FRONTEND_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | CORS allowlist |
| `GEMINI_API_KEY` | empty | Enables the LLM path; empty means deterministic only |
| `GEMINI_EXTRACTION_MODEL` | `gemini-2.5-flash-lite` | Per-ad extraction |
| `GEMINI_REPORT_MODEL` | `gemini-2.5-flash` | Report narrative |
| `LLM_ENABLED` | `true` | Hard switch for model calls |
| `DEMO_MODE` | `true` | Labels runs as demo/seed mode |
| `RUN_INLINE` | `true` | Run the pipeline in a background task instead of a separate worker |
| `MIN_RELEVANCE` | `0.55` | Minimum title-match score; below 3 matches, related roles from the same job family are added |
| `MAX_JOBS_PER_RUN` | `40` | Corpus cap per run |
| `ADMIN_TOKEN` | `change-me` | Required by `/api/v1/admin/*` |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000` | API base URL used by the browser |

**Never commit a real `.env`.** `opencode.json` is also ignored.

### LLM routing

- Extraction uses Gemini Flash-Lite with JSON output mode.
- Report narrative uses Gemini Flash with a strict evidence-pack prompt.
- Local **Qwen3:4B via Ollama** is intended for development and evaluation only; it is not routed
  by the MVP.
- On a missing key, timeout, rate limit, malformed JSON, or failed validation, the pipeline falls
  back deterministically and records the fallback in `llm_calls`.

### Report validation

The validator rejects a claim when:

- it has no `evidence_ref`,
- the `evidence_ref` is unknown,
- it cites a job outside the run's corpus,
- it contains a number that is not present in the evidence pack,
- the report corpus count does not match the pack.

A rejected LLM narrative is replaced by the deterministic template, and the reason is recorded on
the report.

---

## API

Base path: `/api/v1`

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/runs` | Create a run (`{"job_title": "Data Analyst"}`); optional `Idempotency-Key` |
| `GET` | `/runs/{id}` | Run status, stage, progress, warnings, report ID |
| `POST` | `/runs/{id}/cancel` | Cancel a queued/running run |
| `GET` | `/reports` | List generated reports |
| `GET` | `/reports/{id}` | Full report JSON, markdown, evidence |
| `GET` | `/reports/{id}/markdown` | Markdown download |
| `GET` | `/jobs` | Browse corpus; filters: `q`, `skill`, `company`, `family`, `city` |
| `GET` | `/jobs/{id}` | Job detail plus latest extraction |
| `GET` | `/skills` | Skill taxonomy |
| `GET` | `/meta/coverage` | Corpus totals and family/source breakdown |
| `GET` | `/meta/demo-titles` | Suggested demo queries |
| `POST` | `/admin/seed` | Idempotent seed (`X-Admin-Token`) |
| `POST` | `/admin/precompute` | Queue one run per demo title (`X-Admin-Token`) |
| `GET` | `/admin/usage` | LLM call/token/fallback totals (`X-Admin-Token`) |

Example:

```bash
curl -X POST http://localhost:8000/api/v1/runs \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-1" \
  -d '{"job_title":"Registered Nurse"}'

curl http://localhost:8000/api/v1/meta/coverage
```

---

## Data policy and the sample corpus

- Only public pages permitted by `robots.txt` and the source's terms are in scope.
- No login walls, paywalls, CAPTCHA bypassing, or personal data.
- Nationality, gender, age, marital status, religion, and photos are excluded from requirements and
  flagged in extraction.
- Every source is expected to record its robots URL, terms URL, policy status, attribution
  requirement, crawl delay, and fetch history.
- Reports state snapshot vs trend limits, salary coverage, source diversity, and language coverage.

The MVP corpus in `data/seed/jobs.jsonl` is **sample fixture data**. The 24 ads and salary ranges are
illustrative, and the URLs use an illustrative `job=` parameter. See
[`data/seed/PROVENANCE.md`](data/seed/PROVENANCE.md). Do not present seed reports as live market
measurements.

---

## Evaluation

Current automated checks (37 tests):

- taxonomy alias matching and longest-alias precedence,
- URL canonicalization, fingerprinting, and description hashing,
- required/preferred extraction and protected-attribute flags,
- evidence validator: unknown refs, missing refs, hallucinated numbers, out-of-corpus jobs,
- deterministic report claim citations,
- API smoke tests and idempotency,
- end-to-end pipeline: seed → collect → extract → aggregate → report,
- cross-run isolation so evidence does not leak between reports.

Portfolio metrics to report once live collection is enabled:

| Metric | Definition | Target |
| --- | --- | --- |
| Extraction precision | Share of extracted skills present in a hand-labeled ad set | ≥ 0.90 |
| Extraction recall | Share of labeled skills recovered | ≥ 0.80 |
| Evidence validity | Share of stored quotes found verbatim in the ad | 1.00 |
| Claim rejection rate | Share of LLM reports rejected by the validator | track, not minimize blindly |
| Report latency | p95 time from run creation to published report | < 60 s on free tier |
| Cost per report | LLM tokens × provider price | $0 on free tier |

---

## Strictly $0 deployment

| Layer | Service | Free-tier notes |
| --- | --- | --- |
| Frontend | Vercel Hobby | Set root directory to `frontend`; add `NEXT_PUBLIC_API_BASE_URL` |
| Database | Supabase Free | Use the session pooler/direct connection for migrations; keep the project active |
| API + worker | Oracle Cloud Always Free (ARM) | Run Docker Compose behind Caddy; DuckDNS for a hostname |
| Fallback API | Render Free | Spins down when idle; cold starts are expected |
| LLM | Gemini free tier | Rate-limited; deterministic fallback keeps the demo usable |
| TLS | Caddy + Let's Encrypt | Automatic certificates |

Suggested deployment order:

1. Create the Supabase project and copy its Postgres connection string into `DATABASE_URL`.
2. Run `uv run alembic upgrade head` and `uv run python -m scripts.seed` once against Supabase.
3. Deploy the API to Oracle Cloud (Docker Compose + Caddy reverse proxy on port 443).
4. Set `FRONTEND_ORIGINS` to the Vercel domain and `NEXT_PUBLIC_API_BASE_URL` to the API domain.
5. Deploy `frontend/` to Vercel and run a smoke test with a non-tech title.

Operational limits for the free tier:

- Precompute demo titles instead of running the pipeline on every page view.
- Cache reports by normalized query and evidence-pack hash.
- Cap jobs per run and LLM calls per run.
- Add per-IP rate limiting at Caddy before exposing the demo publicly.

---

## Repository layout

```
backend/
  app/
    agents/          collector, skills analyst, intelligence analyst
    api/v1/          runs, reports, jobs, skills, meta, admin
    core/            config, logging, errors
    db/              SQLAlchemy models and session
    llm/             provider protocol, Gemini, router, prompt rendering
    pipeline/        orchestrator state machine
    services/        idempotent seed loader
  alembic/           initial schema migration
  tests/             37 backend tests
  scripts/seed.py
frontend/
  app/               landing, about, jobs, runs, reports
  components/        search, progress, report view, jobs explorer
  lib/               API client and types
data/seed/           sample ads, skill taxonomy, provenance
config/prompts/      extraction and report prompts
docker-compose.yml
PLAN.md              approved implementation plan
```

---

## Deliberately out of scope for this MVP

- Authentication and user accounts
- CV upload or personal career advice
- Arabic UI (Arabic extraction is a later phase; the UI stays English)
- A demo video or blog post
- Live scraping of sources that do not permit automated access

## Roadmap

- Live source adapters (JSON-LD/ATS) with per-source policy tests and fetch telemetry
- Arabic requirement extraction with language-aware evidence spans
- Trend detection across collection waves; “rising/falling” claims only with ≥ 2 snapshots
- PostgreSQL full-text search and optional `pgvector` skill similarity
- Evaluation dataset with hand-labeled ads and a published error analysis
- Caddy rate limiting and abuse controls for the public demo

---

## License and attribution

Company names appear only in sample scenarios. Reports generated from the seed corpus are labeled
as snapshots and must not be described as live Qatar market measurements.
