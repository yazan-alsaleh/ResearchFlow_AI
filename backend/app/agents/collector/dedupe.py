from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "gclid",
    "fbclid",
    "ref",
    "source",
    "seed",
}


def canonicalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key.lower() not in TRACKING_PARAMS
    ]
    query.sort()
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((scheme, netloc, path, "", urlencode(query), ""))


def hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def url_hash(url: str) -> str:
    return hash_text(canonicalize_url(url))


def normalize_for_comparison(value: str) -> str:
    value = value.lower()
    value = value.replace("c++", " cplusplus ").replace("c#", " csharp ")
    value = value.replace(".net", " dotnet ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def fingerprint(title: str, company: str, description: str) -> str:
    basis = "|".join(
        (
            normalize_for_comparison(title),
            normalize_for_comparison(company),
            normalize_for_comparison(description)[:500],
        )
    )
    return hash_text(basis)


def description_hash(description: str) -> str:
    return hash_text(normalize_for_comparison(description))
