"""Robots-aware live collector (PLAN §5.2, Phase 2).

Fetches approved+enabled sources from config/sources.yaml, parses JSON-LD
JobPosting payloads, redacts PII, and upserts jobs. Every attempt is
recorded in source_fetches. Live collection is best-effort: a failing
source never fails the run — the seeded corpus remains the fallback.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from datetime import UTC, datetime
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.collector.dedupe import description_hash, fingerprint, url_hash
from app.agents.collector.jsonld import parse_jobposting_jsonld
from app.agents.collector.robots import USER_AGENT, RobotsCache, is_safe_public_url
from app.core.config import settings
from app.core.logging import get_logger
from app.core.registry import load_sources_registry
from app.db.models import Job, Run, Source, SourceFetch

logger = get_logger(__name__)

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-()]{7,}\d)")


def redact_pii(text: str) -> str:
    """Remove emails and phone-like numbers before storage and LLM use."""
    text = EMAIL_RE.sub("[redacted email]", text)
    return PHONE_RE.sub("[redacted phone]", text)


async def sync_sources(session: AsyncSession) -> list[Source]:
    """Upsert registry sources into the DB; return approved+enabled rows."""
    registry = load_sources_registry(str(settings.config_dir))
    rows: list[Source] = []
    for config in registry.sources:
        row = (
            await session.execute(select(Source).where(Source.slug == config.slug))
        ).scalar_one_or_none()
        if row is None:
            row = Source(
                slug=config.slug,
                name=config.name,
                type=config.type,
                base_url=config.base_url,
                domain=config.domain,
                country=config.country,
                terms_url=config.terms_url,
                robots_url=config.robots_url,
                policy_status=config.policy_status,
                crawl_delay_ms=config.crawl_delay_ms,
                max_rps=float(config.max_rps),
                attribution_required=config.attribution_required,
                enabled=config.enabled,
                metadata_json=config.metadata,
            )
            session.add(row)
            await session.flush()
        rows.append(row)
    return [row for row in rows if row.policy_status == "approved" and row.enabled]


class LiveCollector:
    name = "live_collector"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client
        self._robots = RobotsCache()

    async def collect(self, run: Run, session: AsyncSession) -> dict:
        stats: dict = {
            "sources_checked": 0,
            "fetched": 0,
            "parsed": 0,
            "persisted": 0,
            "duplicates_skipped": 0,
            "robots_blocked": 0,
            "errors": 0,
            "warnings": [],
        }
        if not settings.live_collection_enabled:
            stats["warnings"].append("Live collection disabled; using seeded corpus only.")
            return stats

        sources = await sync_sources(session)
        stats["sources_checked"] = len(sources)
        own_client = self._client is None
        client = self._client or httpx.AsyncClient(
            timeout=settings.live_fetch_timeout_s, follow_redirects=True
        )
        try:
            for source in sources:
                if source.type == "seed":
                    continue
                await self._collect_source(run, source, session, client, stats)
        finally:
            if own_client:
                await client.aclose()
        await session.flush()
        return stats

    async def _collect_source(
        self,
        run: Run,
        source: Source,
        session: AsyncSession,
        client: httpx.AsyncClient,
        stats: dict,
    ) -> None:
        url = source.base_url
        # SSRF + allowlist: only the source's own public domain.
        parsed = urlparse(url)
        if not is_safe_public_url(url) or (parsed.netloc or "").lower() != source.domain.lower():
            stats["errors"] += 1
            stats["warnings"].append(f"Source {source.slug}: URL failed safety checks; skipped.")
            await self._record_fetch(session, run, source, url, error="unsafe_url")
            return

        decision = await self._robots.check(url, client)
        if not decision.allowed:
            stats["robots_blocked"] += 1
            stats["warnings"].append(
                f"Source {source.slug}: blocked by robots.txt ({decision.reason})."
            )
            await self._record_fetch(
                session, run, source, url, robots_allowed=False, error="robots_blocked"
            )
            return

        delay = max(decision.crawl_delay or 0, source.crawl_delay_ms / 1000)
        if delay:
            await asyncio.sleep(min(delay, 5))

        started = time.perf_counter()
        try:
            response = await client.get(url, headers={"User-Agent": USER_AGENT})
        except httpx.HTTPError as exc:
            stats["errors"] += 1
            stats["warnings"].append(f"Source {source.slug}: fetch failed ({type(exc).__name__}).")
            await self._record_fetch(session, run, source, url, error=str(exc)[:300])
            return

        duration_ms = int((time.perf_counter() - started) * 1000)
        stats["fetched"] += 1
        if response.status_code != 200:
            stats["errors"] += 1
            stats["warnings"].append(
                f"Source {source.slug}: HTTP {response.status_code}; skipped."
            )
            await self._record_fetch(
                session,
                run,
                source,
                url,
                status_code=response.status_code,
                duration_ms=duration_ms,
                error=f"http_{response.status_code}",
            )
            return

        parsed_jobs = parse_jobposting_jsonld(response.text, url)
        stats["parsed"] += len(parsed_jobs)
        if not parsed_jobs:
            stats["warnings"].append(f"Source {source.slug}: no JobPosting JSON-LD found.")
        for item in parsed_jobs:
            persisted = await self._upsert_job(session, source, item)
            stats["persisted" if persisted else "duplicates_skipped"] += 1
        await self._record_fetch(
            session,
            run,
            source,
            url,
            status_code=response.status_code,
            duration_ms=duration_ms,
            content_hash=hashlib.sha256(response.content).hexdigest(),
            bytes=len(response.content),
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
        )

    async def _upsert_job(self, session: AsyncSession, source: Source, item: dict) -> bool:
        description = redact_pii(item["description"] or item["title"])
        canonical = item["url"]
        digest = url_hash(canonical)
        existing = (
            await session.execute(select(Job).where(Job.url_hash == digest))
        ).scalar_one_or_none()
        if existing:
            return False
        now = datetime.now(UTC)
        job = Job(
            source_id=source.id,
            external_id=None,
            url=canonical,
            url_hash=digest,
            title=item["title"],
            title_normalized=item["title"].lower().strip(),
            company=item["company"],
            company_normalized=item["company"].lower().strip(),
            location_text=item["location"],
            city=item["city"],
            description=description,
            description_hash=description_hash(description),
            posted_at=item["posted_at"],
            collected_at=now,
            expires_at=None,
            employment_type=item["employment_type"],
            language="en",
            job_family="other",
            is_active=True,
            fingerprint=fingerprint(item["title"], item["company"], description),
            raw={"live": True, "source_slug": source.slug},
        )
        session.add(job)
        await session.flush()
        return True

    async def _record_fetch(
        self, session: AsyncSession, run: Run, source: Source, url: str, **kwargs
    ) -> None:
        session.add(
            SourceFetch(
                run_id=run.id,
                source_id=source.id,
                url=url,
                fetched_at=datetime.now(UTC),
                **kwargs,
            )
        )
        await session.flush()
