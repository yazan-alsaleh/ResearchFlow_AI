# ResearchFlow AI — Project Summary

## 1. The problem

Job seekers in Qatar face a familiar question: *"What does the market actually
ask for in this role?"* Today the answers come from vague advice, personal
networks, or opaque AI chatbots that invent plausible-sounding but
unverifiable claims. Meanwhile, employers publish thousands of job ads that
encode real demand — required skills, degrees, certifications, experience —
but nobody aggregates that demand into trustworthy, cited market intelligence.

The gap: **no tool answers "what does the Qatar market ask for?" with
evidence.** Generic LLM answers hallucinate; traditional job boards show
listings but no synthesis; market reports are paywalled and stale.

## 2. The idea

ResearchFlow AI is **evidence-backed job market intelligence for Qatar**.

A user types a job title. The system:

1. **Collects** relevant Qatar job ads (robots-aware, permitted sources only)
2. **Extracts** structured requirements — skills, degrees, certifications,
   experience, languages — each carrying a **verbatim quote** from the ad
3. **Aggregates** demand deterministically in SQL/Python (counts, percentages,
   co-occurrence — never the LLM)
4. **Reports** with an optional LLM narrative that a **validator** checks
   claim-by-claim against the evidence pack; unsupported claims are rejected
   and replaced by a deterministic template
5. **Explains** every conclusion with clickable evidence chips that map back
   to real ads and source links

Working title in one line: *type a job title, get a cited market report.*

## 3. Design philosophy

- **LLMs where they add value, code where correctness matters.** Numbers are
  computed, never generated. This is what makes reports trustworthy.
- **No agent frameworks.** Three bounded agents (Collector, Skills Analyst,
  Intelligence Analyst) orchestrated by a small, inspectable state machine —
  easier to test, debug, and explain in an interview than an autonomous swarm.
- **Evidence-first.** Hash of the evidence pack stored with every report;
  every numeric claim traces to `evidence_ref → job_ids → source URL`.
- **Graceful degradation.** No API key? Deterministic extraction and template
  reports still run end to end. Live source down? Seed corpus fallback.
- **Strictly $0.** Free-tier hosting (Vercel, Supabase, Oracle Cloud ARM,
  Gemini free tier) and zero paid dependencies in the required path.
- **Legal/ethical guardrails.** Permitted sources only (robots.txt *and*
  reviewed terms), PII redaction, protected attributes excluded and flagged,
  attribution and takedown policy.

## 4. Architecture

```text
Next.js 16 (Vercel Hobby)          FastAPI + SQLAlchemy 2 async
        │  REST                         │
        ▼                               ▼
  UI: search, progress,          Postgres 16 queue
  report, jobs explorer          (FOR UPDATE SKIP LOCKED)
                                        │
                          collect → dedupe → extract → aggregate → report
                                        │
                          Gemini free tier (Flash-Lite extraction,
                          Flash report) + deterministic fallback
                                        │
                          Validator: every claim → evidence → jobs → URL
```

Key subsystems:

| Area | Implementation |
|---|---|
| API | FastAPI, Pydantic v2, idempotent `POST /runs`, RFC-7807 style errors |
| Queue | Postgres-backed, resumable stages, worker leases |
| Collection | Robots-aware fetcher, JSON-LD `JobPosting` parser, SSRF/domain allowlist, politeness delays, `source_fetches` audit log |
| Extraction | Deterministic taxonomy matching (English + Arabic aliases), required/preferred cues, verbatim quotes, protected-attribute flags, LLM path with fallback |
| Aggregation | SQL/Python evidence pack: demand, degrees, experience, companies, languages, skill co-occurrence (Jaccard) |
| Reporting | Grounded LLM narrative → validator (unknown refs, hallucinated numbers, out-of-corpus jobs rejected) → deterministic template fallback |
| Frontend | Next.js App Router, Tailwind, evidence drawer, shareable report pages with Open Graph metadata |
| Config | `config/models.yaml` (providers, routes, budgets) + `config/sources.yaml` (policy registry), validated on load |

## 5. Data

- **Seed corpus:** 69 hand-written sample ads across 19 job families
  (software/data, finance, engineering, marketing, HR, healthcare, education,
  sales, admin, legal, logistics, project management, business, design,
  customer service, operations, procurement) — labeled as fixtures, not live
  market measurements (`data/seed/PROVENANCE.md`)
- **Taxonomy:** ~200 canonical skills with aliases (English + 50 Arabic aliases)
- **Gold sets:** 30 hand-labeled cases (24 English + 6 Arabic) with per-language
  metrics in `docs/evaluation/`
- **Live collection:** disabled by default (`LIVE_COLLECTION_ENABLED=false`);
  when enabled, only `approved + enabled` sources in `config/sources.yaml` are
  fetched, with provenance recorded per fetch

## 6. Evaluation results (deterministic extractor, 30 gold cases)

| Metric | English (24) | Arabic (6) | Overall |
|---|---|---|---|
| Skill precision | 0.75 | 1.00 | 0.79 |
| Skill recall | 1.00 | 1.00 | 1.00 |
| Skill F1 | 0.85 | 1.00 | 0.88 |
| Required/preferred accuracy | 0.99 | 0.94 | 0.98 |
| Evidence validity | 1.00 | 1.00 | 1.00 |
| Experience MAE | 0.0 yrs | 0.0 yrs | 0.0 yrs |

Honest caveats: English precision is below 1.0 because the extractor surfaces
every taxonomy skill mentioned while gold labels list salient ones only; the
Arabic gold set (6 ads) is smaller than the PLAN target (20). Reproduce with
`make eval`. Full details: `docs/evaluation/README.md`.

## 7. What was built (13 merged PRs, all on `main`)

| PR | Feature |
|---|---|
| #1 | MVP scaffold: FastAPI backend, Next.js frontend, Postgres/Alembic, Docker Compose, seed corpus, 37 tests |
| #2 | GitHub Actions CI (ruff, mypy, pytest, typecheck, build) |
| #3 | Rate limiting for run creation (3/hr/IP — now **disabled by default** for local use, re-enable for public demo) |
| #4 | Evaluation harness: metrics module, gold cases, `make eval` |
| #5 | Config registry: `models.yaml` + `sources.yaml` with validated loading |
| #6 | Local CI equivalent: `check.sh` / `make check` (run before every commit) |
| #7 | Root `/health` + `/ready` endpoints with Docker healthchecks |
| #8 | Robots-aware live collector: SSRF/domain gate, robots.txt, JSON-LD parsing, PII redaction, fetch audit |
| #9 | Corpus expansion: 24 → 63 seed ads, gold set 8 → 24 cases |
| #10 | Frontend tests: Vitest (10 unit) + Playwright E2E (4 smoke) |
| #11 | Arabic extraction: language detection, normalization, 50+ aliases, per-language eval |
| #12 | Skill co-occurrence matrix: evidence pack + UI heatmap/table |
| #13 | Shareable report pages: Open Graph / Twitter metadata per report |

**Current test totals:** 70 backend tests, 13 frontend unit tests, 4 Playwright
E2E — all passing locally via `./check.sh`.

## 8. Current status

- **Local development:** fully working — `docker compose up --build` (or manual
  uvicorn + `npm run dev`) serves the UI at http://localhost:3000 and the API
  at http://localhost:8000/docs. Searches are **unlimited locally**
  (`RATE_LIMIT_ENABLED=false`).
- **Public deployment:** not yet done — intentionally parked. Planned free-tier
  topology (Vercel + Supabase + Oracle Cloud ARM, Gemini free tier) is
  documented in `PLAN.md` §13. At deploy time: set `RATE_LIMIT_ENABLED=true`.
- **GitHub Actions CI:** workflow merged but currently blocked by an account-level
  billing lock; local `./check.sh` is the enforced gate until that's resolved.

## 9. What remains

1. **Comparison mode** — two job titles side-by-side
2. **Arabic gold expansion** — 6 → 20 cases (PLAN target), plus Arabic UI polish
3. **Semantic skill normalization** (pgvector embeddings + review queue)
4. **Admin evaluation dashboard** (optional)
5. **Public deployment** — free-tier stack, precomputed reports, HTTPS

## 10. How to verify

```bash
cp .env.example .env        # once
docker compose up --build   # or: make dev
# http://localhost:3000 — try "Data Analyst", "Accountant", "Civil Engineer"

make check                  # full local CI: ruff, mypy, pytest, vitest, build
make eval                   # extraction evaluation against gold sets
```

## 11. Repository map

```text
backend/     FastAPI app: agents/, api/v1/, core/, db/, llm/, pipeline/, eval/
frontend/    Next.js: app/, components/, lib/, e2e/
config/      models.yaml, sources.yaml, prompts/
data/        seed/ (69 fixture ads + taxonomy), gold/ (30 labeled cases)
docs/        evaluation/, data-sources.md
PLAN.md      full implementation plan (architecture, schema, roadmap)
```
