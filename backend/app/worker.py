from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.logging import configure_logging, get_logger
from app.db.models import Run
from app.db.session import SessionLocal
from app.pipeline.orchestrator import Orchestrator

logger = get_logger("worker")


async def claim_and_run() -> bool:
    async with SessionLocal() as session:
        run = (
            await session.execute(
                select(Run)
                .where(Run.status == "queued")
                .order_by(Run.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
        ).scalar_one_or_none()
        if not run:
            return False
        run.status = "running"
        await session.commit()
        logger.info("run_claimed", run_id=str(run.id), query=run.query)
        await Orchestrator().run(str(run.id), session)
        return True


async def main() -> None:
    configure_logging()
    logger.info("worker_started")
    while True:
        worked = await claim_and_run()
        if not worked:
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
