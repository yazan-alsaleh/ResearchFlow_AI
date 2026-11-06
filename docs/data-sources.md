# Data sources and collection policy

Live collection is **disabled by default** (`LIVE_COLLECTION_ENABLED=false`).
The demo runs entirely on the curated seed corpus in `data/seed/`.

## Policy (PLAN.md §7)

- **robots.txt is necessary, not sufficient.** Every source needs a manually
  reviewed `terms_url` and `policy_status` in `config/sources.yaml` before
  automated collection starts.
- Only sources with `policy_status: approved` **and** `enabled: true` are
  collected. `review` and `blocked` sources are synced to the DB for
  visibility but never fetched.
- **Never scraped without written permission:** LinkedIn, Indeed, Bayt,
  GulfTalent, Naukrigulf. These are link-only or excluded.
- No login walls, paywalls, or CAPTCHA bypassing. No personal data;
  emails and phone numbers are redacted before storage and LLM use.
- Protected attributes (nationality, gender, age, marital status, religion,
  photos) are excluded from requirements and flagged in extraction.

## How the live collector works

1. Sync `config/sources.yaml` into the `sources` table.
2. For each approved + enabled source:
   - **SSRF/allowlist check** — URL must be public and on the source's own
     domain (`is_safe_public_url` + domain match).
   - **robots.txt check** (24h cache) — disallowed sources are skipped and
     recorded in `source_fetches` with `robots_allowed=false`.
   - Polite fetch: descriptive User-Agent, crawl delay honored (capped at
     5s), timeout `LIVE_FETCH_TIMEOUT_S` (default 10s).
   - Parse `application/ld+json` `JobPosting` blocks.
   - Redact PII, upsert jobs by canonical URL hash (dedupe).
   - Record every attempt in `source_fetches` (status, hash, bytes, timing).
3. The seed collector then selects relevant jobs from the full corpus, so
   live jobs and seed jobs compete on relevance. Live collection is
   best-effort — a failing source never fails the run.

## Enabling

Set `LIVE_COLLECTION_ENABLED=true` in `.env` and flip a source to
`enabled: true` in `config/sources.yaml` after reviewing its terms.
Currently shipped as `approved` + disabled: Greenhouse public boards
(ATS API adapter is Phase 2 work — JSON-LD parsing covers career pages).
