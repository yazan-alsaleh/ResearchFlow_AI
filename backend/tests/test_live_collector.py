from __future__ import annotations

import httpx
import pytest
from sqlalchemy import func, select

from app.agents.collector.live import LiveCollector, redact_pii
from app.agents.collector.robots import is_safe_public_url
from app.core.config import settings
from app.core.registry import clear_registry_cache
from app.db.models import Job, Run, SourceFetch

PAGE_HTML = """<html><head>
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "JobPosting",
  "title": "Data Analyst",
  "description": "Required: SQL and Python. Contact hr@example.com or +974 5555 1234 to apply.",
  "datePosted": "2026-11-01",
  "employmentType": "Full-time",
  "url": "https://jobs.example.com/data-analyst",
  "hiringOrganization": {"@type": "Organization", "name": "Test Bank"},
  "jobLocation": {"@type": "Place", "address": {"addressLocality": "Doha", "addressCountry": "QA"}}
}
</script></head><body><h1>Careers</h1></body></html>"""

SOURCES_YAML = """
sources:
  - slug: test-jobs
    name: Test Jobs
    type: career_page
    base_url: https://jobs.example.com/careers
    domain: jobs.example.com
    country: QA
    terms_url: https://jobs.example.com/terms
    robots_url: https://jobs.example.com/robots.txt
    policy_status: approved
    crawl_delay_ms: 0
    max_rps: 5
    attribution_required: true
    enabled: true
    metadata:
      adapter: jsonld
  - slug: pending-source
    name: Pending Source
    type: career_page
    base_url: https://pending.example.com/careers
    domain: pending.example.com
    policy_status: review
    enabled: true
"""


def make_client(robots_body: str = "User-agent: *\nAllow: /\n") -> httpx.AsyncClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(200, text=robots_body)
        return httpx.Response(200, text=PAGE_HTML)

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture
async def live_run(seeded_session, monkeypatch, tmp_path):
    (tmp_path / "sources.yaml").write_text(SOURCES_YAML, encoding="utf-8")
    monkeypatch.setattr(settings, "live_collection_enabled", True)
    monkeypatch.setattr(settings, "config_dir", tmp_path)
    clear_registry_cache()
    run = Run(
        query="Data Analyst",
        normalized_query="data analyst",
        status="queued",
        stage="queued",
        mode="live",
        params={},
        budget={},
        stats={},
    )
    seeded_session.add(run)
    await seeded_session.flush()
    yield run
    clear_registry_cache()


async def test_live_collector_persists_jsonld_jobs_and_records_fetch(seeded_session, live_run):
    stats = await LiveCollector(client=make_client()).collect(live_run, seeded_session)
    assert stats["sources_checked"] == 1
    assert stats["fetched"] == 1
    assert stats["parsed"] == 1
    assert stats["persisted"] == 1

    job = (
        await seeded_session.execute(select(Job).where(Job.company == "Test Bank"))
    ).scalar_one_or_none()
    assert job is not None
    assert job.company == "Test Bank"
    assert job.city == "Doha"
    # PII is redacted before storage.
    assert "hr@example.com" not in job.description
    assert "5555 1234" not in job.description
    assert "[redacted" in job.description

    fetches = (await seeded_session.execute(select(SourceFetch))).scalars().all()
    assert len(fetches) == 1
    assert fetches[0].status_code == 200
    assert fetches[0].robots_allowed is True
    assert fetches[0].content_hash


async def test_live_collector_skips_duplicate_on_second_run(seeded_session, live_run):
    collector = LiveCollector(client=make_client())
    first = await collector.collect(live_run, seeded_session)
    assert first["persisted"] == 1
    second = await collector.collect(live_run, seeded_session)
    assert second["persisted"] == 0
    assert second["duplicates_skipped"] == 1
    count = await seeded_session.scalar(
        select(func.count()).select_from(Job).where(Job.title == "Data Analyst")
    )
    assert count == 2  # 1 seed + 1 live (seed row has the same title)


async def test_live_collector_respects_robots_disallow(seeded_session, live_run):
    stats = await LiveCollector(
        client=make_client(robots_body="User-agent: *\nDisallow: /careers\n")
    ).collect(live_run, seeded_session)
    assert stats["robots_blocked"] == 1
    assert stats["fetched"] == 0
    assert stats["persisted"] == 0
    fetches = (await seeded_session.execute(select(SourceFetch))).scalars().all()
    assert len(fetches) == 1
    assert fetches[0].robots_allowed is False


async def test_live_collector_disabled_by_default(seeded_session, live_run, monkeypatch):
    monkeypatch.setattr(settings, "live_collection_enabled", False)
    stats = await LiveCollector(client=make_client()).collect(live_run, seeded_session)
    assert stats["sources_checked"] == 0
    assert stats["persisted"] == 0
    assert await seeded_session.scalar(select(func.count()).select_from(SourceFetch)) == 0


def test_redact_pii():
    assert redact_pii("Mail a@b.com or call +974 5555 1234") == (
        "Mail [redacted email] or call [redacted phone]"
    )


def test_ssrf_guard_blocks_private_urls():
    assert is_safe_public_url("https://jobs.example.com/careers")
    assert not is_safe_public_url("http://127.0.0.1/admin")
    assert not is_safe_public_url("http://localhost:8000/")
    assert not is_safe_public_url("file:///etc/passwd")
    assert not is_safe_public_url("https://10.0.0.5/secret")
