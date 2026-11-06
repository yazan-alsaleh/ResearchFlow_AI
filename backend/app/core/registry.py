"""Load and validate config/models.yaml and config/sources.yaml (PLAN §6, §7).

YAML is the source of truth for model IDs, routes, budgets, and source
policy. Environment settings remain overrides for deployment secrets
(API keys, tokens) — model *selection* lives here, not in code.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG_DIR = ROOT_DIR / "config"


class ProviderLimits(BaseModel):
    rpm: int | None = None
    rpd: int | None = None
    concurrency: int | None = None


class ProviderConfig(BaseModel):
    type: str
    api_key_env: str | None = None
    base_url: str | None = None
    model: str | None = None
    limits: ProviderLimits = Field(default_factory=ProviderLimits)


class ModelConfig(BaseModel):
    provider: str
    capabilities: list[str] = Field(default_factory=list)
    context_window: int | None = None


class RouteConfig(BaseModel):
    chain: list[str]
    temperature: float = 0
    max_output_tokens: int = 2500
    timeout_s: float = 60
    retries: int = 0
    repair_attempts: int = 0


class BudgetConfig(BaseModel):
    max_llm_calls: int | None = None
    max_tokens: int | None = None
    max_wall_clock_s: int | None = None
    max_cost_usd: float | None = None


class BudgetsConfig(BaseModel):
    per_run: BudgetConfig = Field(default_factory=BudgetConfig)
    daily: BudgetConfig = Field(default_factory=BudgetConfig)


class ModelsRegistry(BaseModel):
    providers: dict[str, ProviderConfig]
    models: dict[str, ModelConfig]
    routes: dict[str, RouteConfig]
    budgets: BudgetsConfig = Field(default_factory=BudgetsConfig)


class SourceConfig(BaseModel):
    slug: str
    name: str
    type: str
    base_url: str
    domain: str
    country: str = "QA"
    terms_url: str | None = None
    robots_url: str | None = None
    policy_status: str = "review"
    crawl_delay_ms: int = 1000
    max_rps: float = 1
    attribution_required: bool = False
    enabled: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourcesRegistry(BaseModel):
    sources: list[SourceConfig]

    def approved_sources(self) -> list[SourceConfig]:
        """Sources permitted for automated collection."""
        return [s for s in self.sources if s.policy_status == "approved" and s.enabled]

    def get(self, slug: str) -> SourceConfig | None:
        return next((s for s in self.sources if s.slug == slug), None)


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Registry file {path} must contain a mapping")
    return data


@lru_cache
def load_models_registry(config_dir: str | None = None) -> ModelsRegistry:
    path = Path(config_dir or DEFAULT_CONFIG_DIR) / "models.yaml"
    registry = ModelsRegistry.model_validate(_load_yaml(path))
    unknown = {
        model
        for route in registry.routes.values()
        for model in route.chain
        if model not in registry.models
    }
    if unknown:
        raise ValueError(f"models.yaml routes reference unknown models: {sorted(unknown)}")
    return registry


@lru_cache
def load_sources_registry(config_dir: str | None = None) -> SourcesRegistry:
    path = Path(config_dir or DEFAULT_CONFIG_DIR) / "sources.yaml"
    return SourcesRegistry.model_validate(_load_yaml(path))


def route_chain(task: str, config_dir: str | None = None) -> list[str]:
    registry = load_models_registry(config_dir)
    route = registry.routes.get(task)
    return list(route.chain) if route else []


def primary_model(task: str, config_dir: str | None = None) -> str | None:
    chain = route_chain(task, config_dir)
    return chain[0] if chain else None


def clear_registry_cache() -> None:
    load_models_registry.cache_clear()
    load_sources_registry.cache_clear()
