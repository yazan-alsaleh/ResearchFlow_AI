from __future__ import annotations

import uuid

from app.agents.skills.extractor import (
    _seniority,
    extract_deterministic,
    normalize_llm_payload,
)
from app.db.models import Job

DESCRIPTION = (
    "Required: 3+ years of experience with Python, SQL, and machine learning. "
    "Experience with Docker is preferred. "
    "A Bachelor's degree in Computer Science is required. "
    "NEBOSH certification is preferred. "
    "Fluent English is required."
)


def make_job(description: str = DESCRIPTION) -> Job:
    return Job(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        url="https://example.com/jobs/1",
        url_hash="hash",
        title="Senior Data Scientist",
        title_normalized="senior data scientist",
        company="Example Co",
        company_normalized="example co",
        location_text="Doha, Qatar",
        description=description,
        description_hash="description-hash",
        fingerprint="fingerprint",
        job_family="software_data",
        language="en",
    )


def test_extract_deterministic_splits_required_and_preferred():
    payload = extract_deterministic(make_job())
    by_name = {item["name"]: item for item in payload["skills"]}

    assert by_name["Python"]["importance"] == "required"
    assert by_name["SQL"]["importance"] == "required"
    assert by_name["Machine Learning"]["importance"] == "required"
    assert by_name["Docker"]["importance"] == "preferred"
    assert by_name["NEBOSH"]["importance"] == "preferred"

    for item in payload["skills"]:
        assert item["evidence_quote"]
        assert item["evidence_quote"] in DESCRIPTION.lower()


def test_extract_deterministic_reads_experience_degree_and_language():
    payload = extract_deterministic(make_job())
    assert payload["experience"]["min_years"] == 3
    assert payload["experience"]["evidence_quote"]
    assert any(item["type"] == "degree" for item in payload["qualifications"])
    assert any(item["language"] == "English" for item in payload["languages"])
    assert payload["seniority"] == "senior"
    assert payload["flags"]["contains_protected_attributes"] is False
    assert payload["evidence_coverage"] > 0.9


def test_extract_deterministic_flags_protected_attributes():
    payload = extract_deterministic(
        make_job("Required: Python. Male candidates only. Bachelor's degree required.")
    )
    assert payload["flags"]["contains_protected_attributes"] is True


def test_extract_deterministic_handles_empty_text():
    payload = extract_deterministic(make_job("No requirements listed."))
    assert payload["skills"] == []
    assert payload["flags"]["ambiguous"] is True
    assert payload["experience"] is None


def test_normalize_llm_payload_rejects_unsupported_quotes():
    payload = normalize_llm_payload(
        make_job(),
        {
            "skills": [
                {
                    "name": "Python",
                    "importance": "required",
                    "evidence_quote": "Required: 3+ years of experience with Python, SQL",
                },
                {
                    "name": "Kubernetes",
                    "importance": "required",
                    "evidence_quote": "Kubernetes is mandatory.",
                },
                {
                    "name": "SQL",
                    "importance": "required",
                    "evidence_quote": "SQL",
                },
            ]
        },
    )
    by_name = {item["name"]: item for item in payload["skills"]}
    assert by_name["Python"]["evidence_valid"] is True
    assert by_name["SQL"]["evidence_valid"] is True
    assert by_name["Kubernetes"]["evidence_valid"] is False


def test_seniority_labels():
    assert _seniority("Junior Analyst") == "junior"
    assert _seniority("Head of Data") == "head"
    assert _seniority("Data Analyst") == "mid"
