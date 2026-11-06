from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache

from rapidfuzz import fuzz

from app.core.config import settings


@dataclass(frozen=True)
class SkillDefinition:
    name: str
    category: str
    skill_type: str
    aliases: tuple[str, ...] = field(default_factory=tuple)


def _normalize_alias(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


@lru_cache
def load_taxonomy() -> tuple[SkillDefinition, ...]:
    path = settings.seed_dir / "skills.json"
    if not path.exists():
        return tuple()
    raw = json.loads(path.read_text(encoding="utf-8"))
    return tuple(
        SkillDefinition(
            name=item["name"],
            category=item.get("category", "technical"),
            skill_type=item.get("skill_type", "tool"),
            aliases=tuple(_normalize_alias(alias) for alias in item.get("aliases", [])),
        )
        for item in raw
    )


@lru_cache
def alias_index() -> tuple[tuple[str, SkillDefinition], ...]:
    pairs: dict[str, SkillDefinition] = {}
    for skill in load_taxonomy():
        for alias in (*skill.aliases, _normalize_alias(skill.name)):
            pairs[alias] = skill
    # Longest aliases first so "react.js" wins over "react".
    return tuple(sorted(pairs.items(), key=lambda item: len(item[0]), reverse=True))


@lru_cache
def canonical_index() -> dict[str, SkillDefinition]:
    return {_normalize_alias(skill.name): skill for skill in load_taxonomy()}


def normalize_text(text: str) -> str:
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    return re.sub(r"\s+", " ", text).strip().lower()


def find_skill_mentions(text: str) -> list[tuple[SkillDefinition, int, int, str]]:
    """Return non-overlapping skill mentions as (skill, start, end, matched_alias)."""
    normalized = normalize_text(text)
    matches: list[tuple[SkillDefinition, int, int, str]] = []
    occupied: list[tuple[int, int]] = []
    for alias, skill in alias_index():
        if len(alias) < 2:
            continue
        pattern = re.compile(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])")
        for match in pattern.finditer(normalized):
            start, end = match.span()
            if any(start < other_end and end > other_start for other_start, other_end in occupied):
                continue
            occupied.append((start, end))
            matches.append((skill, start, end, alias))
    return sorted(matches, key=lambda item: item[1])


def match_canonical(name: str) -> SkillDefinition | None:
    normalized = _normalize_alias(name)
    if normalized in canonical_index():
        return canonical_index()[normalized]
    for alias, skill in alias_index():
        if alias == normalized:
            return skill
    if len(normalized) >= 4:
        best = max(load_taxonomy(), key=lambda skill: fuzz.token_set_ratio(normalized, skill.name))
        if fuzz.token_set_ratio(normalized, best.name) >= 92:
            return best
    return None


def skill_payload(skill: SkillDefinition) -> dict:
    return {
        "name": skill.name,
        "category": skill.category,
        "skill_type": skill.skill_type,
    }


def skill_slug(name: str) -> str:
    """Build a URL-safe slug that keeps C#, C++, and .NET distinct."""
    value = name.lower()
    value = value.replace("c++", "cpp").replace("c#", "c-sharp").replace(".net", "dotnet")
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "skill"
