"""Run extraction evaluation against the hand-labeled gold cases.

Usage (from backend/):
    uv run python -m scripts.eval
    uv run python -m scripts.eval --write ../docs/evaluation/results.json

Uses the deterministic extractor, so no API quota is spent. LLM-based
evaluation can reuse app.eval.metrics with a different producer.
"""

from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from app.agents.skills.extractor import extract_deterministic
from app.db.models import Job
from app.eval.metrics import summarize

ROOT = Path(__file__).resolve().parents[2]
SEED_JOBS = ROOT / "data" / "seed" / "jobs.jsonl"
GOLD_CASES = ROOT / "data" / "gold" / "cases.jsonl"


def load_jobs() -> dict[tuple[str, str], dict]:
    jobs = {}
    seed_dir = ROOT / "data" / "seed"
    for path in sorted(seed_dir.glob("jobs*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                jobs[(record["title"], record["company"])] = record
    return jobs


def load_gold() -> list[dict]:
    gold_dir = ROOT / "data" / "gold"
    cases: list[dict] = []
    for path in sorted(gold_dir.glob("cases*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cases.append(json.loads(line))
    return cases


def to_job(record: dict) -> Job:
    return Job(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        url=record["url"],
        url_hash=record["url"],
        title=record["title"],
        title_normalized=record["title"].lower(),
        company=record["company"],
        company_normalized=record["company"].lower(),
        location_text=record.get("location", ""),
        description=record["description"],
        description_hash=record["url"],
        fingerprint=record["url"],
        job_family=record.get("family", ""),
        language=record.get("language", "en"),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    default_out = str(ROOT / "docs" / "evaluation" / "results.json")
    parser.add_argument("--write", nargs="?", const=default_out)
    args = parser.parse_args()

    jobs = load_jobs()
    cases = []
    for gold_case in load_gold():
        record = jobs.get((gold_case["job_title"], gold_case["company"]))
        if record is None:
            print(f"WARNING: seed job not found for gold case {gold_case}")
            continue
        predicted = extract_deterministic(to_job(record))
        cases.append(
            {
                "gold": gold_case["gold"],
                "predicted": predicted,
                "language": gold_case.get("language", "en"),
            }
        )

    metrics = summarize(cases)
    metrics["by_language"] = {
        language: summarize([c for c in cases if c["language"] == language])
        for language in sorted({c["language"] for c in cases})
    }
    print(json.dumps(metrics, indent=2))
    if args.write:
        target = Path(args.write)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {target}")


if __name__ == "__main__":
    main()
