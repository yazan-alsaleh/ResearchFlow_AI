from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from math import log

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Job, Run, RunJob

STOPWORDS = {"a", "an", "and", "at", "for", "in", "of", "on", "the", "to", "with"}
GENERIC_TITLE_TOKENS = {
    "administrator",
    "analyst",
    "assistant",
    "associate",
    "consultant",
    "coordinator",
    "developer",
    "director",
    "engineer",
    "executive",
    "graduate",
    "head",
    "intern",
    "junior",
    "lead",
    "manager",
    "officer",
    "principal",
    "senior",
    "specialist",
    "staff",
    "trainee",
}


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9+#]+", text.lower())


def _title_tokens(text: str) -> list[str]:
    return [token for token in _tokens(text) if token not in STOPWORDS]


class SeedCollector:
    """MVP collector backed by the seeded corpus.

    The production collector adds robots-aware fetchers and JSON-LD/ATS adapters.
    This class keeps the pipeline demonstrable offline and deterministic.
    """

    name = "seed_collector"

    async def collect(self, run: Run, session: AsyncSession) -> dict:
        jobs = (
            await session.execute(
                select(Job).where(Job.is_active.is_(True)).order_by(Job.collected_at.desc())
            )
        ).scalars().all()

        if not jobs:
            raise RuntimeError("The job corpus is empty. Run `python -m scripts.seed` first.")

        idf = self._title_idf(jobs)
        scored = sorted(
            ((self._relevance(job, run.query, idf), job) for job in jobs),
            key=lambda item: item[0],
            reverse=True,
        )
        strong = [item for item in scored if item[0] >= settings.min_relevance]
        warnings: list[str] = []
        selected = strong[: settings.max_jobs_per_run]
        expanded = False

        if not strong:
            selected = scored[:3]
            warnings.append(
                "No close title match was found; the report uses the closest available "
                "Qatar ads."
            )
        elif len(selected) < 3:
            family = selected[0][1].job_family
            target = max(3, min(6, settings.max_jobs_per_run))
            chosen = {item[1].id for item in selected}
            for item in scored:
                if len(selected) >= target:
                    break
                if item[1].job_family != family or item[1].id in chosen:
                    continue
                selected.append(item)
                chosen.add(item[1].id)
            if len(selected) > len(strong):
                expanded = True
                warnings.append(
                    f"Only {len(strong)} close title match(es) were found; the report also "
                    f"includes related {family.replace('_', ' ')} roles."
                )

        selected.sort(key=lambda item: item[0], reverse=True)
        if len(selected) < 3:
            warnings.append(
                f"Only {len(selected)} relevant ad(s) were found in the demo corpus; "
                "treat the findings as directional."
            )

        existing = {
            row.job_id
            for row in (
                await session.execute(select(RunJob).where(RunJob.run_id == run.id))
            ).scalars()
        }
        for score, job in selected:
            if job.id not in existing:
                session.add(
                    RunJob(
                        run_id=run.id,
                        job_id=job.id,
                        relevance_score=max(0.0, min(1.0, score)),
                    )
                )

        await session.flush()
        return {
            "fetched": len(jobs),
            "selected": len(selected),
            "strong_matches": len(strong),
            "expanded_family": expanded,
            "warnings": warnings,
        }

    @staticmethod
    def _title_idf(jobs: Sequence[Job]) -> dict[str, float]:
        document_frequency: Counter[str] = Counter()
        for job in jobs:
            document_frequency.update(set(_title_tokens(job.title)))
        total = len(jobs)
        return {
            token: log((total + 1) / (count + 1)) + 1
            for token, count in document_frequency.items()
        }

    @staticmethod
    def _weight(token: str, idf: dict[str, float]) -> float:
        weight = idf.get(token, 1.0)
        if token in GENERIC_TITLE_TOKENS:
            weight *= 0.35
        return weight

    @staticmethod
    def _relevance(job: Job, query: str, idf: dict[str, float] | None = None) -> float:
        idf = idf or {}
        query_tokens = list(dict.fromkeys(_title_tokens(query)))
        if not query_tokens:
            return 0.0

        weights = {token: SeedCollector._weight(token, idf) for token in query_tokens}
        total = sum(weights.values())
        title_tokens = set(_title_tokens(job.title))
        title_coverage = sum(
            weight for token, weight in weights.items() if token in title_tokens
        ) / total

        normalized_query = " ".join(_title_tokens(query))
        normalized_title = " ".join(_title_tokens(job.title))
        if normalized_query and normalized_query in normalized_title:
            title_coverage = 1.0

        if title_coverage <= 0:
            return 0.0

        distinctive = [token for token in query_tokens if token not in GENERIC_TITLE_TOKENS]
        description_coverage = 0.0
        if distinctive:
            description_tokens = set(_tokens(job.description))
            distinctive_total = sum(weights[token] for token in distinctive)
            description_coverage = (
                sum(
                    weights[token]
                    for token in distinctive
                    if token in description_tokens
                )
                / distinctive_total
            )

        return min(1.0, title_coverage * 0.85 + description_coverage * 0.15)


def seed_query_titles() -> list[str]:
    return [
        "AI Engineer",
        "Data Analyst",
        "Accountant",
        "Civil Engineer",
        "Marketing Manager",
        "HR Specialist",
        "Registered Nurse",
        "Teacher",
        "Project Manager",
        "Business Analyst",
    ]


def default_date_range(days: int = 60) -> tuple[datetime, datetime]:
    end = datetime.now(UTC)
    return end - timedelta(days=days), end
