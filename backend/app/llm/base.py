from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class LLMResponse:
    text: str
    provider: str
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    status: str = "success"


class LLMProvider(Protocol):
    name: str

    async def generate(
        self, prompt: str, *, temperature: float = 0, max_output_tokens: int = 2500
    ) -> LLMResponse: ...
