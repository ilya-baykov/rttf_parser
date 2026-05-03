from __future__ import annotations

import logging

import httpx

from src.constants import DEFAULT_HEADERS, DEFAULT_TIMEOUT_SECONDS
from src.exceptions import FetchError

log = logging.getLogger(__name__)


class RttfHttpClient:
    """Небольшая async-обертка над httpx для загрузки страниц RTTF."""

    def __init__(self, *, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        """Создает HTTP-клиент с browser-like headers."""
        self._client = httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=httpx.Timeout(timeout_seconds),
            follow_redirects=True,
        )

    async def __aenter__(self) -> "RttfHttpClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def close(self) -> None:
        """Закрывает пул HTTP-соединений."""
        await self._client.aclose()

    async def fetch_html(self, url: str) -> str:
        """Загружает HTML одной страницы RTTF."""
        log.info("Downloading RTTF page: %s", url)

        try:
            response = await self._client.get(url)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise FetchError(f"RTTF returned HTTP {exc.response.status_code} for {url}") from exc
        except httpx.RequestError as exc:
            raise FetchError(f"Cannot fetch {url}: {exc}") from exc

        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            log.warning("Unexpected content type for %s: %s", url, content_type)

        return response.text