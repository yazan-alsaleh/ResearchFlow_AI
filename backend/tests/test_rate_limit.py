from __future__ import annotations

from app.api.v1.runs import limiter
from app.core.config import settings
from app.core.rate_limit import RateLimiter


def test_limiter_allows_up_to_hourly_limit():
    rl = RateLimiter(per_hour=3, per_day=10, global_per_day=100)
    for _ in range(3):
        assert rl.check("1.2.3.4", now=1_000_000.0).allowed
    denied = rl.check("1.2.3.4", now=1_000_000.0)
    assert not denied.allowed
    assert denied.retry_after is not None and denied.retry_after > 0
    assert denied.headers["X-RateLimit-Remaining"] == "0"


def test_limiter_windows_reset_and_ips_are_independent():
    rl = RateLimiter(per_hour=1, per_day=1, global_per_day=100)
    assert rl.check("1.1.1.1", now=1_000_000.0).allowed
    assert not rl.check("1.1.1.1", now=1_000_000.0 + 60).allowed
    # Another IP is unaffected; the same IP is allowed again in a new window.
    assert rl.check("2.2.2.2", now=1_000_000.0 + 60).allowed
    assert rl.check("1.1.1.1", now=2_000_000.0).allowed


def test_limiter_global_daily_limit_applies_across_ips():
    rl = RateLimiter(per_hour=10, per_day=10, global_per_day=2)
    assert rl.check("1.1.1.1", now=1_000_000.0).allowed
    assert rl.check("2.2.2.2", now=1_000_000.0).allowed
    assert not rl.check("3.3.3.3", now=1_000_000.0).allowed


async def test_create_run_returns_rate_limit_headers(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    response = await client.post("/api/v1/runs", json={"job_title": "Data Analyst", "filters": {}})
    assert response.status_code == 202
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers


async def test_create_run_returns_429_when_hourly_limit_exceeded(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "runs_per_hour_per_ip", 1)
    monkeypatch.setattr(settings, "runs_per_day_per_ip", 10)
    monkeypatch.setattr(settings, "runs_per_day_global", 100)
    limiter.reset()

    first = await client.post("/api/v1/runs", json={"job_title": "Data Analyst", "filters": {}})
    assert first.status_code == 202

    second = await client.post("/api/v1/runs", json={"job_title": "Accountant", "filters": {}})
    assert second.status_code == 429
    assert "Retry-After" in second.headers


async def test_idempotent_replay_does_not_consume_quota(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "runs_per_hour_per_ip", 1)
    monkeypatch.setattr(settings, "runs_per_day_per_ip", 10)
    monkeypatch.setattr(settings, "runs_per_day_global", 100)
    limiter.reset()

    headers = {"Idempotency-Key": "rate-limit-replay-key"}
    body = {"job_title": "Data Analyst", "filters": {}}
    first = await client.post("/api/v1/runs", json=body, headers=headers)
    assert first.status_code == 202
    replay = await client.post("/api/v1/runs", json=body, headers=headers)
    assert replay.status_code == 202
    assert replay.json()["id"] == first.json()["id"]


async def test_rate_limit_can_be_disabled(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(settings, "runs_per_hour_per_ip", 1)
    limiter.reset()
    for title in ("Data Analyst", "Accountant", "Civil Engineer"):
        response = await client.post("/api/v1/runs", json={"job_title": title, "filters": {}})
        assert response.status_code == 202
