from __future__ import annotations

from app.agents.collector.dedupe import (
    canonicalize_url,
    description_hash,
    fingerprint,
    normalize_for_comparison,
    url_hash,
)


def test_canonicalize_url_strips_tracking_and_sorts_query():
    url = "https://www.Example.com/jobs/123/?utm_source=x&seed=y&b=2&a=1#apply"
    assert canonicalize_url(url) == "https://example.com/jobs/123?a=1&b=2"


def test_canonicalize_url_keeps_meaningful_query():
    url = "https://example.com/jobs?id=42&utm_campaign=qatar"
    assert canonicalize_url(url) == "https://example.com/jobs?id=42"


def test_url_hash_is_stable_across_tracking_parameters():
    first = "https://example.com/jobs/1?utm_source=a&id=9"
    second = "https://www.example.com/jobs/1/?id=9"
    assert url_hash(first) == url_hash(second)


def test_fingerprint_ignores_case_and_punctuation():
    left = fingerprint("AI Engineer", "QatarEnergy", "Build ML systems.")
    right = fingerprint("ai engineer!", "qatarenergy", "build ml systems")
    assert left == right


def test_description_hash_normalizes_whitespace():
    assert description_hash("Hello   World!") == description_hash("hello world")
    assert normalize_for_comparison("C++ / C#") == "cplusplus csharp"
