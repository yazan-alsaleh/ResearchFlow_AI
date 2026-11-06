from __future__ import annotations

from app.agents.intelligence.evidence import build_cooccurrence


def make_skills() -> list[dict]:
    return [
        {"skill": "Python", "job_ids": ["j1", "j2", "j3"]},
        {"skill": "SQL", "job_ids": ["j1", "j2"]},
        {"skill": "Docker", "job_ids": ["j3"]},
        {"skill": "Excel", "job_ids": []},
    ]


def test_cooccurrence_matrix_counts_shared_ads():
    result = build_cooccurrence(make_skills(), top_n=4)
    assert result["skills"] == ["Python", "SQL", "Docker", "Excel"]
    # Diagonal counts are each skill's own job count.
    assert result["matrix"][0] == [3, 2, 1, 0]
    assert result["matrix"][1] == [2, 2, 0, 0]
    assert result["matrix"][2] == [1, 0, 1, 0]


def test_cooccurrence_pairs_sorted_by_count_with_jaccard():
    result = build_cooccurrence(make_skills(), top_n=4)
    pairs = result["pairs"]
    assert pairs[0]["a"] == "Python"
    assert pairs[0]["b"] == "SQL"
    assert pairs[0]["count"] == 2
    assert pairs[0]["jaccard"] == round(2 / 3, 4)
    # Zero-overlap pairs are excluded.
    assert all(pair["count"] > 0 for pair in pairs)


def test_cooccurrence_empty_skills():
    result = build_cooccurrence([], top_n=10)
    assert result == {"skills": [], "matrix": [], "pairs": []}


def test_cooccurrence_caps_at_top_n():
    result = build_cooccurrence(make_skills(), top_n=2)
    assert result["skills"] == ["Python", "SQL"]
    assert len(result["matrix"]) == 2
