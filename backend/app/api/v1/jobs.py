from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.db.models import Extraction, Job, JobSkill, Skill

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc


def _serialize(job: Job) -> dict:
    return {
        "id": str(job.id),
        "title": job.title,
        "company": job.company,
        "location_text": job.location_text,
        "city": job.city,
        "country": job.country,
        "url": job.url,
        "posted_at": job.posted_at,
        "collected_at": job.collected_at,
        "job_family": job.job_family,
        "language": job.language,
        "employment_type": job.employment_type,
        "work_mode": job.work_mode,
    }


@router.get("")
async def list_jobs(
    q: str | None = Query(default=None),
    skill: str | None = Query(default=None),
    company: str | None = Query(default=None),
    family: str | None = Query(default=None),
    city: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> dict:
    statement = select(Job).where(Job.is_active.is_(True))
    if q:
        pattern = f"%{q.lower()}%"
        statement = statement.where(
            or_(
                Job.title.ilike(pattern),
                Job.company.ilike(pattern),
                Job.description.ilike(pattern),
            )
        )
    if company:
        statement = statement.where(Job.company.ilike(f"%{company}%"))
    if family:
        statement = statement.where(Job.job_family == family)
    if city:
        statement = statement.where(Job.city.ilike(f"%{city}%"))
    if skill:
        statement = (
            statement.join(JobSkill, JobSkill.job_id == Job.id)
            .join(Skill, Skill.id == JobSkill.skill_id)
            .where(Skill.canonical_name.ilike(f"%{skill}%"))
            .distinct()
        )
    statement = statement.order_by(Job.posted_at.desc()).offset(offset).limit(limit)
    jobs = (await session.execute(statement)).scalars().all()
    return {"items": [_serialize(job) for job in jobs], "limit": limit, "offset": offset}


@router.get("/{job_id}")
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    job = await session.get(Job, _parse_uuid(job_id))
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    extraction = (
        await session.execute(
            select(Extraction)
            .where(Extraction.job_id == job.id)
            .order_by(Extraction.created_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    payload = _serialize(job)
    payload["description"] = job.description
    payload["extraction"] = extraction.payload if extraction else None
    return payload
