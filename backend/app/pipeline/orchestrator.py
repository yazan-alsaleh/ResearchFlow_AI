from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.collector.live import LiveCollector
from app.agents.collector.seed import SeedCollector
from app.agents.intelligence.analyst import IntelligenceAnalyst
from app.agents.intelligence.evidence import build_evidence_pack
from app.agents.skills.analyst import SkillsAnalyst
from app.core.logging import get_logger
from app.db.models import Run, RunStage
from app.db.session import SessionLocal
from app.llm.router import LLMRouter

logger = get_logger(__name__)
STAGES = ("collect", "dedupe", "extract", "aggregate", "report")


class Orchestrator:
    def __init__(self, router: LLMRouter | None = None) -> None:
        self.router = router or LLMRouter()

    async def run(self, run_id: str, session: AsyncSession) -> None:
        run = await session.get(Run, uuid.UUID(run_id))
        if not run:
            logger.error("run_not_found", run_id=run_id)
            return
        if run.status in {"completed", "partial", "failed", "cancelled"}:
            return

        run.status = "running"
        run.started_at = run.started_at or datetime.now(UTC)
        run.lease_expires_at = datetime.now(UTC) + timedelta(minutes=10)
        await session.commit()

        try:
            await self._start(session, run, "collect")
            # Live collection is best-effort: it can only add jobs, never
            # fail the run. The seeded corpus (SeedCollector) is the fallback.
            live_stats = await LiveCollector().collect(run, session)
            collect_stats = await SeedCollector().collect(run, session)
            collect_stats = {**collect_stats, "live": live_stats}
            warnings = [*collect_stats.get("warnings", []), *live_stats.get("warnings", [])]
            collect_stats["warnings"] = warnings
            run.stats = {**(run.stats or {}), "collect": collect_stats}
            await self._finish(session, run, "collect", collect_stats)

            await self._start(session, run, "dedupe")
            dedupe_stats = {"duplicates_removed": 0, "canonical_jobs": collect_stats["selected"]}
            await self._finish(session, run, "dedupe", dedupe_stats)

            await self._start(session, run, "extract")
            extract_stats = await SkillsAnalyst(self.router).run(run, session)
            run.stats = {**(run.stats or {}), "extract": extract_stats}
            await self._finish(session, run, "extract", extract_stats)

            await self._start(session, run, "aggregate")
            pack = await build_evidence_pack(run, session)
            aggregate_stats = {
                "skills": len(pack["skills"]),
                "evidence_refs": len(pack["evidence_refs"]),
            }
            run.stats = {**(run.stats or {}), "aggregate": aggregate_stats}
            await self._finish(session, run, "aggregate", aggregate_stats)

            await self._start(session, run, "report")
            report_stats = await IntelligenceAnalyst(self.router).run(run, session, pack=pack)
            run.stats = {**(run.stats or {}), "report": report_stats}
            await self._finish(session, run, "report", report_stats)

            warnings = list(collect_stats.get("warnings", []))
            degraded = False
            if extract_stats.get("failed", 0) > 0:
                warnings.append(f"{extract_stats['failed']} ads could not be extracted.")
                degraded = True
            if report_stats.get("validation_status") != "verified":
                warnings.append("Some report claims could not be fully verified.")
                degraded = True
            run.stats = {**(run.stats or {}), "warnings": warnings}
            run.status = "partial" if degraded else "completed"
            run.stage = "done"
            run.finished_at = datetime.now(UTC)
            run.lease_expires_at = None
            await session.commit()
        except Exception as exc:  # noqa: BLE001 - surface the failure on the run record
            logger.exception("run_failed", run_id=run_id, error=str(exc))
            run.status = "failed"
            run.error = str(exc)
            run.finished_at = datetime.now(UTC)
            run.lease_expires_at = None
            stage = await self._stage_row(session, run, run.stage)
            if stage:
                stage.status = "failed"
                stage.error = str(exc)
                stage.finished_at = datetime.now(UTC)
            await session.commit()

    async def _stage_row(self, session: AsyncSession, run: Run, stage_name: str) -> RunStage | None:
        return (
            await session.execute(
                select(RunStage).where(
                    RunStage.run_id == run.id, RunStage.stage == stage_name
                )
            )
        ).scalar_one_or_none()

    async def _start(self, session: AsyncSession, run: Run, stage_name: str) -> None:
        run.stage = stage_name
        stage = await self._stage_row(session, run, stage_name)
        if stage is None:
            stage = RunStage(run_id=run.id, stage=stage_name)
            session.add(stage)
        stage.status = "running"
        stage.started_at = datetime.now(UTC)
        stage.error = None
        await session.commit()

    async def _finish(
        self, session: AsyncSession, run: Run, stage_name: str, counts: dict
    ) -> None:
        stage = await self._stage_row(session, run, stage_name)
        if stage is None:
            stage = RunStage(run_id=run.id, stage=stage_name)
            session.add(stage)
        stage.status = "completed"
        stage.counts = counts
        stage.finished_at = datetime.now(UTC)
        await session.commit()


async def run_pipeline(run_id: str) -> None:
    async with SessionLocal() as session:
        await Orchestrator().run(run_id, session)
