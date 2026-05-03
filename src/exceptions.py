class RttfParserError(Exception):
    """Базовая ошибка парсера RTTF."""


class FetchError(RttfParserError):
    """Ошибка загрузки страницы RTTF."""


class InvalidPlayerPageError(RttfParserError):
    """Ошибка, когда HTML не похож на страницу игрока."""


class ParserStructureError(RttfParserError):
    """Ошибка, когда обязательный HTML-блок отсутствует или изменился."""