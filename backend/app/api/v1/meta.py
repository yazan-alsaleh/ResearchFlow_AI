from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.collector.seed import seed_query_titles
from app.api.deps import get_session
from app.db.models import Job, Source

router = APIRouter(prefix="/meta", tags=["meta"])


@router.get("/coverage")
async def coverage(session: AsyncSession = Depends(get_session)) -> dict:
    total_jobs = await session.scalar(
        select(func.count()).select_from(Job).where(Job.is_active.is_(True))
    )
    total_companies = await session.scalar(
        select(func.count(func.distinct(Job.company))).select_from(Job)
    )
    total_sources = await session.scalar(select(func.count()).select_from(Source))
    latest = await session.scalar(select(func.max(Job.collected_at)))
    by_family_rows = (
        await session.execute(
            select(Job.job_family, func.count())
            .group_by(Job.job_family)
            .order_by(func.count().desc())
        )
    ).all()
    by_source_rows = (
        await session.execute(
            select(Source.name, func.count(Job.id))
            .join(Job, Job.source_id == Source.id)
            .group_by(Source.name)
        )
    ).all()
    return {
        "total_jobs": total_jobs or 0,
        "total_companies": total_companies or 0,
        "total_sources": total_sources or 0,
        "by_family": {row[0]: row[1] for row in by_family_rows},
        "by_source": {row[0]: row[1] for row in by_source_rows},
        "latest_collected_at": latest,
    }


@router.get("/demo-titles")
async def demo_titles() -> dict:
    return {"titles": seed_query_titles()}
