from __future__ import annotations

import asyncio
import logging

from src.constants import DEFAULT_CONCURRENCY
from src.exceptions import RttfParserError
from src.http_client import RttfHttpClient
from src.models import ParseErrorInfo, ParseResult, PlayerProfile
from src.parser import RttfPlayerPageParser

log = logging.getLogger(__name__)


class RttfParserService:
    """Сервисный слой: загружает страницы и запускает парсер."""

    def __init__(
        self,
        *,
        http_client: RttfHttpClient,
        parser: RttfPlayerPageParser | None = None,
        concurrency: int = DEFAULT_CONCURRENCY,
    ) -> None:
        """Создает сервис с общим HTTP-клиентом и лимитом параллельности."""
        if concurrency < 1:
            raise ValueError("concurrency must be >= 1")

        self._http_client = http_client
        self._parser = parser or RttfPlayerPageParser()
        self._semaphore = asyncio.Semaphore(concurrency)

    async def parse_many(self, urls: list[str]) -> ParseResult:
        """Парсит список URL, не роняя весь batch из-за одной ошибки."""
        tasks = [self._parse_one_safely(url) for url in urls]
        raw_results = await asyncio.gather(*tasks)

        ok: list[PlayerProfile] = []
        failed: list[ParseErrorInfo] = []

        for item in raw_results:
            if isinstance(item, PlayerProfile):
                ok.append(item)
            else:
                failed.append(item)

        return ParseResult(ok=ok, failed=failed)

    async def _parse_one_safely(self, url: str) -> PlayerProfile | ParseErrorInfo:
        """Парсит одну ссылку и превращает ошибку в структурированный результат."""
        async with self._semaphore:
            try:
                html = await self._http_client.fetch_html(url)
                return self._parser.parse(html=html, source_url=url)
            except RttfParserError as exc:
                log.warning("Cannot parse %s: %s", url, exc)
                return ParseErrorInfo(url=url, error_type=type(exc).__name__, message=str(exc))
            except Exception as exc:
                log.exception("Unexpected parser error for %s", url)
                return ParseErrorInfo(url=url, error_type=type(exc).__name__, message=str(exc))