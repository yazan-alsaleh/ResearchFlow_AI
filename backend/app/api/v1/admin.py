from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.collector.seed import seed_query_titles
from app.api.deps import get_session
from app.api.v1.runs import STAGES
from app.core.config import settings
from app.db.models import LLMCall, Run, RunStage
from app.pipeline.orchestrator import run_pipeline
from app.services.seed import seed_all

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.post("/seed", dependencies=[Depends(require_admin)])
async def seed(session: AsyncSession = Depends(get_session)) -> dict:
    return await seed_all(session)


@router.get("/usage", dependencies=[Depends(require_admin)])
async def usage(session: AsyncSession = Depends(get_session)) -> dict:
    calls = await session.scalar(select(func.count()).select_from(LLMCall))
    tokens_in = await session.scalar(select(func.coalesce(func.sum(LLMCall.tokens_in), 0)))
    tokens_out = await session.scalar(select(func.coalesce(func.sum(LLMCall.tokens_out), 0)))
    fallback = await session.scalar(
        select(func.count()).select_from(LLMCall).where(LLMCall.status == "fallback")
    )
    return {
        "calls": calls or 0,
        "tokens_in": tokens_in or 0,
        "tokens_out": tokens_out or 0,
        "fallback_calls": fallback or 0,
    }


@router.post("/precompute", dependencies=[Depends(require_admin)])
async def precompute(
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
) -> dict:
    created = []
    for title in seed_query_titles():
        normalized = title.lower()
        existing = (
            await session.execute(
                select(Run).where(Run.normalized_query == normalized, Run.status == "completed")
            )
        ).scalar_one_or_none()
        if existing:
            continue
        run = Run(
            query=title,
            normalized_query=normalized,
            status="queued",
            stage="queued",
            mode="seed",
            params={},
            budget={"max_jobs": settings.max_jobs_per_run},
            stats={},
        )
        session.add(run)
        await session.flush()
        for stage in STAGES:
            session.add(RunStage(run_id=run.id, stage=stage, status="pending"))
        await session.commit()
        background_tasks.add_task(run_pipeline, str(run.id))
        created.append(str(run.id))
    return {"created": created, "count": len(created)}
