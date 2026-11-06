from __future__ import annotations

import json
import time

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.skills.extractor import extract_deterministic, normalize_llm_payload
from app.agents.skills.taxonomy import skill_slug
from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import Extraction, Job, JobRequirement, JobSkill, LLMCall, Run, RunJob, Skill
from app.llm.prompts import render_prompt
from app.llm.router import LLMRouter

logger = get_logger(__name__)
PROMPT_PATH = settings.seed_dir.parent.parent / "config" / "prompts" / "extraction.md"


class SkillsAnalyst:
    name = "skills_analyst"

    def __init__(self, router: LLMRouter | None = None) -> None:
        self.router = router or LLMRouter()

    async def run(self, run: Run, session: AsyncSession) -> dict:
        rows = (
            await session.execute(
                select(RunJob, Job)
                .join(Job, RunJob.job_id == Job.id)
                .where(RunJob.run_id == run.id)
                .order_by(RunJob.relevance_score.desc())
            )
        ).all()

        processed = 0
        failed = 0
        skills_written = 0
        llm_calls = 0
        for _run_job, job in rows:
            existing = (
                await session.execute(
                    select(Extraction).where(
                        Extraction.run_id == run.id, Extraction.job_id == job.id
                    )
                )
            ).scalar_one_or_none()
            if existing:
                continue

            try:
                async with session.begin_nested():
                    payload = extract_deterministic(job)
                    model_id = "deterministic-v1"

                    if self.router.enabled:
                        response = await self._try_llm(job)
                        if response is not None:
                            try:
                                candidate = normalize_llm_payload(
                                    job, json.loads(response.text)
                                )
                            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                                logger.warning(
                                    "llm_extraction_rejected",
                                    run_id=str(run.id),
                                    job_id=str(job.id),
                                    error=str(exc),
                                )
                                session.add(
                                    LLMCall(
                                        run_id=run.id,
                                        stage="extraction",
                                        provider=response.provider,
                                        model=response.model,
                                        prompt_version="skills-v1",
                                        tokens_in=response.tokens_in,
                                        tokens_out=response.tokens_out,
                                        latency_ms=response.latency_ms,
                                        status="fallback",
                                        error_code="invalid_output",
                                    )
                                )
                            else:
                                payload = candidate
                                model_id = response.model
                                llm_calls += 1
                                session.add(
                                    LLMCall(
                                        run_id=run.id,
                                        stage="extraction",
                                        provider=response.provider,
                                        model=response.model,
                                        prompt_version="skills-v1",
                                        tokens_in=response.tokens_in,
                                        tokens_out=response.tokens_out,
                                        latency_ms=response.latency_ms,
                                        status="success",
                                    )
                                )
                        else:
                            session.add(
                                LLMCall(
                                    run_id=run.id,
                                    stage="extraction",
                                    provider="gemini",
                                    model=self.router.model_for("extraction"),
                                    prompt_version="skills-v1",
                                    status="fallback",
                                    error_code="provider_unavailable",
                                )
                            )

                    extraction = Extraction(
                        job_id=job.id,
                        run_id=run.id,
                        status="success",
                        schema_version="1.0",
                        prompt_version="skills-v1",
                        model_id=model_id,
                        payload=payload,
                        evidence_coverage=float(payload.get("evidence_coverage", 0)),
                        validation_errors=[],
                    )
                    session.add(extraction)
                    await session.flush()

                    for item in payload.get("skills", []):
                        skill = await self._get_or_create_skill(
                            session,
                            name=item["name"],
                            category=item.get("category", "technical"),
                            skill_type=item.get("skill_type", "tool"),
                        )
                        session.add(
                            JobSkill(
                                job_id=job.id,
                                skill_id=skill.id,
                                extraction_id=extraction.id,
                                importance=item.get("importance", "mentioned"),
                                evidence_quote=item.get("evidence_quote", ""),
                                evidence_valid=bool(item.get("evidence_valid", True)),
                                confidence=float(item.get("confidence", 0.5)),
                            )
                        )
                        skills_written += 1

                    for item in payload.get("qualifications", []):
                        session.add(
                            JobRequirement(
                                job_id=job.id,
                                extraction_id=extraction.id,
                                type=item.get("type", "degree"),
                                value=item.get("value", ""),
                                required=bool(item.get("required", True)),
                                evidence_quote=item.get("evidence_quote", ""),
                            )
                        )
                    for item in payload.get("certifications", []):
                        session.add(
                            JobRequirement(
                                job_id=job.id,
                                extraction_id=extraction.id,
                                type="certification",
                                value=item.get("name", ""),
                                required=bool(item.get("required", False)),
                                evidence_quote=item.get("evidence_quote", ""),
                            )
                        )
                    experience = payload.get("experience")
                    if experience:
                        min_years = experience.get("min_years")
                        session.add(
                            JobRequirement(
                                job_id=job.id,
                                extraction_id=extraction.id,
                                type="experience",
                                value=(
                                    f"{min_years}+ years"
                                    if min_years is not None
                                    else "experience"
                                ),
                                required=True,
                                evidence_quote=experience.get("evidence_quote", ""),
                            )
                        )
                    for item in payload.get("languages", []):
                        session.add(
                            JobRequirement(
                                job_id=job.id,
                                extraction_id=extraction.id,
                                type="language",
                                value=item.get("language", ""),
                                required=bool(item.get("required", False)),
                                evidence_quote=item.get("evidence_quote", ""),
                            )
                        )
                processed += 1
            except Exception as exc:  # noqa: BLE001 - a single bad ad must not fail the run
                failed += 1
                logger.warning(
                    "extraction_failed",
                    run_id=str(run.id),
                    job_id=str(job.id),
                    error=str(exc),
                )
                session.add(
                    Extraction(
                        job_id=job.id,
                        run_id=run.id,
                        status="failed",
                        prompt_version="skills-v1",
                        model_id="deterministic-v1",
                        payload={"error": str(exc)},
                        evidence_coverage=0,
                        validation_errors=[str(exc)],
                    )
                )

        await session.flush()
        return {
            "jobs": processed,
            "failed": failed,
            "skills": skills_written,
            "llm_calls": llm_calls,
        }

    async def _try_llm(self, job: Job):
        if not PROMPT_PATH.exists():
            return None
        template = PROMPT_PATH.read_text(encoding="utf-8")
        prompt = render_prompt(
            template,
            title=job.title,
            company=job.company,
            location=job.location_text,
            description=job.description[:12000],
        )
        return await self.router.generate_json(prompt, task="extraction", temperature=0)

    async def _get_or_create_skill(
        self, session: AsyncSession, *, name: str, category: str, skill_type: str
    ) -> Skill:
        skill = (
            await session.execute(select(Skill).where(Skill.canonical_name == name))
        ).scalar_one_or_none()
        if skill:
            return skill
        slug = skill_slug(name)
        existing_slug = (
            await session.execute(select(Skill).where(Skill.slug == slug))
        ).scalar_one_or_none()
        if existing_slug:
            slug = f"{slug}-{int(time.time() * 1000) % 100000}"
        skill = Skill(
            canonical_name=name,
            slug=slug,
            category=category,
            skill_type=skill_type,
        )
        session.add(skill)
        await session.flush()
        return skill
