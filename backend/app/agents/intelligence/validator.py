from __future__ import annotations

import json
import re
from typing import Any


def _iter_claims(report: dict[str, Any]):
    for item in report.get("executive_summary", []):
        if isinstance(item, dict):
            yield "executive_summary", item
    for section in report.get("sections", []):
        for item in section.get("claims", []):
            if isinstance(item, dict):
                yield section.get("heading", "section"), item
    for item in report.get("recommendations", []):
        if isinstance(item, dict):
            yield "recommendation", item


def validate_report(report: dict[str, Any], pack: dict[str, Any]) -> tuple[str, list[str]]:
    refs = {ref["id"]: ref for ref in pack.get("evidence_refs", [])}
    corpus_job_ids = set()
    for ref in refs.values():
        if ref.get("metric") == "corpus_jobs":
            corpus_job_ids = set(ref.get("job_ids", []))
    pack_text = json.dumps(pack, default=str)
    violations: list[str] = []

    for location, claim in _iter_claims(report):
        ref_id = claim.get("evidence_ref")
        if not ref_id:
            violations.append(f"{location}: claim has no evidence_ref")
            continue
        ref = refs.get(ref_id)
        if not ref:
            violations.append(f"{location}: unknown evidence_ref {ref_id}")
            continue
        for job_id in ref.get("job_ids", []):
            if corpus_job_ids and job_id not in corpus_job_ids:
                violations.append(f"{location}: evidence cites a job outside the corpus ({job_id})")
        text = str(claim.get("text") or claim.get("rationale") or "")
        for number in re.findall(r"\d+(?:\.\d+)?", text):
            if number not in pack_text:
                violations.append(
                    f"{location}: number {number} is not present in the evidence pack"
                )

    if report.get("corpus", {}).get("jobs") != pack.get("corpus", {}).get("jobs"):
        violations.append("Report corpus job count does not match the evidence pack")

    return ("verified" if not violations else "partial"), violations
