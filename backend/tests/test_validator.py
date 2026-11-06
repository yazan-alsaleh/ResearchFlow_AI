from __future__ import annotations

from app.agents.intelligence.validator import validate_report


def make_pack() -> dict:
    return {
        "corpus": {"jobs": 2, "companies": 1, "sources": 1},
        "evidence_refs": [
            {
                "id": "ev_corpus",
                "label": "Relevant ads analyzed",
                "value": 2,
                "metric": "corpus_jobs",
                "job_ids": ["job-a", "job-b"],
            },
            {
                "id": "ev_skill_001",
                "label": "Skill demand: Python",
                "value": 1,
                "metric": "skill_jobs",
                "job_ids": ["job-a"],
            },
            {
                "id": "ev_required",
                "label": "Ads with at least one required skill",
                "value": 2,
                "metric": "required_jobs",
                "job_ids": ["job-a", "job-b"],
            },
        ],
    }


def make_report() -> dict:
    return {
        "corpus": {"jobs": 2},
        "executive_summary": [
            {"text": "2 relevant ads were analyzed.", "evidence_ref": "ev_corpus"},
            {"text": "Python appears in 1 of 2 ads.", "evidence_ref": "ev_skill_001"},
        ],
        "sections": [
            {
                "heading": "Requirements",
                "claims": [
                    {"text": "2 ads require at least one skill.", "evidence_ref": "ev_required"}
                ],
            }
        ],
        "recommendations": [
            {
                "skill": "Python",
                "rationale": "Appears in 1 of 2 ads.",
                "evidence_ref": "ev_skill_001",
            }
        ],
    }


def test_valid_report_passes():
    status, violations = validate_report(make_report(), make_pack())
    assert status == "verified"
    assert violations == []


def test_unknown_evidence_reference_fails():
    report = make_report()
    report["executive_summary"][0]["evidence_ref"] = "ev_missing"
    status, violations = validate_report(report, make_pack())
    assert status == "partial"
    assert any("unknown evidence_ref" in item for item in violations)


def test_missing_evidence_reference_fails():
    report = make_report()
    report["sections"][0]["claims"][0]["evidence_ref"] = None
    status, violations = validate_report(report, make_pack())
    assert status == "partial"
    assert any("no evidence_ref" in item for item in violations)


def test_number_not_in_evidence_pack_fails():
    report = make_report()
    report["executive_summary"][1]["text"] = "Python appears in 99 of 2 ads."
    status, violations = validate_report(report, make_pack())
    assert status == "partial"
    assert any("99" in item for item in violations)


def test_evidence_citing_job_outside_corpus_fails():
    pack = make_pack()
    pack["evidence_refs"][1]["job_ids"] = ["job-outside"]
    status, violations = validate_report(make_report(), pack)
    assert status == "partial"
    assert any("outside the corpus" in item for item in violations)


def test_corpus_mismatch_fails():
    report = make_report()
    report["corpus"]["jobs"] = 3
    status, violations = validate_report(report, pack=make_pack())
    assert status == "partial"
    assert any("corpus job count" in item for item in violations)
