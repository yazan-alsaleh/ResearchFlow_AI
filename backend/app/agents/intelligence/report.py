from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.db.models import Run


def _claim(text: str, evidence_ref: str) -> dict:
    return {"text": text, "evidence_ref": evidence_ref}


def _effort(skill_type: str) -> str:
    if skill_type == "certification":
        return "high"
    if skill_type in {
        "language",
        "spoken_language",
        "framework",
        "platform",
        "domain_knowledge",
    }:
        return "medium"
    return "low"


def build_deterministic_report(run: Run, pack: dict[str, Any]) -> dict[str, Any]:
    corpus = pack["corpus"]
    skills = pack["skills"]
    top = skills[:8]
    total = corpus["jobs"]

    summary = [
        _claim(
            f"{total} relevant Qatar ads from {corpus['companies']} companies were analyzed "
            f"for the title '{run.query}'.",
            "ev_corpus",
        )
    ]
    if top:
        leader = top[0]
        summary.append(
            _claim(
                f"{leader['skill']} is the most requested skill, appearing in "
                f"{leader['jobs']} of {total} ads ({leader['pct']}%).",
                leader["evidence_ref"],
            )
        )
    summary.append(
        _claim(
            f"{pack['required_jobs']} ads list at least one required skill, while "
            f"{pack['preferred_jobs']} ads mention at least one preferred skill.",
            "ev_required",
        )
    )
    summary.append(
        _claim(
            f"{pack['categories']['technical_jobs']} ads request technical skills; "
            f"{pack['categories']['non_technical_jobs']} request non-technical or domain skills.",
            "ev_technical",
        )
    )

    sections: list[dict[str, Any]] = []
    if top:
        sections.append(
            {
                "heading": "Most requested skills",
                "claims": [
                    _claim(
                        f"{item['skill']}: {item['jobs']} ads ({item['pct']}%), "
                        f"with {item['required_jobs']} listing it as required.",
                        item["evidence_ref"],
                    )
                    for item in top
                ],
            }
        )

    sections.append(
        {
            "heading": "How requirements are framed",
            "claims": [
                _claim(
                    f"{pack['required_jobs']} of {total} ads use required language; "
                    f"{pack['preferred_jobs']} use preferred language.",
                    "ev_required",
                )
            ],
        }
    )
    sections.append(
        {
            "heading": "Technical and non-technical demand",
            "claims": [
                _claim(
                    f"{pack['categories']['technical_jobs']} ads request technical skills, "
                    f"compared with {pack['categories']['non_technical_jobs']} that request "
                    "non-technical or domain skills.",
                    "ev_technical",
                )
            ],
        }
    )

    qualification_claims = []
    for item in pack.get("degrees", [])[:5]:
        qualification_claims.append(
            _claim(f"{item['level']}: {item['jobs']} ads.", item["evidence_ref"])
        )
    for item in pack.get("certifications", [])[:5]:
        qualification_claims.append(
            _claim(f"{item['name']}: {item['jobs']} ads.", item["evidence_ref"])
        )
    if qualification_claims:
        sections.append(
            {"heading": "Degrees and certifications", "claims": qualification_claims}
        )

    experience_claims = [
        _claim(f"{item['bucket']} years: {item['jobs']} ads.", item["evidence_ref"])
        for item in pack.get("experience_details", [])
        if item["bucket"] != "not stated"
    ]
    if experience_claims:
        sections.append({"heading": "Experience requirements", "claims": experience_claims})

    company_claims = [
        _claim(f"{item['company']}: {item['jobs']} ads.", item["evidence_ref"])
        for item in pack.get("companies", [])[:5]
    ]
    if company_claims:
        sections.append({"heading": "Where the demand is", "claims": company_claims})

    recommendations = []
    for priority, item in enumerate(top[:5], start=1):
        recommendations.append(
            {
                "priority": priority,
                "skill": item["skill"],
                "rationale": (
                    f"Appears in {item['jobs']} of {total} ads ({item['pct']}%), "
                    f"including {item['required_jobs']} where it is required."
                ),
                "effort": _effort(item["skill_type"]),
                "evidence_ref": item["evidence_ref"],
            }
        )

    caveats = list(pack.get("warnings", []))
    caveats.append(
        "This is a snapshot of currently open ads, not a longitudinal trend. "
        "A trend claim requires at least two collection waves."
    )
    if corpus.get("date_range", {}).get("start"):
        caveats.append(
            "Posting dates span "
            f"{corpus['date_range']['start']} to {corpus['date_range']['end']}."
        )
    caveats.append("Only English-language extraction is enabled in the MVP.")

    return {
        "title": f"{run.query} — Qatar Market Snapshot",
        "query": run.query,
        "generated_at": datetime.now(UTC).isoformat(),
        "corpus": corpus,
        "executive_summary": summary,
        "sections": sections,
        "recommendations": recommendations,
        "caveats": caveats,
        "insights": {
            "top_skills": top,
            "degrees": pack.get("degrees", []),
            "certifications": pack.get("certifications", []),
            "experience": pack.get("experience_details", []),
            "companies": pack.get("companies", [])[:8],
            "languages": pack.get("languages", []),
        },
        "evidence_refs": pack.get("evidence_refs", []),
        "evidence_jobs": {job["id"]: job for job in pack.get("corpus_jobs", [])},
        "validation": {"status": "pending", "violations": []},
    }
