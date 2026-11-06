from __future__ import annotations

from app.agents.intelligence.report import build_deterministic_report
from app.agents.intelligence.validator import validate_report
from app.db.models import Run


def skill(index: int, name: str, jobs: int, ref: str) -> dict:
    return {
        "skill": name,
        "category": "technical",
        "skill_type": "language",
        "jobs": jobs,
        "pct": 50.0,
        "required_jobs": jobs,
        "preferred_jobs": 0,
        "evidence_ref": ref,
    }


def make_pack() -> dict:
    return {
        "query": "Data Analyst",
        "corpus": {
            "jobs": 2,
            "companies": 1,
            "sources": 1,
            "date_range": {"start": "2026-01-01", "end": "2026-01-31"},
            "salary_coverage": 0,
            "snapshot": True,
        },
        "skills": [skill(1, "Python", 2, "ev_skill_001")],
        "required_jobs": 2,
        "preferred_jobs": 1,
        "categories": {"technical_jobs": 2, "non_technical_jobs": 1},
        "companies": [{"company": "Example Co", "jobs": 2, "evidence_ref": "ev_company_001"}],
        "degrees": [{"level": "Bachelor's", "jobs": 2, "evidence_ref": "ev_degree_001"}],
        "certifications": [],
        "languages": [],
        "experience": {"0-2": 1, "3-5": 1, "6+": 0, "not stated": 0},
        "experience_details": [
            {"bucket": "0-2", "jobs": 1, "evidence_ref": "ev_experience_001"},
            {"bucket": "3-5", "jobs": 1, "evidence_ref": "ev_experience_002"},
            {"bucket": "6+", "jobs": 0, "evidence_ref": "ev_experience_003"},
            {"bucket": "not stated", "jobs": 0, "evidence_ref": "ev_experience_004"},
        ],
        "warnings": [],
        "evidence_refs": [
            {"id": "ev_corpus", "value": 2, "metric": "corpus_jobs", "job_ids": []},
            {"id": "ev_skill_001", "value": 2, "metric": "skill_jobs", "job_ids": []},
            {"id": "ev_required", "value": 2, "metric": "required_jobs", "job_ids": []},
            {"id": "ev_preferred", "value": 1, "metric": "preferred_jobs", "job_ids": []},
            {"id": "ev_technical", "value": 2, "metric": "technical_jobs", "job_ids": []},
            {"id": "ev_non_technical", "value": 1, "metric": "non_technical_jobs", "job_ids": []},
            {"id": "ev_company_001", "value": 2, "metric": "company_jobs", "job_ids": []},
            {"id": "ev_degree_001", "value": 2, "metric": "degree_jobs", "job_ids": []},
            {"id": "ev_experience_001", "value": 1, "metric": "experience_bucket", "job_ids": []},
            {"id": "ev_experience_002", "value": 1, "metric": "experience_bucket", "job_ids": []},
            {"id": "ev_experience_003", "value": 0, "metric": "experience_bucket", "job_ids": []},
            {"id": "ev_experience_004", "value": 0, "metric": "experience_bucket", "job_ids": []},
        ],
        "corpus_jobs": [],
    }


def test_deterministic_report_is_valid_and_cited():
    run = Run(query="Data Analyst", normalized_query="data analyst")
    report = build_deterministic_report(run, make_pack())
    status, violations = validate_report(report, make_pack())
    assert status == "verified", violations
    assert report["executive_summary"]
    assert report["recommendations"][0]["skill"] == "Python"
    assert report["insights"]["top_skills"][0]["skill"] == "Python"
    assert any("snapshot" in caveat.lower() for caveat in report["caveats"])


def test_report_includes_salary_and_source_caveats():
    run = Run(query="Data Analyst", normalized_query="data analyst")
    pack = make_pack()
    pack["warnings"] = ["The corpus comes from a single source; source diversity is limited."]
    report = build_deterministic_report(run, pack)
    assert report["caveats"][0] == pack["warnings"][0]
