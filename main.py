import asyncio

from src.constants import DEFAULT_CONCURRENCY, DEFAULT_OUTPUT_DIR
from src.http_client import RttfHttpClient
from src.service import RttfParserService
from src.storage import JsonStorage


URLS = [
    "https://rttf.ru/players/193138",
    "https://rttf.ru/players/242733",
    "https://rttf.ru/players/237657",
    "https://rttf.ru/players/109567",
    "https://rttf.ru/players/205479",
]


async def main() -> None:
    """Запускает парсинг списка RTTF-профилей из переменной URLS."""
    storage = JsonStorage(DEFAULT_OUTPUT_DIR)

    async with RttfHttpClient() as http_client:
        service = RttfParserService(
            http_client=http_client,
            concurrency=DEFAULT_CONCURRENCY,
        )
        result = await service.parse_many(URLS)

    for profile in result.ok:
        storage.save_profile(profile)

    batch_path = storage.save_batch_result(result)

    print(f"OK: {len(result.ok)}; failed: {len(result.failed)}")
    print(f"Batch JSON: {batch_path}")


if __name__ == "__main__":
    asyncio.run(main())