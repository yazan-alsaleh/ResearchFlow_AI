from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup


def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text("\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    return text.strip()


def _iter_jsonld_objects(value: Any):
    if isinstance(value, list):
        for item in value:
            yield from _iter_jsonld_objects(item)
    elif isinstance(value, dict):
        if "@graph" in value:
            yield from _iter_jsonld_objects(value["@graph"])
        yield value


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _location_parts(location: Any) -> tuple[str, str | None]:
    if isinstance(location, list):
        location = location[0] if location else {}
    if not isinstance(location, dict):
        return "Qatar", None
    address = location.get("address", {})
    if isinstance(address, list):
        address = address[0] if address else {}
    if not isinstance(address, dict):
        return "Qatar", None
    city = address.get("addressLocality")
    region = address.get("addressRegion")
    country = address.get("addressCountry")
    if isinstance(country, dict):
        country = country.get("name")
    parts = [part for part in (city, region, country) if part]
    return ", ".join(parts) or "Qatar", city


def parse_jobposting_jsonld(html: str, base_url: str) -> list[dict]:
    soup = BeautifulSoup(html or "", "html.parser")
    jobs: list[dict] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            payload = json.loads(script.string or "{}")
        except json.JSONDecodeError:
            continue
        for item in _iter_jsonld_objects(payload):
            if not isinstance(item, dict):
                continue
            types = item.get("@type", "")
            if isinstance(types, str):
                types = [types]
            if not any("JobPosting" in str(value) for value in types):
                continue
            organization = item.get("hiringOrganization") or {}
            if isinstance(organization, list):
                organization = organization[0] if organization else {}
            location_text, city = _location_parts(item.get("jobLocation"))
            description = html_to_text(item.get("description", ""))
            title = item.get("title") or item.get("name") or "Untitled role"
            url = item.get("url") or base_url
            employment = item.get("employmentType")
            if isinstance(employment, list):
                employment = ", ".join(str(value) for value in employment)
            jobs.append(
                {
                    "title": str(title).strip(),
                    "company": str(organization.get("name", "Unknown company")).strip(),
                    "location": location_text,
                    "city": city,
                    "description": description,
                    "posted_at": _parse_date(item.get("datePosted")),
                    "employment_type": employment,
                    "url": str(url),
                }
            )
    return jobs
