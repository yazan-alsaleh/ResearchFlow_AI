from __future__ import annotations

import uuid

from app.agents.skills.arabic import (
    detect_language,
    find_arabic_skill_mentions,
    normalize_arabic,
)
from app.agents.skills.extractor import extract_deterministic
from app.db.models import Job


def test_detect_language():
    assert detect_language("Required: Python experience") == "en"
    assert detect_language("مطلوب خبرة في بايثون") == "ar"
    assert detect_language("") == "en"


def test_normalize_arabic_unifies_orthography():
    assert normalize_arabic("الإنجليزية") == "الانجليزيه"
    assert normalize_arabic("مَطْلُوب") == "مطلوب"
    assert " " not in normalize_arabic("  محاسبة  ")


def test_find_arabic_skill_mentions_maps_to_canonical():
    mentions = find_arabic_skill_mentions("مطلوب خبرة في بايثون ومعرفة المحاسبة")
    names = {canonical for canonical, _s, _e, _a in mentions}
    assert {"Python", "Accounting"} <= names


def make_job(description: str, language: str = "ar") -> Job:
    return Job(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        url="https://example.com/jobs/arabic",
        url_hash="hash",
        title="محاسب",
        title_normalized="محاسب",
        company="Example Co",
        company_normalized="example co",
        location_text="الدوحة",
        description=description,
        description_hash="description-hash",
        fingerprint="fingerprint",
        job_family="finance",
        language=language,
    )


def test_extract_deterministic_handles_arabic_ads_with_arabic_quotes():
    description = (
        "مطلوب: 3 سنوات خبرة في المحاسبة ومعرفة المعايير الدولية. "
        "خبرة في برنامج اكسل ضرورية. يفضل معرفة ضريبة القيمة المضافة. "
        "التواصل الجيد اساسى."
    )
    payload = extract_deterministic(make_job(description))
    by_name = {item["name"]: item for item in payload["skills"]}
    assert by_name["Accounting"]["importance"] == "required"
    assert by_name["Excel"]["importance"] == "required"
    assert by_name["VAT"]["importance"] == "preferred"
    # Evidence quotes stay in Arabic with valid verbatim content.
    assert by_name["Accounting"]["evidence_quote"]
    assert payload["language"] == "ar"


def test_extract_deterministic_english_still_works():
    description = "Required: Python experience. Docker is preferred."
    payload = extract_deterministic(make_job(description, language="en"))
    by_name = {item["name"]: item for item in payload["skills"]}
    assert by_name["Python"]["importance"] == "required"
    assert by_name["Docker"]["importance"] == "preferred"
