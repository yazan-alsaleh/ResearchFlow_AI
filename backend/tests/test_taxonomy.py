from __future__ import annotations

from app.agents.skills.taxonomy import (
    find_skill_mentions,
    load_taxonomy,
    match_canonical,
)


def test_taxonomy_loads_seed_skills():
    taxonomy = load_taxonomy()
    assert len(taxonomy) >= 190
    names = {skill.name for skill in taxonomy}
    assert {"Python", "SQL", "Nursing", "IFRS", "NEBOSH", "Figma"} <= names


def test_longest_alias_wins_without_overlap():
    text = "We use Python, SQL, machine learning, and React.js every day."
    mentions = find_skill_mentions(text)
    names = [skill.name for skill, _start, _end, _alias in mentions]
    assert "Python" in names
    assert "SQL" in names
    assert "Machine Learning" in names
    assert "React" in names
    assert names.count("React") == 1

    spans = [(start, end) for _skill, start, end, _alias in mentions]
    for index, (start, end) in enumerate(spans):
        for other_start, other_end in spans[index + 1 :]:
            assert not (start < other_end and end > other_start)


def test_match_canonical_normalizes_aliases():
    assert match_canonical("postgres").name == "PostgreSQL"  # type: ignore[union-attr]
    assert match_canonical("ML").name == "Machine Learning"  # type: ignore[union-attr]
    assert match_canonical("gen ai").name == "Generative AI"  # type: ignore[union-attr]
    assert match_canonical("not-a-real-skill-xyz") is None


def test_mentions_are_case_insensitive():
    mentions = find_skill_mentions("PYTHON and pytorch and POWER BI")
    names = {skill.name for skill, _start, _end, _alias in mentions}
    assert {"Python", "PyTorch", "Power BI"} <= names
