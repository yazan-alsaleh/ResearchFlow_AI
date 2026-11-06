from __future__ import annotations

import uuid

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Header,
    HTTPException,
    Request,
    Response,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.core.config import settings
from app.core.rate_limit import build_limiter
from app.db.models import Extraction, Report, Run, RunJob, RunStage
from app.pipeline.orchestrator import run_pipeline
from app.schemas.api import RunCreate, RunOut, RunProgress

router = APIRouter(prefix="/runs", tags=["runs"])

STAGES = ("collect", "dedupe", "extract", "aggregate", "report")

limiter = build_limiter(settings)


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Run not found") from exc


async def serialize_run(session: AsyncSession, run: Run) -> dict:
    job_count = (
        await session.scalar(
            select(func.count()).select_from(RunJob).where(RunJob.run_id == run.id)
        )
        or 0
    )
    extracted = (
        await session.scalar(
            select(func.count())
            .select_from(Extraction)
            .where(Extraction.run_id == run.id, Extraction.status == "success")
        )
        or 0
    )
    failed = (
        await session.scalar(
            select(func.count())
            .select_from(Extraction)
            .where(Extraction.run_id == run.id, Extraction.status == "failed")
        )
        or 0
    )
    report = (
        await session.execute(select(Report).where(Report.run_id == run.id))
    ).scalar_one_or_none()
    return {
        "id": str(run.id),
        "query": run.query,
        "status": run.status,
        "stage": run.stage,
        "mode": run.mode,
        "progress": RunProgress(
            jobs_collected=job_count,
            jobs_deduplicated=job_count,
            jobs_extracted=extracted,
            jobs_failed=failed,
        ),
        "warnings": (run.stats or {}).get("warnings", []),
        "error": run.error,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "finished_at": run.finished_at,
        "report_id": str(report.id) if report else None,
    }


@router.post("", response_model=RunOut, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    payload: RunCreate,
    background_tasks: BackgroundTasks,
    response: Response,
    request: Request,
    session: AsyncSession = Depends(get_session),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    query = payload.job_title.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Job title is required")

    # Idempotent replays are free: return the existing run without consuming quota.
    if idempotency_key:
        existing = (
            await session.execute(select(Run).where(Run.idempotency_key == idempotency_key))
        ).scalar_one_or_none()
        if existing:
            return await serialize_run(session, existing)

    if settings.rate_limit_enabled:
        client_ip = request.client.host if request.client else "unknown"
        # Rebuild limits if tests monkeypatched settings.
        limiter.per_hour = settings.runs_per_hour_per_ip
        limiter.per_day = settings.runs_per_day_per_ip
        limiter.global_per_day = settings.runs_per_day_global
        decision = limiter.check(client_ip)
        for key, value in decision.headers.items():
            response.headers[key] = value
        if not decision.allowed:
            raise HTTPException(
                status_code=429,
                detail="Run creation rate limit exceeded",
                headers={"Retry-After": str(decision.retry_after or 60)},
            )

    run = Run(
        query=query,
        normalized_query=query.lower(),
        status="queued",
        stage="queued",
        mode="seed" if settings.demo_mode else "live",
        params=payload.filters,
        budget={
            "max_jobs": settings.max_jobs_per_run,
            "max_llm_calls": settings.max_llm_calls_per_run,
        },
        stats={},
        idempotency_key=idempotency_key,
    )
    session.add(run)
    await session.flush()
    for stage in STAGES:
        session.add(RunStage(run_id=run.id, stage=stage, status="pending"))
    await session.commit()
    await session.refresh(run)

    if settings.run_inline:
        background_tasks.add_task(run_pipeline, str(run.id))
    return await serialize_run(session, run)


@router.get("/{run_id}", response_model=RunOut)
async def get_run(run_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    run = await session.get(Run, _parse_uuid(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return await serialize_run(session, run)


@router.post("/{run_id}/cancel", response_model=RunOut)
async def cancel_run(run_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    run = await session.get(Run, _parse_uuid(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    if run.status in {"queued", "running"}:
        run.status = "cancelled"
        run.stage = "cancelled"
        await session.commit()
    return await serialize_run(session, run)


@router.get("/{run_id}/report")
async def get_run_report(run_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    run = await session.get(Run, _parse_uuid(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    report = (
        await session.execute(select(Report).where(Report.run_id == run.id))
    ).scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report is not ready")
    return {"report_id": str(report.id)}
