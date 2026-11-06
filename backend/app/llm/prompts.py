from __future__ import annotations


def render_prompt(template: str, **values: object) -> str:
    """Replace named placeholders without interpreting JSON braces in the template.

    Prompt files contain literal JSON examples (`{ ... }`), so ``str.format`` cannot be
    used. This helper only substitutes the exact ``{name}`` placeholders it is given.
    """
    rendered = template
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", str(value))
    return rendered
