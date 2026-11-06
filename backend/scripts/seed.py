from __future__ import annotations

import asyncio

from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.services.seed import seed_all


async def main() -> None:
    # Import models before create_all so metadata is populated.
    from app.db import models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        result = await seed_all(session)
    print(f"Seed complete: {result}")


if __name__ == "__main__":
    asyncio.run(main())
