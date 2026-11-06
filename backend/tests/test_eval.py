from __future__ import annotations

from app.eval.metrics import (
    evidence_validity,
    experience_mae,
    importance_accuracy,
    skill_prf,
    summarize,
)


def test_skill_prf_perfect_and_partial():
    gold = [{"name": "Python"}, {"name": "SQL"}, {"name": "Docker"}]
    predicted = [{"name": "Python"}, {"name": "SQL"}]
    result = skill_prf(gold, predicted)
    assert result["tp"] == 2
    assert result["fn"] == 1
    assert result["fp"] == 0
    assert result["precision"] == 1.0
    assert result["recall"] == round(2 / 3, 4)

    extra = skill_prf(gold, [{"name": "Python"}, {"name": "Go"}])
    assert extra["fp"] == 1
    assert extra["precision"] == 0.5


def test_importance_accuracy_and_evidence_validity():
    gold = [{"name": "Python", "importance": "required"}]
    predicted = [{"name": "Python", "importance": "preferred", "evidence_valid": False}]
    assert importance_accuracy(gold, predicted) == 0.0
    assert evidence_validity(predicted) == 0.0
    assert importance_accuracy(gold, []) is None
    assert evidence_validity([]) is None


def test_experience_mae():
    gold = [{"experience": {"min_years": 3}}, {"experience": {"min_years": 5}}]
    predicted = [{"experience": {"min_years": 4}}, {"experience": {"min_years": 5}}]
    assert experience_mae(gold, predicted) == 0.5
    assert experience_mae([{"experience": None}], [{"experience": None}]) is None


def test_summarize_aggregates_micro_metrics():
    cases = [
        {
            "gold": {
                "skills": [{"name": "Python", "importance": "required"}],
                "experience": {"min_years": 3},
            },
            "predicted": {
                "skills": [{"name": "Python", "importance": "required", "evidence_valid": True}],
                "experience": {"min_years": 3},
            },
        },
        {
            "gold": {"skills": [{"name": "SQL", "importance": "required"}]},
            "predicted": {"skills": [], "experience": None},
        },
    ]
    result = summarize(cases)
    assert result["cases"] == 2
    assert result["skill_recall"] == 0.5
    assert result["skill_precision"] == 1.0
    assert result["importance_accuracy"] == 1.0
    assert result["experience_mae_years"] == 0.0
