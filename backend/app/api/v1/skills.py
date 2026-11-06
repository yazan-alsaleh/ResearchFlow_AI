from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.db.models import Skill

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("")
async def list_skills(
    category: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    statement = select(Skill).where(Skill.is_active.is_(True)).order_by(Skill.canonical_name)
    if category:
        statement = statement.where(Skill.category == category)
    skills = (await session.execute(statement)).scalars().all()
    return {
        "items": [
            {
                "id": str(skill.id),
                "canonical_name": skill.canonical_name,
                "slug": skill.slug,
                "category": skill.category,
                "skill_type": skill.skill_type,
            }
            for skill in skills
        ]
    }
