from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.db.models import Report

router = APIRouter(prefix="/reports", tags=["reports"])


def _parse_uuid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Report not found") from exc


def _serialize(report: Report) -> dict:
    return {
        "id": str(report.id),
        "run_id": str(report.run_id),
        "query": report.query,
        "status": report.status,
        "validation_status": report.validation_status,
        "corpus_job_count": report.corpus_job_count,
        "corpus_company_count": report.corpus_company_count,
        "generated_at": report.generated_at,
        "report": report.report_json,
        "markdown": report.markdown,
    }


@router.get("")
async def list_reports(
    query: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    statement = select(Report).order_by(Report.generated_at.desc()).limit(limit)
    if query:
        statement = statement.where(Report.normalized_query.contains(query.lower()))
    reports = (await session.execute(statement)).scalars().all()
    return [
        {
            "id": str(report.id),
            "run_id": str(report.run_id),
            "query": report.query,
            "status": report.status,
            "validation_status": report.validation_status,
            "corpus_job_count": report.corpus_job_count,
            "generated_at": report.generated_at,
        }
        for report in reports
    ]


@router.get("/{report_id}")
async def get_report(
    report_id: str, session: AsyncSession = Depends(get_session)
) -> dict:
    report = await session.get(Report, _parse_uuid(report_id))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return _serialize(report)


@router.get("/{report_id}/markdown", response_class=PlainTextResponse)
async def get_report_markdown(
    report_id: str, session: AsyncSession = Depends(get_session)
) -> str:
    report = await session.get(Report, _parse_uuid(report_id))
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report.markdown
