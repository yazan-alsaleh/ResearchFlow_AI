from __future__ import annotations

import ipaddress
import time
from dataclasses import dataclass
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

USER_AGENT = (
    "ResearchFlowAI/0.1 (+https://github.com/yazan-alsaleh/ResearchFlow_AI; "
    "contact: researchflow@example.com)"
)


@dataclass
class RobotsDecision:
    allowed: bool
    crawl_delay: float | None
    reason: str
    checked_at: float


class RobotsCache:
    def __init__(self, ttl_seconds: int = 86_400) -> None:
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, RobotsDecision] = {}

    def _cached(self, domain: str) -> RobotsDecision | None:
        decision = self._cache.get(domain)
        if decision and time.time() - decision.checked_at < self.ttl_seconds:
            return decision
        return None

    async def check(self, url: str, client: httpx.AsyncClient) -> RobotsDecision:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        cached = self._cached(domain)
        if cached:
            return cached

        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        parser = RobotFileParser()
        reason = "robots.txt unavailable"
        try:
            response = await client.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=10)
            if response.status_code == 200:
                parser.parse(response.text.splitlines())
                reason = "robots.txt parsed"
            elif response.status_code in (401, 403):
                parser.disallow_all = True  # type: ignore[attr-defined]
                reason = "robots.txt forbidden"
        except httpx.HTTPError:
            reason = "robots.txt fetch failed"

        allowed = (
            parser.can_fetch(USER_AGENT, url)
            if parser.default_entry  # type: ignore[attr-defined]
            else True
        )
        crawl_delay = parser.crawl_delay(USER_AGENT)
        decision = RobotsDecision(
            allowed=allowed,
            crawl_delay=float(crawl_delay) if crawl_delay else None,
            reason=reason,
            checked_at=time.time(),
        )
        self._cache[domain] = decision
        return decision


def is_safe_public_url(url: str) -> bool:
    """Block obvious SSRF targets. The collector also uses a domain allowlist."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname
    if not host:
        return False
    if host in {"localhost", "127.0.0.1", "::1"}:
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return True
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
    )
