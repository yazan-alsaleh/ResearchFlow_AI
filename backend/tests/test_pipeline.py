from __future__ import annotations

from sqlalchemy import func, select

from app.api.v1.runs import STAGES
from app.db.models import Extraction, Job, JobSkill, Report, Run, RunJob, RunStage
from app.pipeline.orchestrator import Orchestrator


async def test_seed_corpus_is_cross_sector(seeded_session):
    session = seeded_session
    assert await session.scalar(select(func.count()).select_from(Job)) == 69
    families = (
        await session.execute(select(Job.job_family).distinct())
    ).scalars().all()
    assert len(families) >= 15
    assert {"software_data", "finance", "engineering", "healthcare", "education"} <= set(families)


async def test_pipeline_generates_a_verified_cited_report(seeded_session):
    session = seeded_session
    run = Run(
        query="Data Analyst",
        normalized_query="data analyst",
        status="queued",
        stage="queued",
        mode="seed",
        params={},
        budget={},
        stats={},
    )
    session.add(run)
    await session.flush()
    for stage in STAGES:
        session.add(RunStage(run_id=run.id, stage=stage, status="pending"))
    await session.commit()

    await Orchestrator().run(str(run.id), session)
    await session.refresh(run)

    assert run.status in {"completed", "partial"}
    assert run.finished_at is not None
    assert run.lease_expires_at is None

    report = (
        await session.execute(select(Report).where(Report.run_id == run.id))
    ).scalar_one()
    assert report.validation_status == "verified"
    assert report.corpus_job_count >= 1
    assert report.markdown.startswith("# ")

    report_json = report.report_json
    ref_ids = {ref["id"] for ref in report_json["evidence_refs"]}
    claims = list(report_json["executive_summary"])
    for section in report_json["sections"]:
        claims.extend(section["claims"])
    claims.extend(report_json["recommendations"])
    assert claims
    assert all(claim["evidence_ref"] in ref_ids for claim in claims)

    corpus_ids = set(report_json["evidence_jobs"])
    for ref in report_json["evidence_refs"]:
        assert set(ref["job_ids"]) <= corpus_ids

    job_count = await session.scalar(
        select(func.count()).select_from(RunJob).where(RunJob.run_id == run.id)
    )
    extraction_count = await session.scalar(
        select(func.count()).select_from(Extraction).where(Extraction.run_id == run.id)
    )
    skill_count = await session.scalar(select(func.count()).select_from(JobSkill))
    assert job_count == extraction_count
    assert skill_count > 0


async def test_two_runs_do_not_leak_evidence_between_reports(seeded_session):
    session = seeded_session

    async def make_run(query: str) -> Run:
        run = Run(
            query=query,
            normalized_query=query.lower(),
            status="queued",
            stage="queued",
            mode="seed",
            params={},
            budget={},
            stats={},
        )
        session.add(run)
        await session.flush()
        for stage in STAGES:
            session.add(RunStage(run_id=run.id, stage=stage, status="pending"))
        await session.commit()
        await Orchestrator().run(str(run.id), session)
        return run

    first = await make_run("AI Engineer")
    second = await make_run("Registered Nurse")

    reports = (
        await session.execute(
            select(Report).where(Report.run_id.in_([first.id, second.id]))
        )
    ).scalars().all()
    assert len(reports) == 2

    for report in reports:
        run_job_ids = set(
            (
                await session.execute(
                    select(RunJob.job_id).where(RunJob.run_id == report.run_id)
                )
            ).scalars().all()
        )
        corpus_ids = {job["id"] for job in report.report_json["evidence_jobs"].values()}
        assert {str(job_id) for job_id in run_job_ids} == corpus_ids
