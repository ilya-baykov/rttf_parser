from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal


@dataclass(slots=True)
class ProfileLink:
    """Ссылка из верхнего блока профиля игрока."""

    title: str
    url: str


@dataclass(slots=True)
class RatingPoint:
    """Одна точка истории рейтинга."""

    date: str
    rating: int


@dataclass(slots=True)
class MaxRating:
    """Максимальный рейтинг игрока и дата достижения."""

    rating: int | None
    date: str | None


@dataclass(slots=True)
class PlayerStats:
    """Агрегированная статистика игрока."""

    rank_place: int | None = None
    tournaments_count: int | None = None
    games_total: int | None = None
    wins: int | None = None
    losses: int | None = None
    first_tournament: str | None = None
    favorite_hall: str | None = None
    favorite_hall_url: str | None = None
    favorite_hall_tournaments_count: int | None = None
    rttf_cup_rating: int | None = None
    rttf_cup_tournaments_count: int | None = None
    rttf_cup_games_count: int | None = None


@dataclass(slots=True)
class BestWin:
    """Одна строка из таблицы лучших побед."""

    tournament_title: str | None
    tournament_url: str | None
    player_rating: int | None
    opponent_name: str | None
    opponent_url: str | None
    opponent_rating: int | None
    score: str | None
    rating_delta: float | None
    duration: str | None
    interval: str | None


@dataclass(slots=True)
class MedalHall:
    """Награды игрока в конкретном зале."""

    hall_name: str | None
    gold: bool
    silver: bool
    bronze: bool
    url: str | None


@dataclass(slots=True)
class MatchResult:
    """Один матч внутри турнирного результата."""

    start_time: str | None
    stage: str | None
    opponent_name: str | None
    opponent_url: str | None
    opponent_rating: int | None
    score: str | None
    rating_delta: float | None
    duration: str | None
    history_url: str | None
    is_win: bool | None


@dataclass(slots=True)
class TournamentResult:
    """Турнирный блок с общей информацией и матчами."""

    title: str | None
    url: str | None
    date_time: str | None
    rating_limit: int | None
    hall_name: str | None
    participants_count: int | None
    place: str | None
    medal: Literal["gold", "silver", "bronze"] | None
    player_rating_before: int | None
    total_score: str | None
    total_rating_delta: float | None
    total_duration: str | None
    rating_after: int | None
    matches: list[MatchResult] = field(default_factory=list)


@dataclass(slots=True)
class PlayerProfile:
    """Полная структурированная модель страницы игрока RTTF."""

    source_url: str
    player_id: int | None
    full_name: str | None
    nickname: str | None
    rttf_rating: int | None
    city: str | None
    birth_year: int | None
    playing_hand: str | None
    registered_at: str | None
    last_visit_at: str | None
    max_rating: MaxRating
    links: list[ProfileLink]
    stats: PlayerStats
    rating_history: list[RatingPoint]
    best_wins: list[BestWin]
    medals: list[MedalHall]
    recent_results: list[TournamentResult]

    def to_dict(self) -> dict[str, Any]:
        """Преобразует вложенные dataclass-модели в словарь для JSON."""
        return asdict(self)


@dataclass(slots=True)
class ParseErrorInfo:
    """Информация об ошибке парсинга одной ссылки."""

    url: str
    error_type: str
    message: str


@dataclass(slots=True)
class ParseResult:
    """Результат batch-парсинга: успешные и неуспешные ссылки."""

    ok: list[PlayerProfile]
    failed: list[ParseErrorInfo]