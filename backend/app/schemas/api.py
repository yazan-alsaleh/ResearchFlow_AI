from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunCreate(BaseModel):
    job_title: str = Field(min_length=2, max_length=120)
    filters: dict[str, Any] = Field(default_factory=dict)


class RunProgress(BaseModel):
    jobs_collected: int = 0
    jobs_deduplicated: int = 0
    jobs_extracted: int = 0
    jobs_failed: int = 0


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    query: str
    status: str
    stage: str
    mode: str
    progress: RunProgress
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    report_id: str | None = None


class EvidenceRef(BaseModel):
    id: str
    label: str
    value: Any
    job_ids: list[str] = Field(default_factory=list)


class ReportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    query: str
    status: str
    validation_status: str
    corpus_job_count: int
    corpus_company_count: int
    generated_at: datetime
    report: dict[str, Any]
    markdown: str


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    company: str
    location_text: str
    city: str | None
    country: str
    url: str
    posted_at: datetime | None
    collected_at: datetime
    job_family: str
    language: str
    employment_type: str | None
    work_mode: str | None


class JobDetailOut(JobOut):
    description: str
    extraction: dict[str, Any] | None = None


class SkillOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    canonical_name: str
    slug: str
    category: str
    skill_type: str


class CoverageOut(BaseModel):
    total_jobs: int
    total_companies: int
    total_sources: int
    by_family: dict[str, int]
    by_source: dict[str, int]
    latest_collected_at: datetime | None
