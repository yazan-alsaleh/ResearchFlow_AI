from __future__ import annotations

import pytest

from app.core.registry import (
    clear_registry_cache,
    load_models_registry,
    load_sources_registry,
    primary_model,
    route_chain,
)
from app.llm.router import LLMRouter


def test_models_registry_loads_and_routes_are_valid():
    registry = load_models_registry()
    assert "gemini" in registry.providers
    assert registry.routes["extraction"].chain[0] == "gemini-2.5-flash-lite"
    assert registry.routes["report"].chain[0] == "gemini-2.5-flash"
    for route in registry.routes.values():
        assert route.chain
        assert all(model in registry.models for model in route.chain)


def test_primary_model_matches_plan_routes():
    assert primary_model("extraction") == "gemini-2.5-flash-lite"
    assert primary_model("report") == "gemini-2.5-flash"
    assert route_chain("extraction") == ["gemini-2.5-flash-lite", "gemini-2.5-flash", "qwen3:4b"]
    assert primary_model("unknown-task") is None


def test_sources_registry_policy_gate():
    registry = load_sources_registry()
    approved = registry.approved_sources()
    assert approved  # at least the seed corpus
    assert all(s.policy_status == "approved" and s.enabled for s in approved)
    # Review/blocked sources must never be collectable.
    assert all(s.slug != "qatarenergy-careers" for s in approved)
    assert registry.get("seed-corpus") is not None
    assert registry.get("does-not-exist") is None


def test_router_uses_registry_primary_models():
    router = LLMRouter()
    assert router.model_for("extraction") == "gemini-2.5-flash-lite"
    assert router.model_for("report") == "gemini-2.5-flash"


def test_registry_rejects_unknown_models_in_routes(tmp_path):
    (tmp_path / "models.yaml").write_text(
        """
providers:
  gemini:
    type: gemini
models:
  m1:
    provider: gemini
routes:
  extraction:
    chain: [not-a-model]
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown models"):
        load_models_registry(str(tmp_path))
    clear_registry_cache()
