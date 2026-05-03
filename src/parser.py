from __future__ import annotations

import json
import logging
import re

from bs4 import BeautifulSoup, Tag

from src.exceptions import InvalidPlayerPageError, ParserStructureError
from src.models import (
    BestWin,
    MatchResult,
    MaxRating,
    MedalHall,
    PlayerProfile,
    PlayerStats,
    ProfileLink,
    RatingPoint,
    TournamentResult,
)
from src.utils import absolute_url, cell_text, clean_text, extract_player_id, parse_float, parse_int

log = logging.getLogger(__name__)


class RttfPlayerPageParser:
    """Парсер одной HTML-страницы игрока RTTF."""

    def parse(self, *, html: str, source_url: str) -> PlayerProfile:
        """Парсит HTML страницы игрока в структурированную модель."""
        soup = BeautifulSoup(html, "html.parser")

        player_info = soup.select_one(".player-info")
        if not player_info:
            raise InvalidPlayerPageError("Block .player-info was not found")

        full_name_tag = player_info.select_one("h1")
        if not full_name_tag:
            raise ParserStructureError("Player name h1 was not found")

        registered_at, last_visit_at = self._parse_registered_at(player_info)

        return PlayerProfile(
            source_url=source_url,
            player_id=extract_player_id(source_url),
            full_name=clean_text(full_name_tag.get_text()),
            nickname=self._parse_nickname(player_info),
            rttf_rating=self._parse_current_rating(player_info),
            city=self._get_strong_value(player_info, "город"),
            birth_year=parse_int(self._get_strong_value(player_info, "Год рождения")),
            playing_hand=self._get_strong_value(player_info, "Игровая рука"),
            registered_at=registered_at,
            last_visit_at=last_visit_at,
            max_rating=self._parse_max_rating(soup),
            links=self._parse_profile_links(player_info),
            stats=self._parse_stats(soup),
            rating_history=self._parse_rating_history(html),
            best_wins=self._parse_best_wins(soup),
            medals=self._parse_medals(soup),
            recent_results=self._parse_recent_results(soup),
        )

    def _parse_nickname(self, player_info: Tag) -> str | None:
        """Достает ник из заголовка, не захватывая рейтинг."""
        h3 = player_info.select_one("h3")
        if not h3:
            return None

        h3_copy = BeautifulSoup(str(h3), "html.parser")
        rating_tag = h3_copy.select_one("dfn")

        # Внутри h3 RTTF может хранить рейтинг, поэтому удаляем его перед чтением ника.
        if rating_tag:
            rating_tag.extract()

        return clean_text(h3_copy.get_text()) or None

    def _parse_current_rating(self, player_info: Tag) -> int | None:
        """Достает текущий RTTF-рейтинг из верхнего блока профиля."""
        rating_tag = player_info.select_one("h3 dfn")
        return parse_int(rating_tag.get_text()) if rating_tag else None

    def _get_strong_value(self, section: Tag, label: str) -> str | None:
        """Находит значение поля профиля по подписи рядом с strong."""
        for p in section.select("p"):
            if label.lower() in clean_text(p.get_text()).lower():
                strong = p.select_one("strong")
                return clean_text(strong.get_text()) if strong else None

        return None

    def _parse_registered_at(self, player_info: Tag) -> tuple[str | None, str | None]:
        """Достает даты регистрации и последнего визита, если они есть."""
        for p in player_info.select("p"):
            if "На сайте с" not in clean_text(p.get_text()):
                continue

            values = [clean_text(tag.get_text()) for tag in p.select("strong")]
            return (
                values[0] if len(values) > 0 else None,
                values[1] if len(values) > 1 else None,
            )

        return None, None

    def _parse_profile_links(self, player_info: Tag) -> list[ProfileLink]:
        """Собирает ссылки из блока профиля: комментарии, результаты, статистика и т.д."""
        links: list[ProfileLink] = []

        for link in player_info.select("p a[href]"):
            title = clean_text(link.get_text())
            if title:
                links.append(ProfileLink(title=title, url=absolute_url(link.get("href")) or ""))

        return links

    def _parse_max_rating(self, soup: BeautifulSoup) -> MaxRating:
        """Достает максимальный рейтинг за все время."""
        tag = soup.select_one("#maxAll_s")
        if not tag:
            return MaxRating(rating=None, date=None)

        text = clean_text(tag.get_text())
        date_match = re.search(r"\(([^)]+)\)", text)

        return MaxRating(
            rating=parse_int(text),
            date=date_match.group(1) if date_match else None,
        )

    def _parse_stats(self, soup: BeautifulSoup) -> PlayerStats:
        """Парсит агрегированную статистику игрока."""
        section = soup.select_one(".player-stats")
        if not section:
            return PlayerStats()

        rows: dict[str, Tag] = {}

        # В HTML RTTF статистика лежит в таблицах: первый td — название, второй td — значение.
        for tr in section.select("tr"):
            cells = tr.select("td")
            if len(cells) >= 2:
                rows[clean_text(cells[0].get_text()).rstrip(":")] = cells[1]

        games_total = wins = losses = None
        games_cell = rows.get("Игры (победы-поражения)")
        games_text = clean_text(games_cell.get_text()) if games_cell else None

        if games_text:
            match = re.search(r"(\d+)\s*\((\d+)\s*-\s*(\d+)\)", games_text)
            if match:
                games_total, wins, losses = map(int, match.groups())

        favorite_cell = rows.get("Чаще всего в")
        favorite_link = favorite_cell.select_one("a") if favorite_cell else None
        favorite_text = clean_text(favorite_cell.get_text()) if favorite_cell else ""

        cup_cell = next((cell for label, cell in rows.items() if label.startswith("Допуск на")), None)
        cup_text = clean_text(cup_cell.get_text()) if cup_cell else ""

        return PlayerStats(
            rank_place=parse_int(self._row_text(rows, "Место в рейтинге")),
            tournaments_count=parse_int(self._row_text(rows, "Сыграно турниров")),
            games_total=games_total,
            wins=wins,
            losses=losses,
            first_tournament=self._row_text(rows, "Первый турнир"),
            favorite_hall=clean_text(favorite_link.get_text()) if favorite_link else None,
            favorite_hall_url=absolute_url(favorite_link.get("href")) if favorite_link else None,
            favorite_hall_tournaments_count=self._parse_count_by_label(favorite_text, "турниров"),
            rttf_cup_rating=parse_int(cup_cell.select_one("dfn").get_text())
            if cup_cell and cup_cell.select_one("dfn")
            else None,
            rttf_cup_tournaments_count=self._parse_count_by_label(cup_text, "турниров"),
            rttf_cup_games_count=self._parse_count_by_label(cup_text, "игр"),
        )

    def _parse_rating_history(self, html: str) -> list[RatingPoint]:
        """Достает историю рейтинга из JS-массивов графика."""
        labels_match = re.search(r"chartAllLabels_s\s*=\s*(\[.*?\]);", html, re.DOTALL)
        data_match = re.search(r"chartAllData_s\s*=\s*(\[.*?\]);", html, re.DOTALL)

        if not labels_match or not data_match:
            log.warning("Rating history variables were not found")
            return []

        labels = json.loads(labels_match.group(1))
        ratings = json.loads(data_match.group(1))

        return [
            RatingPoint(date=date, rating=int(rating))
            for date, rating in zip(labels, ratings)
            if date and date != "..."
        ]

    def _parse_best_wins(self, soup: BeautifulSoup) -> list[BestWin]:
        """Парсит таблицу лучших побед."""
        section = soup.select_one(".player-wins")
        if not section:
            return []

        wins: list[BestWin] = []

        for row in section.select("tbody tr"):
            cells = row.select("td")
            if len(cells) < 7:
                continue

            tournament_link = cells[0].select_one("a")
            opponent_link = cells[2].select_one("a")

            wins.append(
                BestWin(
                    tournament_title=clean_text(tournament_link.get_text())
                    if tournament_link
                    else cell_text(row, 0),
                    tournament_url=absolute_url(tournament_link.get("href"))
                    if tournament_link
                    else None,
                    player_rating=parse_int(cell_text(row, 1)),
                    opponent_name=clean_text(opponent_link.get_text())
                    if opponent_link
                    else cell_text(row, 2),
                    opponent_url=absolute_url(opponent_link.get("href"))
                    if opponent_link
                    else None,
                    opponent_rating=parse_int(cell_text(row, 3)),
                    score=cell_text(row, 4),
                    rating_delta=parse_float(cell_text(row, 5)),
                    duration=cell_text(row, 6),
                    interval=row.get("class", [None])[0] if row.get("class") else None,
                )
            )

        return wins

    def _parse_medals(self, soup: BeautifulSoup) -> list[MedalHall]:
        """Парсит блок наград по залам."""
        medals: list[MedalHall] = []

        for item in soup.select(".player-medals .medals"):
            onclick = item.get("onclick") or ""
            url_match = re.search(r"location='([^']+)'", onclick)
            hall_tag = item.select_one("b")

            medals.append(
                MedalHall(
                    hall_name=clean_text(hall_tag.get_text()) if hall_tag else None,
                    gold=bool(item.select_one(".gold")),
                    silver=bool(item.select_one(".silver")),
                    bronze=bool(item.select_one(".bronze")),
                    url=absolute_url(url_match.group(1)) if url_match else None,
                )
            )

        return medals

    def _parse_recent_results(self, soup: BeautifulSoup) -> list[TournamentResult]:
        """Парсит последние турниры и матчи внутри них."""
        section = soup.select_one(".player-results")
        if not section:
            return []

        results: list[TournamentResult] = []
        current_link: Tag | None = None
        current_participants: int | None = None

        # Структура блока: ссылка турнира -> количество участников -> таблица результата.
        for child in section.children:
            if not isinstance(child, Tag):
                continue

            if child.name == "a" and child.get("href", "").startswith("tournaments/"):
                current_link = child
                current_participants = None
            elif child.name == "kbd" and current_link:
                current_participants = parse_int(clean_text(child.get_text()))
            elif child.name == "table" and current_link:
                results.append(
                    self._parse_tournament_table(
                        link=current_link,
                        participants_count=current_participants,
                        table=child,
                    )
                )
                current_link = None
                current_participants = None

        return results

    def _parse_tournament_table(
        self,
        *,
        link: Tag,
        participants_count: int | None,
        table: Tag,
    ) -> TournamentResult:
        """Парсит один турнирный блок."""
        title = clean_text(link.get_text())
        title_match = re.match(
            r"(?P<date_time>\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})\s+(?P<rest>.*)",
            title,
        )
        rating_limit_tag = link.select_one("var")

        header = table.select_one("thead tr td")
        place_tag = header.select_one("i:not(.gift)") if header else None

        medal = None
        if place_tag:
            classes = set(place_tag.get("class", []))
            if "gold" in classes:
                medal = "gold"
            elif "silver" in classes:
                medal = "silver"
            elif "bronze" in classes:
                medal = "bronze"

        body_list = table.select("tbody")
        match_rows = body_list[0].select("tr") if body_list else []
        total_row = body_list[1].select_one("tr") if len(body_list) > 1 else None

        return TournamentResult(
            title=title,
            url=absolute_url(link.get("href")),
            date_time=title_match.group("date_time") if title_match else None,
            rating_limit=parse_int(rating_limit_tag.get_text()) if rating_limit_tag else None,
            hall_name=self._parse_hall_name(title_match, rating_limit_tag),
            participants_count=participants_count,
            place=clean_text(place_tag.get_text()) if place_tag else None,
            medal=medal,
            player_rating_before=parse_int(header.select_one("dfn").get_text())
            if header and header.select_one("dfn")
            else None,
            total_score=cell_text(total_row, 4) if total_row else None,
            total_rating_delta=parse_float(cell_text(total_row, 5)) if total_row else None,
            total_duration=cell_text(total_row, 6) if total_row else None,
            rating_after=parse_int(cell_text(total_row, 7)) if total_row else None,
            matches=[self._parse_match_row(row) for row in match_rows],
        )

    def _parse_match_row(self, row: Tag) -> MatchResult:
        """Парсит одну строку матча из таблицы турнира."""
        opponent_link = row.select_one("td:nth-of-type(3) a")
        score_cell = row.select("td")[4] if len(row.select("td")) > 4 else None
        score = clean_text(score_cell.get_text()) if score_cell else None
        history_link = row.select_one('a[href^="games/"]')

        return MatchResult(
            start_time=cell_text(row, 0),
            stage=cell_text(row, 1),
            opponent_name=clean_text(opponent_link.get_text()) if opponent_link else cell_text(row, 2),
            opponent_url=absolute_url(opponent_link.get("href")) if opponent_link else None,
            opponent_rating=parse_int(cell_text(row, 3)),
            score=score,
            rating_delta=parse_float(cell_text(row, 5)),
            duration=cell_text(row, 6),
            history_url=absolute_url(history_link.get("href")) if history_link else None,
            is_win=False if score_cell and "minus" in score_cell.get("class", []) else True if score else None,
        )

    @staticmethod
    def _row_text(rows: dict[str, Tag], label: str) -> str | None:
        """Безопасно достает текст значения из словаря строк статистики."""
        cell = rows.get(label)
        return clean_text(cell.get_text()) if cell else None

    @staticmethod
    def _parse_count_by_label(text: str, label: str) -> int | None:
        """Достает число после подписи вида `турниров: 11`."""
        match = re.search(rf"{re.escape(label)}:\s*\d+", text)
        return parse_int(match.group(0)) if match else None

    @staticmethod
    def _parse_hall_name(title_match: re.Match[str] | None, rating_limit_tag: Tag | None) -> str | None:
        """Достает название зала из заголовка турнира."""
        if not title_match:
            return None

        hall_name = title_match.group("rest")
        if rating_limit_tag:
            hall_name = hall_name.replace(clean_text(rating_limit_tag.get_text()), "")

        return hall_name.strip() or None