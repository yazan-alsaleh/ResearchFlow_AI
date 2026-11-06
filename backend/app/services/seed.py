from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.collector.dedupe import description_hash, fingerprint, url_hash
from app.agents.skills.taxonomy import load_taxonomy, skill_slug
from app.core.config import settings
from app.db.models import Job, Skill, SkillAlias, Source

SEED_SOURCE_SLUG = "seed-fixture"


async def seed_all(session: AsyncSession) -> dict:
    source = await _upsert_source(session)
    skills = await _upsert_skills(session)
    jobs = await _upsert_jobs(session, source)
    await session.commit()
    return {"source": source.slug, "skills": skills, "jobs": jobs}


async def _upsert_source(session: AsyncSession) -> Source:
    source = (
        await session.execute(select(Source).where(Source.slug == SEED_SOURCE_SLUG))
    ).scalar_one_or_none()
    if source:
        return source
    source = Source(
        slug=SEED_SOURCE_SLUG,
        name="Seed fixture corpus",
        type="seed",
        base_url="https://github.com/yazan-alsaleh/ResearchFlow_AI",
        domain="seed.local",
        country="QA",
        terms_url="https://github.com/yazan-alsaleh/ResearchFlow_AI/blob/main/data/seed/PROVENANCE.md",
        robots_url=None,
        policy_status="approved",
        crawl_delay_ms=0,
        max_rps=0,
        attribution_required=True,
        enabled=True,
        metadata_json={
            "note": (
                "Sample Qatar job ads for local development and demos. "
                "Replace with permitted live sources before claiming live coverage."
            )
        },
    )
    session.add(source)
    await session.flush()
    return source


async def _upsert_skills(session: AsyncSession) -> int:
    count = 0
    for definition in load_taxonomy():
        skill = (
            await session.execute(
                select(Skill).where(Skill.canonical_name == definition.name)
            )
        ).scalar_one_or_none()
        if not skill:
            skill = Skill(
                canonical_name=definition.name,
                slug=skill_slug(definition.name),
                category=definition.category,
                skill_type=definition.skill_type,
            )
            session.add(skill)
            await session.flush()
            count += 1
        else:
            skill.category = definition.category
            skill.skill_type = definition.skill_type

        for alias in {definition.name.lower(), *definition.aliases}:
            existing = (
                await session.execute(select(SkillAlias).where(SkillAlias.alias == alias))
            ).scalar_one_or_none()
            if existing is None:
                session.add(SkillAlias(skill_id=skill.id, alias=alias, source="seed"))
    return count


async def _upsert_jobs(session: AsyncSession, source: Source) -> int:
    inserted = 0
    now = datetime.now(UTC)
    for path in sorted(settings.seed_dir.glob("jobs*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            canonical_url = row["url"]
            url_digest = url_hash(canonical_url)
            existing = (
                await session.execute(select(Job).where(Job.url_hash == url_digest))
            ).scalar_one_or_none()
            if existing:
                continue

            posted_at = now - timedelta(days=int(row.get("posted_days_ago", 0)))
            description = row["description"]
            job = Job(
                source_id=source.id,
                external_id=f"seed-{url_digest[:16]}",
                url=canonical_url,
                url_hash=url_digest,
                title=row["title"],
                title_normalized=row["title"].lower().strip(),
                company=row["company"],
                company_normalized=row["company"].lower().strip(),
                location_text=row.get("location", "Qatar"),
                city=row.get("city"),
                country="QA",
                description=description,
                description_hash=description_hash(description),
                posted_at=posted_at,
                collected_at=now,
                expires_at=now + timedelta(days=60),
                employment_type=row.get("employment_type"),
                work_mode=row.get("work_mode"),
                salary_min=row.get("salary_min"),
                salary_max=row.get("salary_max"),
                salary_currency=row.get("salary_currency"),
                salary_period=row.get("salary_period"),
                language=row.get("language", "en"),
                job_family=row.get("family", "other"),
                is_active=True,
                fingerprint=fingerprint(row["title"], row["company"], description),
                raw={
                    "seed": True,
                    "source_name": "Seed fixture corpus",
                    "source_note": "Sample ad for development; not a live source of record.",
                },
            )
            session.add(job)
            inserted += 1
    return inserted
