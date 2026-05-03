from __future__ import annotations

import argparse
import logging
from pathlib import Path

from src.constants import (
    DEFAULT_CONCURRENCY,
    DEFAULT_LOG_LEVEL,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_URLS,
)
from src.http_client import RttfHttpClient
from src.service import RttfParserService
from src.storage import JsonStorage


def build_parser() -> argparse.ArgumentParser:
    """Создает парсер аргументов командной строки."""
    parser = argparse.ArgumentParser(description="Parse RTTF player profiles into JSON")
    parser.add_argument("urls", nargs="*", help="RTTF player profile URLs")
    parser.add_argument("--urls-file", type=Path, help="Text file with one URL per line")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY)
    parser.add_argument(
        "--log-level",
        default=DEFAULT_LOG_LEVEL,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    )
    parser.add_argument(
        "--use-default-urls",
        action="store_true",
        help="Use URLs from constants.py when no URLs were provided",
    )
    return parser


def setup_logging(log_level: str) -> None:
    """Настраивает базовый logging для CLI-запуска."""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def read_urls(args: argparse.Namespace) -> list[str]:
    """Читает URL из аргументов CLI, файла и дефолтного списка."""
    urls = list(args.urls)

    if args.urls_file:
        urls.extend(
            line.strip()
            for line in args.urls_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("#")
        )

    if not urls and args.use_default_urls:
        urls.extend(DEFAULT_URLS)

    # dict.fromkeys сохраняет порядок и убирает дубли.
    return list(dict.fromkeys(urls))


async def run_from_cli() -> int:
    """Точка входа для запуска через main.py."""
    args = build_parser().parse_args()
    setup_logging(args.log_level)

    urls = read_urls(args)
    if not urls:
        raise SystemExit("Provide URLs as arguments, via --urls-file, or use --use-default-urls")

    storage = JsonStorage(args.output_dir)

    async with RttfHttpClient() as http_client:
        service = RttfParserService(
            http_client=http_client,
            concurrency=args.concurrency,
        )
        result = await service.parse_many(urls)

    for profile in result.ok:
        storage.save_profile(profile)

    batch_path = storage.save_batch_result(result)

    print(f"OK: {len(result.ok)}; failed: {len(result.failed)}")
    print(f"Batch JSON: {batch_path}")

    return 0 if not result.failed else 1