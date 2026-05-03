from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.constants import DEFAULT_BATCH_FILENAME, DEFAULT_OUTPUT_DIR
from src.models import ParseResult, PlayerProfile


class JsonStorage:
    """Сохраняет результат парсинга в JSON-файлы."""

    def __init__(self, output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> None:
        """Создает директорию для результатов, если ее еще нет."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save_profile(self, profile: PlayerProfile) -> Path:
        """Сохраняет один профиль игрока в отдельный JSON."""
        filename = self._build_profile_filename(profile)
        path = self.output_dir / filename

        self._write_json(
            path,
            {
                "source_url": profile.source_url,
                "parsed_at": datetime.now().isoformat(timespec="seconds"),
                "player": profile.to_dict(),
            },
        )

        return path

    def save_batch_result(
        self,
        result: ParseResult,
        filename: str = DEFAULT_BATCH_FILENAME,
    ) -> Path:
        """Сохраняет общий batch-отчет с успешными и ошибочными URL."""
        path = self.output_dir / filename

        self._write_json(
            path,
            {
                "parsed_at": datetime.now().isoformat(timespec="seconds"),
                "total_ok": len(result.ok),
                "total_failed": len(result.failed),
                "ok": [profile.to_dict() for profile in result.ok],
                "failed": [asdict(error) for error in result.failed],
            },
        )

        return path

    def _build_profile_filename(self, profile: PlayerProfile) -> str:
        """Формирует имя файла из ФИО, а если ФИО нет — из ID игрока."""
        if profile.full_name:
            return f"{self._slugify(profile.full_name)}.json"

        player_id = profile.player_id or "unknown"
        return f"rttf_player_{player_id}.json"

    @staticmethod
    def _slugify(value: str) -> str:
        """Делает строку безопасной для имени файла."""
        value = value.lower().strip()
        value = re.sub(r"\s+", "_", value)
        value = re.sub(r"[^a-zа-яё0-9_\\-]", "", value)
        value = re.sub(r"_+", "_", value)

        return value or "unknown_player"

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        """Пишет JSON в UTF-8, сохраняя кириллицу читаемой."""
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )