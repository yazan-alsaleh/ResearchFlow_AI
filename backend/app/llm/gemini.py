from __future__ import annotations

import time

import httpx

from app.core.errors import LLMUnavailable
from app.llm.base import LLMResponse

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout_s: float = 60.0) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_s = timeout_s

    async def generate(
        self, prompt: str, *, temperature: float = 0, max_output_tokens: int = 2500
    ) -> LLMResponse:
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_output_tokens,
                "responseMimeType": "application/json",
            },
        }
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            response = await client.post(
                GEMINI_ENDPOINT.format(model=self.model),
                headers={"x-goog-api-key": self.api_key, "Content-Type": "application/json"},
                json=payload,
            )
        latency_ms = int((time.perf_counter() - started) * 1000)
        if response.status_code in {429, 500, 502, 503, 504}:
            raise LLMUnavailable(f"Gemini transient error {response.status_code}")
        if response.status_code >= 400:
            raise LLMUnavailable(f"Gemini error {response.status_code}: {response.text[:200]}")

        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise LLMUnavailable("Gemini returned no candidates")
        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise LLMUnavailable("Gemini returned an empty response")
        usage = data.get("usageMetadata", {})
        return LLMResponse(
            text=text,
            provider=self.name,
            model=self.model,
            tokens_in=int(usage.get("promptTokenCount", 0)),
            tokens_out=int(usage.get("candidatesTokenCount", 0)),
            latency_ms=latency_ms,
        )
