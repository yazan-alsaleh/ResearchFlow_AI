from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.api.v1 import admin, jobs, meta, reports, runs, skills
from app.core.config import settings
from app.core.logging import configure_logging

configure_logging("DEBUG" if settings.debug else "INFO")

app = FastAPI(
    title="ResearchFlow AI",
    version="0.1.0",
    description=(
        "Evidence-backed job market intelligence for Qatar. "
        "Collect job ads, extract requirements, and generate cited market reports."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(runs.router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(jobs.router, prefix="/api/v1")
app.include_router(skills.router, prefix="/api/v1")
app.include_router(meta.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict:
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}


@app.get("/api/v1/ready")
async def ready(session: AsyncSession = Depends(get_session)) -> dict:
    await session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
