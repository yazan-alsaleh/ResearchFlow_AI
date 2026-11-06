from __future__ import annotations

from app.llm.prompts import render_prompt


def test_render_prompt_preserves_json_braces():
    template = 'Return this shape:\n{"skills": []}\n\nTitle: {title}\nDescription: {description}'
    rendered = render_prompt(template, title="AI Engineer", description="Python required")
    assert '{"skills": []}' in rendered
    assert "Title: AI Engineer" in rendered
    assert "Description: Python required" in rendered
    assert "{title}" not in rendered


def test_render_prompt_does_not_touch_unknown_placeholders():
    template = "{known} and {unknown}"
    rendered = render_prompt(template, known="value")
    assert rendered == "value and {unknown}"


def test_prompt_files_are_renderable():
    from pathlib import Path

    from app.core.config import settings

    prompts_dir = settings.seed_dir.parent.parent / "config" / "prompts"
    extraction = (prompts_dir / "extraction.md").read_text(encoding="utf-8")
    report = (prompts_dir / "report.md").read_text(encoding="utf-8")

    extraction_rendered = render_prompt(
        extraction,
        title="AI Engineer",
        company="Example",
        location="Doha",
        description="Python required",
    )
    report_rendered = render_prompt(report, evidence_pack='{"corpus": {"jobs": 2}}')

    assert "AI Engineer" in extraction_rendered
    assert '"skills"' in extraction_rendered
    assert '{"corpus": {"jobs": 2}}' in report_rendered
    assert Path(prompts_dir).is_dir()
