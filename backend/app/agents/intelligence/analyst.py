from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.intelligence.evidence import build_evidence_pack
from app.agents.intelligence.render import render_markdown
from app.agents.intelligence.report import build_deterministic_report
from app.agents.intelligence.validator import validate_report
from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import LLMCall, Report, Run
from app.llm.prompts import render_prompt
from app.llm.router import LLMRouter

logger = get_logger(__name__)
PROMPT_PATH = settings.seed_dir.parent.parent / "config" / "prompts" / "report.md"


class IntelligenceAnalyst:
    name = "intelligence_analyst"

    def __init__(self, router: LLMRouter | None = None) -> None:
        self.router = router or LLMRouter()

    async def run(
        self, run: Run, session: AsyncSession, pack: dict[str, Any] | None = None
    ) -> dict:
        pack = pack or await build_evidence_pack(run, session)
        report = build_deterministic_report(run, pack)
        model_id = "deterministic-v1"
        prompt_version = "report-v1"

        if self.router.enabled and PROMPT_PATH.exists():
            template = PROMPT_PATH.read_text(encoding="utf-8")
            prompt = render_prompt(
                template,
                evidence_pack=json.dumps(pack, indent=2, default=str)[:30000],
            )
            response = await self.router.generate_json(
                prompt, task="report", temperature=0.2, max_output_tokens=4000
            )
            if response is not None:
                try:
                    candidate = json.loads(response.text)
                    candidate = {
                        **report,
                        "executive_summary": candidate.get(
                            "executive_summary", report["executive_summary"]
                        ),
                        "sections": candidate.get("sections", report["sections"]),
                        "recommendations": candidate.get(
                            "recommendations", report["recommendations"]
                        ),
                        "caveats": candidate.get("caveats", report["caveats"]),
                        "validation": {"status": "pending", "violations": []},
                    }
                    candidate_status, candidate_violations = validate_report(candidate, pack)
                    if candidate_status == "verified":
                        report = candidate
                        model_id = response.model
                        prompt_version = "report-v1"
                    else:
                        report["caveats"].append(
                            "The LLM narrative was rejected by the evidence validator; "
                            "a deterministic template is shown instead."
                        )
                        logger.warning(
                            "report_narrative_rejected",
                            run_id=str(run.id),
                            violations=candidate_violations[:5],
                        )
                    session.add(
                        LLMCall(
                            run_id=run.id,
                            stage="report",
                            provider=response.provider,
                            model=response.model,
                            prompt_version="report-v1",
                            tokens_in=response.tokens_in,
                            tokens_out=response.tokens_out,
                            latency_ms=response.latency_ms,
                            status="success",
                        )
                    )
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    logger.warning("report_narrative_failed", run_id=str(run.id), error=str(exc))
                    session.add(
                        LLMCall(
                            run_id=run.id,
                            stage="report",
                            provider="gemini",
                            model=settings.gemini_report_model,
                            prompt_version="report-v1",
                            status="fallback",
                            error_code="invalid_json",
                        )
                    )

        status, violations = validate_report(report, pack)
        report["validation"] = {
            "status": status,
            "violations": violations[:10],
            "checked_claims": _count_claims(report),
        }
        markdown = render_markdown(report)
        corpus = pack["corpus"]
        start = corpus.get("date_range", {}).get("start")
        end = corpus.get("date_range", {}).get("end")
        report_row = Report(
            run_id=run.id,
            query=run.query,
            normalized_query=run.normalized_query,
            status="published" if status == "verified" else "partial",
            report_json=report,
            markdown=markdown,
            evidence_pack=pack,
            evidence_pack_hash=pack.get("pack_hash", ""),
            prompt_version=prompt_version,
            model_id=model_id,
            validation_status=status,
            corpus_job_count=corpus["jobs"],
            corpus_company_count=corpus["companies"],
            date_range_start=date.fromisoformat(start) if start else None,
            date_range_end=date.fromisoformat(end) if end else None,
        )
        session.add(report_row)
        await session.flush()
        return {
            "report_id": str(report_row.id),
            "validation_status": status,
            "claims": report["validation"]["checked_claims"],
            "jobs": corpus["jobs"],
            "companies": corpus["companies"],
        }


def _count_claims(report: dict[str, Any]) -> int:
    count = len(report.get("executive_summary", []))
    count += sum(len(section.get("claims", [])) for section in report.get("sections", []))
    count += len(report.get("recommendations", []))
    return count


def pack_hash(pack: dict[str, Any]) -> str:
    return sha256(json.dumps(pack, sort_keys=True, default=str).encode("utf-8")).hexdigest()
