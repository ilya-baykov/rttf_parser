
from __future__ import annotations

import re
from urllib.parse import urljoin, urlparse

from bs4 import Tag

from src.constants import BASE_URL


def clean_text(value: str | None) -> str:
    """Нормализует текст из HTML: убирает лишние пробелы и переносы."""
    return re.sub(r"\s+", " ", value or "").strip()


def parse_int(value: str | None) -> int | None:
    """Достает первое целое число из строки."""
    match = re.search(r"\d[\d'\s]*", value or "")
    if not match:
        return None

    return int(match.group(0).replace("'", "").replace(" ", ""))


def parse_float(value: str | None) -> float | None:
    """Достает первое дробное число из строки."""
    if not value:
        return None

    normalized = value.replace("−", "-").replace(",", ".")
    match = re.search(r"[+-]?\d+(?:\.\d+)?", normalized)
    return float(match.group(0)) if match else None


def absolute_url(href: str | None) -> str | None:
    """Превращает относительную ссылку RTTF в абсолютную."""
    if not href:
        return None

    return urljoin(BASE_URL, href)


def extract_player_id(url: str) -> int | None:
    """Достает ID игрока из URL профиля."""
    match = re.search(r"/players/(\d+)", urlparse(url).path)
    return int(match.group(1)) if match else None


def cell_text(row: Tag, index: int) -> str | None:
    """Безопасно достает текст из ячейки таблицы по индексу."""
    cells = row.select("td, th")
    if index >= len(cells):
        return None

    return clean_text(cells[index].get_text(" ")) or None