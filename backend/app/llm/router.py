from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.core.config import settings
from app.core.errors import LLMUnavailable
from app.core.registry import primary_model
from app.llm.base import LLMResponse
from app.llm.gemini import GeminiProvider


@dataclass
class RouterResult:
    response: LLMResponse | None
    cache_hit: bool = False
    error: str | None = None


class LLMRouter:
    """Small provider router with in-memory cache and graceful degradation.

    The database-backed cache and circuit breaker land in Phase 2. For the MVP,
    a missing key or a provider error simply returns None so deterministic
    extraction and template reports keep the product working.
    """

    def __init__(self) -> None:
        self._cache: dict[str, LLMResponse] = {}

    @property
    def enabled(self) -> bool:
        return settings.llm_enabled and bool(settings.gemini_api_key)

    def model_for(self, task: str) -> str:
        """Primary model for a task, from config/models.yaml routes."""
        configured = primary_model(task, str(settings.config_dir))
        if configured:
            return configured
        if task == "report":
            return settings.gemini_report_model
        return settings.gemini_extraction_model

    def _model_for(self, task: str) -> str:
        return self.model_for(task)

    async def generate_json(
        self,
        prompt: str,
        *,
        task: str = "extraction",
        temperature: float = 0,
        max_output_tokens: int = 2500,
    ) -> LLMResponse | None:
        if not self.enabled:
            return None
        model = self._model_for(task)
        cache_key = hashlib.sha256(
            f"{model}|{temperature}|{max_output_tokens}|{prompt}".encode()
        ).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]
        provider = GeminiProvider(api_key=settings.gemini_api_key or "", model=model)
        try:
            response = await provider.generate(
                prompt, temperature=temperature, max_output_tokens=max_output_tokens
            )
        except LLMUnavailable:
            return None
        self._cache[cache_key] = response
        return response

    def clear_cache(self) -> None:
        self._cache.clear()
