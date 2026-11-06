"""Extraction evaluation metrics (PLAN.md §10).

Pure functions over hand-labeled gold cases vs deterministic/LLM extractions.
Skill matching is canonical-name based (alias-aware labels are expected to
already use canonical names).
"""

from __future__ import annotations


def skill_prf(gold: list[dict], predicted: list[dict]) -> dict:
    gold_names = {item["name"] for item in gold}
    pred_names = {item["name"] for item in predicted}
    tp = len(gold_names & pred_names)
    fp = len(pred_names - gold_names)
    fn = len(gold_names - pred_names)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def importance_accuracy(gold: list[dict], predicted: list[dict]) -> float | None:
    pred_by_name = {item["name"]: item.get("importance") for item in predicted}
    matched = [item for item in gold if item["name"] in pred_by_name]
    if not matched:
        return None
    correct = sum(1 for item in matched if pred_by_name[item["name"]] == item.get("importance"))
    return round(correct / len(matched), 4)


def evidence_validity(predicted: list[dict]) -> float | None:
    if not predicted:
        return None
    valid = sum(1 for item in predicted if item.get("evidence_valid", True))
    return round(valid / len(predicted), 4)


def experience_mae(gold: list[dict], predicted: list[dict]) -> float | None:
    """Mean absolute error over cases where both sides state min years."""
    errors = []
    for g, p in zip(gold, predicted, strict=False):
        g_years = (g.get("experience") or {}).get("min_years")
        p_years = (p.get("experience") or {}).get("min_years")
        if g_years is not None and p_years is not None:
            errors.append(abs(g_years - p_years))
    if not errors:
        return None
    return round(sum(errors) / len(errors), 4)


def summarize(cases: list[dict]) -> dict:
    """Aggregate micro metrics across gold cases.

    Each case: {"gold": {...}, "predicted": {...}} where predicted mirrors
    the extractor payload shape (skills, experience).
    """
    all_gold: list[dict] = []
    all_pred: list[dict] = []
    importance_hits = 0
    importance_total = 0
    evidence_hits = 0
    evidence_total = 0
    exp_errors: list[int] = []

    for case in cases:
        gold = case["gold"]
        pred = case["predicted"]
        all_gold.extend(gold.get("skills", []))
        all_pred.extend(pred.get("skills", []))

        pred_by_name = {item["name"]: item for item in pred.get("skills", [])}
        for item in gold.get("skills", []):
            if item["name"] in pred_by_name:
                importance_total += 1
                if pred_by_name[item["name"]].get("importance") == item.get("importance"):
                    importance_hits += 1
        for item in pred.get("skills", []):
            evidence_total += 1
            if item.get("evidence_valid", True):
                evidence_hits += 1

        g_years = (gold.get("experience") or {}).get("min_years")
        p_years = (pred.get("experience") or {}).get("min_years")
        if g_years is not None and p_years is not None:
            exp_errors.append(abs(g_years - p_years))

    prf = skill_prf(all_gold, all_pred)
    return {
        "cases": len(cases),
        "skill_precision": prf["precision"],
        "skill_recall": prf["recall"],
        "skill_f1": prf["f1"],
        "importance_accuracy": (
            round(importance_hits / importance_total, 4) if importance_total else None
        ),
        "evidence_validity": (
            round(evidence_hits / evidence_total, 4) if evidence_total else None
        ),
        "experience_mae_years": (
            round(sum(exp_errors) / len(exp_errors), 4) if exp_errors else None
        ),
    }
