from __future__ import annotations

import json
from collections import Counter, defaultdict
from hashlib import sha256
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Extraction, Job, JobRequirement, JobSkill, Run, RunJob, Skill


def _pct(part: int, whole: int) -> float:
    return round((part / whole) * 100, 1) if whole else 0.0


def build_cooccurrence(skill_list: list[dict], top_n: int = 10) -> dict[str, Any]:
    """Pairwise co-occurrence of the top-N skills (Jaccard over job sets)."""
    top = skill_list[:top_n]
    names = [item["skill"] for item in top]
    sets = {item["skill"]: set(item["job_ids"]) for item in top}
    matrix: list[list[int]] = []
    pairs: list[dict[str, Any]] = []
    for i, a in enumerate(names):
        row = []
        for j, b in enumerate(names):
            shared = len(sets[a] & sets[b])
            row.append(shared)
            if i < j and shared:
                union = len(sets[a] | sets[b]) or 1
                pairs.append(
                    {"a": a, "b": b, "count": shared, "jaccard": round(shared / union, 4)}
                )
        matrix.append(row)
    pairs.sort(key=lambda item: (item["count"], item["jaccard"]), reverse=True)
    return {"skills": names, "matrix": matrix, "pairs": pairs[:15]}


def _degree_level(value: str) -> str:
    lowered = value.lower()
    if "phd" in lowered or "doctorate" in lowered:
        return "PhD / Doctorate"
    if "mba" in lowered:
        return "MBA"
    if "master" in lowered or "msc" in lowered:
        return "Master's"
    if "bachelor" in lowered or "bsc" in lowered:
        return "Bachelor's"
    if "diploma" in lowered:
        return "Diploma"
    return "Other / unspecified"


async def build_evidence_pack(run: Run, session: AsyncSession) -> dict[str, Any]:
    job_rows = (
        await session.execute(
            select(Job)
            .join(RunJob, RunJob.job_id == Job.id)
            .where(RunJob.run_id == run.id)
            .order_by(Job.posted_at.desc())
        )
    ).scalars().all()
    if not job_rows:
        raise RuntimeError("No jobs were collected for this run.")

    job_ids = [str(job.id) for job in job_rows]
    corpus_jobs = [
        {
            "id": str(job.id),
            "title": job.title,
            "company": job.company,
            "url": job.url,
            "city": job.city,
            "family": job.job_family,
            "posted_at": job.posted_at.isoformat() if job.posted_at else None,
        }
        for job in job_rows
    ]

    skill_rows = (
        await session.execute(
            select(JobSkill, Skill, Job)
            .join(Skill, Skill.id == JobSkill.skill_id)
            .join(Job, Job.id == JobSkill.job_id)
            .join(Extraction, Extraction.id == JobSkill.extraction_id)
            .join(RunJob, and_(RunJob.job_id == Job.id, RunJob.run_id == run.id))
            .where(JobSkill.evidence_valid.is_(True), Extraction.run_id == run.id)
        )
    ).all()

    stats: dict[str, dict[str, Any]] = {}
    for job_skill, skill, job in skill_rows:
        bucket = stats.setdefault(
            skill.canonical_name,
            {
                "skill": skill.canonical_name,
                "category": skill.category,
                "skill_type": skill.skill_type,
                "job_ids": set(),
                "required_job_ids": set(),
                "preferred_job_ids": set(),
                "quotes": [],
            },
        )
        bucket["job_ids"].add(str(job.id))
        if job_skill.importance == "required":
            bucket["required_job_ids"].add(str(job.id))
        elif job_skill.importance == "preferred":
            bucket["preferred_job_ids"].add(str(job.id))
        if len(bucket["quotes"]) < 3 and job_skill.evidence_quote:
            bucket["quotes"].append(
                {
                    "job_id": str(job.id),
                    "quote": job_skill.evidence_quote,
                    "title": job.title,
                    "company": job.company,
                }
            )

    skill_list = []
    for item in stats.values():
        jobs_count = len(item["job_ids"])
        item["jobs"] = jobs_count
        item["pct"] = _pct(jobs_count, len(job_ids))
        item["required_jobs"] = len(item["required_job_ids"])
        item["preferred_jobs"] = len(item["preferred_job_ids"])
        item["job_ids"] = sorted(item["job_ids"])
        item["required_job_ids"] = sorted(item["required_job_ids"])
        item["preferred_job_ids"] = sorted(item["preferred_job_ids"])
        skill_list.append(item)
    skill_list.sort(key=lambda item: (item["jobs"], item["required_jobs"]), reverse=True)

    evidence_refs: list[dict[str, Any]] = []
    ref_by_id: dict[str, dict[str, Any]] = {}

    def add_ref(
        ref_id: str, label: str, value: Any, metric: str, *, job_ids_ref: list[str] | None = None
    ) -> None:
        ref = {
            "id": ref_id,
            "label": label,
            "value": value,
            "metric": metric,
            "job_ids": job_ids_ref or [],
        }
        evidence_refs.append(ref)
        ref_by_id[ref_id] = ref

    add_ref("ev_corpus", "Relevant ads analyzed", len(job_ids), "corpus_jobs", job_ids_ref=job_ids)

    for index, item in enumerate(skill_list[:20], start=1):
        ref_id = f"ev_skill_{index:03d}"
        item["evidence_ref"] = ref_id
        add_ref(
            ref_id,
            f"Skill demand: {item['skill']}",
            item["jobs"],
            "skill_jobs",
            job_ids_ref=item["job_ids"],
        )

    required_job_ids = sorted(
        {job_id for item in skill_list for job_id in item["required_job_ids"]}
    )
    preferred_job_ids = sorted(
        {job_id for item in skill_list for job_id in item["preferred_job_ids"]}
    )
    add_ref(
        "ev_required",
        "Ads with at least one required skill",
        len(required_job_ids),
        "required_jobs",
        job_ids_ref=required_job_ids,
    )
    add_ref(
        "ev_preferred",
        "Ads with at least one preferred skill",
        len(preferred_job_ids),
        "preferred_jobs",
        job_ids_ref=preferred_job_ids,
    )

    category_jobs: dict[str, set[str]] = defaultdict(set)
    for item in skill_list:
        category_jobs[item["category"]].update(item["job_ids"])
    technical_jobs = category_jobs.get("technical", set())
    non_technical_jobs = category_jobs.get("non_technical", set())
    add_ref(
        "ev_technical",
        "Ads requesting technical skills",
        len(technical_jobs),
        "technical_jobs",
        job_ids_ref=sorted(technical_jobs),
    )
    add_ref(
        "ev_non_technical",
        "Ads requesting non-technical/domain skills",
        len(non_technical_jobs),
        "non_technical_jobs",
        job_ids_ref=sorted(non_technical_jobs),
    )

    companies = Counter(job.company for job in job_rows)
    company_list = [{"company": name, "jobs": count} for name, count in companies.most_common(15)]
    for index, item in enumerate(company_list[:10], start=1):
        ref_id = f"ev_company_{index:03d}"
        item["evidence_ref"] = ref_id
        company_job_ids = [
            str(job.id) for job in job_rows if job.company == item["company"]
        ]
        add_ref(
            ref_id,
            f"Company demand: {item['company']}",
            item["jobs"],
            "company_jobs",
            job_ids_ref=company_job_ids,
        )
    add_ref("ev_companies", "Companies hiring", len(companies), "companies")

    date_values = [job.posted_at for job in job_rows if job.posted_at]
    date_range = {
        "start": min(date_values).date().isoformat() if date_values else None,
        "end": max(date_values).date().isoformat() if date_values else None,
    }
    sources = {str(job.source_id) for job in job_rows}
    add_ref("ev_sources", "Distinct sources", len(sources), "sources")

    requirement_rows = (
        await session.execute(
            select(JobRequirement)
            .join(Extraction, Extraction.id == JobRequirement.extraction_id)
            .join(RunJob, RunJob.job_id == JobRequirement.job_id)
            .where(RunJob.run_id == run.id, Extraction.run_id == run.id)
        )
    ).scalars().all()

    degree_counter: Counter[str] = Counter()
    cert_counter: Counter[str] = Counter()
    language_counter: Counter[str] = Counter()
    degree_jobs: dict[str, set[str]] = defaultdict(set)
    cert_jobs: dict[str, set[str]] = defaultdict(set)
    language_jobs: dict[str, set[str]] = defaultdict(set)
    for requirement in requirement_rows:
        job_id = str(requirement.job_id)
        if requirement.type == "degree":
            level = _degree_level(requirement.value)
            degree_counter[level] += 1
            degree_jobs[level].add(job_id)
        elif requirement.type == "certification":
            cert_counter[requirement.value] += 1
            cert_jobs[requirement.value].add(job_id)
        elif requirement.type == "language":
            language_counter[requirement.value] += 1
            language_jobs[requirement.value].add(job_id)
    add_ref("ev_degrees", "Degree requirements extracted", sum(degree_counter.values()), "degrees")
    add_ref(
        "ev_certifications",
        "Certification requirements extracted",
        sum(cert_counter.values()),
        "certifications",
    )
    degree_list = []
    for index, (level, count) in enumerate(degree_counter.most_common(10), start=1):
        ref_id = f"ev_degree_{index:03d}"
        add_ref(
            ref_id,
            f"Degree requirement: {level}",
            count,
            "degree_jobs",
            job_ids_ref=sorted(degree_jobs[level]),
        )
        degree_list.append({"level": level, "jobs": count, "evidence_ref": ref_id})
    cert_list = []
    for index, (name, count) in enumerate(cert_counter.most_common(10), start=1):
        ref_id = f"ev_cert_{index:03d}"
        add_ref(
            ref_id,
            f"Certification requirement: {name}",
            count,
            "certification_jobs",
            job_ids_ref=sorted(cert_jobs[name]),
        )
        cert_list.append({"name": name, "jobs": count, "evidence_ref": ref_id})
    language_list = []
    for index, (name, count) in enumerate(language_counter.most_common(10), start=1):
        ref_id = f"ev_language_{index:03d}"
        add_ref(
            ref_id,
            f"Language requirement: {name}",
            count,
            "language_jobs",
            job_ids_ref=sorted(language_jobs[name]),
        )
        language_list.append({"name": name, "jobs": count, "evidence_ref": ref_id})

    extraction_rows = (
        await session.execute(
            select(Extraction).where(
                Extraction.run_id == run.id, Extraction.status.in_(("success", "partial"))
            )
        )
    ).scalars().all()
    experience_buckets = {"0-2": 0, "3-5": 0, "6+": 0, "not stated": 0}
    experience_jobs: dict[str, set[str]] = defaultdict(set)
    for extraction in extraction_rows:
        experience = (extraction.payload or {}).get("experience")
        years = experience.get("min_years") if isinstance(experience, dict) else None
        if years is None:
            exp_bucket = "not stated"
        elif years <= 2:
            exp_bucket = "0-2"
        elif years <= 5:
            exp_bucket = "3-5"
        else:
            exp_bucket = "6+"
        experience_buckets[exp_bucket] += 1
        experience_jobs[exp_bucket].add(str(extraction.job_id))
    stated_experience_jobs = set().union(
        *(experience_jobs[key] for key in ("0-2", "3-5", "6+"))
    )
    add_ref(
        "ev_experience",
        "Ads with a stated experience minimum",
        len(stated_experience_jobs),
        "experience",
        job_ids_ref=sorted(stated_experience_jobs),
    )
    experience_details = []
    for index, (exp_bucket, count) in enumerate(experience_buckets.items(), start=1):
        ref_id = f"ev_experience_{index:03d}"
        add_ref(
            ref_id,
            f"Experience bucket: {exp_bucket} years",
            count,
            "experience_bucket",
            job_ids_ref=sorted(experience_jobs[exp_bucket]),
        )
        experience_details.append(
            {"bucket": exp_bucket, "jobs": count, "evidence_ref": ref_id}
        )

    salary_count = sum(1 for job in job_rows if job.salary_min is not None)
    add_ref("ev_salary", "Ads with stated salary", salary_count, "salary")

    warnings: list[str] = []
    collect_warnings = (run.stats or {}).get("collect", {}).get("warnings", [])
    for warning in collect_warnings:
        if warning not in warnings:
            warnings.append(warning)
    if len(job_ids) < 10:
        warnings.append(
            f"Only {len(job_ids)} relevant ads were available; treat the findings as directional."
        )
    if salary_count / len(job_ids) < 0.2:
        warnings.append(
            f"Salary was stated in only {salary_count} of {len(job_ids)} ads, "
            "so compensation is not analyzed."
        )
    if len(sources) < 2:
        warnings.append("The corpus comes from a single source; source diversity is limited.")
    arabic_jobs = sum(1 for job in job_rows if job.language == "ar")
    if arabic_jobs:
        warnings.append(
            f"{arabic_jobs} ad(s) are in Arabic; extracted with Arabic alias mapping "
            "and reported with per-language evaluation."
        )

    corpus = {
        "jobs": len(job_ids),
        "companies": len(companies),
        "sources": len(sources),
        "date_range": date_range,
        "salary_coverage": salary_count,
        "snapshot": True,
    }

    pack: dict[str, Any] = {
        "query": run.query,
        "generated_at": run.created_at.isoformat() if run.created_at else None,
        "corpus": corpus,
        "corpus_jobs": corpus_jobs,
        "skills": skill_list,
        "required_jobs": len(required_job_ids),
        "preferred_jobs": len(preferred_job_ids),
        "categories": {
            "technical_jobs": len(technical_jobs),
            "non_technical_jobs": len(non_technical_jobs),
            "technical_mentions": sum(
                len(item["job_ids"]) for item in skill_list if item["category"] == "technical"
            ),
            "non_technical_mentions": sum(
                len(item["job_ids"]) for item in skill_list if item["category"] == "non_technical"
            ),
        },
        "companies": company_list,
        "cooccurrence": build_cooccurrence(skill_list),
        "degrees": degree_list,
        "certifications": cert_list,
        "languages": language_list,
        "experience": experience_buckets,
        "experience_details": experience_details,
        "samples": [
            sample
            for item in skill_list[:5]
            for sample in item["quotes"][:2]
        ][:10],
        "warnings": warnings,
        "evidence_refs": evidence_refs,
    }
    pack["evidence_ref_map"] = ref_by_id
    pack["pack_hash"] = sha256(
        json.dumps(pack, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()
    return pack
