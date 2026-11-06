from __future__ import annotations

from typing import Any


def render_markdown(report: dict[str, Any]) -> str:
    lines: list[str] = []
    corpus = report.get("corpus", {})
    lines.append(f"# {report.get('title', 'Market report')}")
    lines.append("")
    lines.append(
        f"**Corpus:** {corpus.get('jobs', 0)} ads · "
        f"{corpus.get('companies', 0)} companies · "
        f"{corpus.get('sources', 0)} sources"
    )
    if corpus.get("date_range", {}).get("start"):
        lines.append(
            f"**Posting window:** {corpus['date_range']['start']} to "
            f"{corpus['date_range']['end']}"
        )
    lines.append("")
    lines.append("## Executive summary")
    for item in report.get("executive_summary", []):
        lines.append(f"- {item['text']} _({item['evidence_ref']})_")
    lines.append("")
    for section in report.get("sections", []):
        lines.append(f"## {section['heading']}")
        for claim in section.get("claims", []):
            lines.append(f"- {claim['text']} _({claim['evidence_ref']})_")
        lines.append("")
    lines.append("## Learning recommendations")
    for item in report.get("recommendations", []):
        lines.append(
            f"{item['priority']}. **{item['skill']}** — {item['rationale']} "
            f"Effort: {item['effort']}. _({item['evidence_ref']})_"
        )
    lines.append("")
    lines.append("## Limitations")
    for caveat in report.get("caveats", []):
        lines.append(f"- {caveat}")
    lines.append("")
    lines.append("## Evidence")
    lines.append(
        "Every claim above references an evidence ID. "
        "The evidence pack is stored with this report."
    )
    lines.append("")
    return "\n".join(lines)
