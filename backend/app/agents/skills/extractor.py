from __future__ import annotations

import re
from typing import Any

from app.agents.skills.taxonomy import (
    SkillDefinition,
    find_skill_mentions,
    match_canonical,
    normalize_text,
)
from app.db.models import Job

REQUIRED_CUES = (
    "required",
    "must",
    "essential",
    "minimum",
    "requires",
    "requirement",
    "mandatory",
)
PREFERRED_CUES = (
    "preferred",
    "plus",
    "advantage",
    "desirable",
    "nice to have",
    "beneficial",
    "ideally",
)
PROTECTED_ATTRIBUTES = re.compile(
    r"\b(nationality|gender|male|female|marital status|religion|age)\b", re.IGNORECASE
)


def split_sentences(text: str) -> list[tuple[int, int, str]]:
    normalized = normalize_text(text)
    spans: list[tuple[int, int, str]] = []
    start = 0
    for match in re.finditer(r"(?<=[.!?])\s+", normalized):
        end = match.start()
        sentence = normalized[start:end].strip()
        if sentence:
            spans.append((start, end, sentence))
        start = match.end()
    if start < len(normalized):
        sentence = normalized[start:].strip()
        if sentence:
            spans.append((start, len(normalized), sentence))
    return spans


def _sentence_at(spans: list[tuple[int, int, str]], position: int) -> str:
    for start, end, sentence in spans:
        if start <= position < end:
            return sentence
    return spans[-1][2] if spans else ""


def _importance(sentence: str) -> str:
    if any(cue in sentence for cue in REQUIRED_CUES):
        return "required"
    if any(cue in sentence for cue in PREFERRED_CUES):
        return "preferred"
    return "mentioned"


def _confidence(importance: str) -> float:
    return {"required": 0.92, "preferred": 0.82, "mentioned": 0.62}.get(importance, 0.5)


def _trim_quote(sentence: str, limit: int = 320) -> str:
    return sentence if len(sentence) <= limit else sentence[: limit - 3].rstrip() + "..."


def _degree_extraction(text: str, spans: list[tuple[int, int, str]]) -> list[dict]:
    results: list[dict] = []
    pattern = re.compile(
        r"\b(bachelor'?s?|master'?s?|bsc|msc|mba|phd|doctorate|diploma)\b[^.!?]{0,160}",
        re.IGNORECASE,
    )
    for match in pattern.finditer(normalize_text(text)):
        sentence = _sentence_at(spans, match.start())
        if not sentence:
            continue
        value = _trim_quote(sentence)
        if any(item["value"] == value for item in results):
            continue
        results.append(
            {
                "type": "degree",
                "value": value,
                "required": "preferred" not in sentence,
                "evidence_quote": value,
            }
        )
    return results


def _experience_extraction(text: str, spans: list[tuple[int, int, str]]) -> dict | None:
    pattern = re.compile(r"(\d{1,2})\s*\+?\s*(?:years|yrs)", re.IGNORECASE)
    match = pattern.search(normalize_text(text))
    if not match:
        return None
    sentence = _sentence_at(spans, match.start())
    return {
        "min_years": int(match.group(1)),
        "max_years": None,
        "evidence_quote": _trim_quote(sentence),
    }


def _language_requirements(skills: list[dict]) -> list[dict]:
    languages = []
    for skill in skills:
        if skill["skill_type"] == "spoken_language":
            languages.append(
                {
                    "language": skill["name"],
                    "required": skill["importance"] == "required",
                    "evidence_quote": skill["evidence_quote"],
                }
            )
    return languages


def extract_deterministic(job: Job) -> dict:
    text = normalize_text(job.description)
    spans = split_sentences(job.description)
    mentions = find_skill_mentions(job.description)

    by_skill: dict[str, dict] = {}
    for skill, start, _end, _alias in mentions:
        sentence = _sentence_at(spans, start)
        if not sentence:
            continue
        importance = _importance(sentence)
        quote = _trim_quote(sentence)
        existing = by_skill.get(skill.name)
        rank = {"required": 3, "preferred": 2, "mentioned": 1}
        if existing and rank[existing["importance"]] >= rank[importance]:
            continue
        by_skill[skill.name] = {
            "name": skill.name,
            "canonical_name": skill.name,
            "category": skill.category,
            "skill_type": skill.skill_type,
            "importance": importance,
            "evidence_quote": quote,
            "confidence": _confidence(importance),
        }

    all_skills = sorted(
        by_skill.values(),
        key=lambda item: (
            {"required": 0, "preferred": 1, "mentioned": 2}[item["importance"]],
            item["name"],
        ),
    )
    languages = _language_requirements(all_skills)
    skills = [item for item in all_skills if item["skill_type"] != "spoken_language"]
    qualifications = _degree_extraction(job.description, spans)
    certificates = [
        {
            "name": skill["name"],
            "required": skill["importance"] == "required",
            "evidence_quote": skill["evidence_quote"],
        }
        for skill in skills
        if skill["category"] == "certification"
    ]
    experience = _experience_extraction(job.description, spans)
    soft_skills = [skill for skill in skills if skill["category"] == "soft_skill"]

    total_items = len(skills) + len(qualifications) + len(certificates) + (1 if experience else 0)
    valid_items = sum(1 for skill in skills if skill["evidence_quote"] in text)
    valid_items += sum(1 for item in qualifications if item["evidence_quote"] in text)
    valid_items += sum(1 for item in certificates if item["evidence_quote"] in text)
    valid_items += 1 if experience and experience["evidence_quote"] in text else 0

    return {
        "job_id": str(job.id),
        "language": job.language,
        "job_family": job.job_family,
        "seniority": _seniority(job.title),
        "skills": skills,
        "qualifications": qualifications,
        "certifications": certificates,
        "experience": experience,
        "languages": languages,
        "soft_skills": [
            {
                "name": item["name"],
                "importance": item["importance"],
                "evidence_quote": item["evidence_quote"],
            }
            for item in soft_skills
        ],
        "flags": {
            "truncated": len(job.description) < 200,
            "ambiguous": len(skills) == 0,
            "contains_protected_attributes": bool(PROTECTED_ATTRIBUTES.search(job.description)),
            "fallback": False,
        },
        "evidence_coverage": (valid_items / total_items) if total_items else 0.0,
    }


def _seniority(title: str) -> str:
    lowered = title.lower()
    for label in (
        "intern",
        "graduate",
        "junior",
        "senior",
        "lead",
        "principal",
        "manager",
        "director",
        "head",
    ):
        if label in lowered:
            return label
    return "mid"


def normalize_llm_payload(job: Job, payload: dict[str, Any]) -> dict:
    """Validate an LLM extraction and force it into the same shape as the deterministic one."""
    text = normalize_text(job.description)
    spans = split_sentences(job.description)
    normalized_skills: list[dict] = []

    for item in payload.get("skills", []):
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        definition: SkillDefinition | None = match_canonical(name)
        canonical = definition.name if definition else name
        quote = str(item.get("evidence_quote", "")).strip()
        valid = bool(quote) and normalize_text(quote) in text
        if not valid and definition:
            for skill, start, _end, _alias in find_skill_mentions(job.description):
                if skill.name == definition.name:
                    quote = _trim_quote(_sentence_at(spans, start))
                    valid = True
                    break
        importance = str(item.get("importance", "mentioned")).lower()
        if importance not in {"required", "preferred", "mentioned"}:
            importance = _importance(normalize_text(quote))
        normalized_skills.append(
            {
                "name": canonical,
                "canonical_name": canonical,
                "category": (
                    definition.category
                    if definition
                    else item.get("category", "technical")
                ),
                "skill_type": (
                    definition.skill_type
                    if definition
                    else item.get("skill_type", "tool")
                ),
                "importance": importance,
                "evidence_quote": quote,
                "confidence": float(item.get("confidence", _confidence(importance))),
                "evidence_valid": valid,
            }
        )

    languages_payload = [
        {
            "language": skill["name"],
            "required": skill["importance"] == "required",
            "evidence_quote": skill["evidence_quote"],
        }
        for skill in normalized_skills
        if skill["skill_type"] == "spoken_language"
    ]
    normalized_skills = [
        skill for skill in normalized_skills if skill["skill_type"] != "spoken_language"
    ]

    if len(normalized_skills) < 3:
        raise ValueError("LLM extraction did not return enough usable skills")

    qualifications = []
    for item in payload.get("qualifications", []):
        quote = str(item.get("evidence_quote", "")).strip()
        if quote and normalize_text(quote) in text:
            qualifications.append(
                {
                    "type": str(item.get("type", "degree")),
                    "value": str(item.get("value", quote)),
                    "required": bool(item.get("required", True)),
                    "evidence_quote": _trim_quote(normalize_text(quote)),
                }
            )

    experience = payload.get("experience")
    if isinstance(experience, dict):
        quote = str(experience.get("evidence_quote", "")).strip()
        if quote and normalize_text(quote) in text:
            experience = {
                "min_years": experience.get("min_years"),
                "max_years": experience.get("max_years"),
                "evidence_quote": _trim_quote(normalize_text(quote)),
            }
        else:
            experience = _experience_extraction(job.description, spans)
    else:
        experience = _experience_extraction(job.description, spans)

    certificates = [
        {
            "name": skill["name"],
            "required": skill["importance"] == "required",
            "evidence_quote": skill["evidence_quote"],
        }
        for skill in normalized_skills
        if skill["category"] == "certification"
    ]
    valid_skills = [skill for skill in normalized_skills if skill.get("evidence_valid", False)]

    total_items = len(normalized_skills) + len(qualifications) + (1 if experience else 0)
    valid_items = len(valid_skills) + len(qualifications) + (1 if experience else 0)

    return {
        "job_id": str(job.id),
        "language": job.language,
        "job_family": job.job_family,
        "seniority": payload.get("seniority") or _seniority(job.title),
        "skills": normalized_skills,
        "qualifications": qualifications,
        "certifications": certificates,
        "experience": experience,
        "languages": languages_payload,
        "soft_skills": [
            {
                "name": skill["name"],
                "importance": skill["importance"],
                "evidence_quote": skill["evidence_quote"],
            }
            for skill in normalized_skills
            if skill["category"] == "soft_skill"
        ],
        "flags": {
            "truncated": len(job.description) < 200,
            "ambiguous": len(normalized_skills) == 0,
            "contains_protected_attributes": bool(PROTECTED_ATTRIBUTES.search(job.description)),
            "fallback": False,
            "llm": True,
        },
        "evidence_coverage": (valid_items / total_items) if total_items else 0.0,
    }
