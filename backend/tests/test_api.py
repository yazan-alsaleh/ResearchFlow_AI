from __future__ import annotations


async def test_health(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


async def test_root_health_alias_used_by_docker_healthcheck(client):
    # Dockerfile / docker-compose healthchecks hit /health, not /api/v1/health.
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ResearchFlow AI"}


async def test_ready_and_root_ready_alias(client):
    for path in ("/api/v1/ready", "/ready"):
        response = await client.get(path)
        assert response.status_code == 200
        assert response.json() == {"status": "ready", "database": "ok"}


async def test_coverage_reports_seeded_corpus(client):
    response = await client.get("/api/v1/meta/coverage")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_jobs"] == 69
    assert payload["total_companies"] >= 10
    assert len(payload["by_family"]) >= 15


async def test_jobs_filter_by_family_and_skill(client):
    response = await client.get("/api/v1/jobs", params={"family": "finance"})
    assert response.status_code == 200
    items = response.json()["items"]
    assert items
    assert all(item["job_family"] == "finance" for item in items)

    response = await client.get("/api/v1/jobs", params={"q": "engineer"})
    assert response.status_code == 200
    assert any("engineer" in item["title"].lower() for item in response.json()["items"])


async def test_skills_endpoint_lists_taxonomy(client):
    response = await client.get("/api/v1/skills", params={"category": "certification"})
    assert response.status_code == 200
    names = {item["canonical_name"] for item in response.json()["items"]}
    assert {"PMP", "NEBOSH", "CPA"} <= names


async def test_create_run_queues_without_running_inline(client):
    response = await client.post(
        "/api/v1/runs",
        json={"job_title": "Data Analyst", "filters": {}},
        headers={"Idempotency-Key": "test-key-1"},
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["query"] == "Data Analyst"
    assert payload["status"] == "queued"
    assert payload["stage"] == "queued"

    again = await client.post(
        "/api/v1/runs",
        json={"job_title": "Data Analyst", "filters": {}},
        headers={"Idempotency-Key": "test-key-1"},
    )
    assert again.status_code == 202
    assert again.json()["id"] == payload["id"]


async def test_run_validation_requires_a_title(client):
    response = await client.post("/api/v1/runs", json={"job_title": "A", "filters": {}})
    assert response.status_code == 422


async def test_unknown_run_returns_404(client):
    response = await client.get("/api/v1/runs/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


async def test_admin_seed_requires_token(client):
    response = await client.post("/api/v1/admin/seed")
    assert response.status_code == 401
