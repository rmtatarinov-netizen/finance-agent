import re

import yfinance as yf
from langchain_core.tools import tool

import config
from logging_config import get_logger, sanitise

logger = get_logger("tools")

TICKER_PATTERN = re.compile(r"^[A-Z0-9.\-^]{1,15}$")
FIELD_ALIASES = {
    "price": "price",
    "change": "change_percent",
    "change_percent": "change_percent",
    "marketCap": "marketCap",
    "market_cap": "marketCap",
    "marketcap": "marketCap",
    "pe": "pe",
    "pe_ratio": "pe",
    "volume": "volume",
}
SUPPORTED_FIELDS = ("price", "change_percent", "marketCap", "pe", "volume")
INFO_KEYS = {
    "price": ("regularMarketPrice", "currentPrice", "lastPrice"),
    "change_percent": ("regularMarketChangePercent",),
    "marketCap": ("marketCap",),
    "pe": ("trailingPE",),
    "volume": ("regularMarketVolume", "volume"),
}
FAST_KEYS = {
    "price": ("lastPrice", "regularMarketPrice"),
    "change_percent": ("regularMarketChangePercent",),
    "marketCap": ("marketCap",),
    "pe": ("trailingPE",),
    "volume": ("regularMarketVolume", "lastVolume"),
}


def _normalise_fields(fields: list[str] | None) -> list[str]:
    if not fields:
        return list(SUPPORTED_FIELDS)
    result = []
    for name in fields:
        field = FIELD_ALIASES.get(name.lower().replace(" ", ""))
        if field and field not in result:
            result.append(field)
    return result or list(SUPPORTED_FIELDS)


def _first_value(*sources: dict, keys: tuple[str, ...]):
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value is not None:
                return value
    return None


def _format_number(value, kind: str) -> str:
    number = float(value)
    if kind == "marketCap":
        if number >= 1e12:
            return f"{number / 1e12:.2f} трлн USD"
        if number >= 1e9:
            return f"{number / 1e9:.2f} млрд USD"
        if number >= 1e6:
            return f"{number / 1e6:.2f} млн USD"
        return f"{number:,.0f} USD"
    if kind == "volume":
        if number >= 1e9:
            return f"{number / 1e9:.2f} млрд"
        if number >= 1e6:
            return f"{number / 1e6:.2f} млн"
        return f"{number:,.0f}"
    return f"{number:,.2f}"


@tool
def format_market_snapshot(
    ticker: str,
    price: float | None = None,
    change_percent: float | None = None,
    market_cap: float | None = None,
    pe: float | None = None,
) -> str:
    """Форматирует рыночный снимок одной акции в краткую сводку.

    Args:
        ticker: Биржевой тикер, например AAPL.
        price: Текущая цена, опционально.
        change_percent: Изменение за день в процентах, опционально.
        market_cap: Рыночная капитализация, опционально.
        pe: Коэффициент P/E, опционально.
    """
    lines = [f"{ticker.upper()}:"]
    lines.append(
        f"цена ${float(price):,.2f}." if price is not None else "цена: нет данных."
    )
    if change_percent is not None:
        lines.append(f"изменение за день {float(change_percent):+.2f}%.")
    if market_cap is not None:
        lines.append(f"Капитализация: ${float(market_cap):,.0f}.")
    if pe is not None:
        lines.append(f"P/E: {float(pe):.2f}.")
    return " ".join(lines)


@tool
def resolve_tickers(
    queries: list[str],
    limit: int = config.LOOKUP_LIMIT,
) -> str:
    """Преобразует названия компаний в биржевые тикеры через Yahoo Finance.

    Args:
        queries: Список названий или приблизительных тикеров,
            например ["Apple", "Microsoft"].
        limit: Максимальное число тикеров на запрос.
    """
    safe_limit = max(1, min(int(limit), config.MAX_TICKERS))
    queries = [q.strip() for q in queries if isinstance(q, str) and q.strip()]
    queries = queries[: config.MAX_SEARCH_QUERIES]
    logger.info("resolve_tickers: запросов=%d, limit=%d", len(queries), safe_limit)
    if not queries:
        logger.warning("resolve_tickers: пустой список запросов")
        return "Ошибка: пустой список запросов."

    lines = []
    for query in queries:
        try:
            search = yf.Search(query, max_results=max(5, safe_limit * 3))
            matches = search.quotes or []
            chosen = []
            for match in matches:
                if str(match.get("quoteType", "")).upper() != "EQUITY":
                    continue
                symbol = str(match.get("symbol", "")).strip().upper()
                if not symbol:
                    continue
                if symbol == query.upper():
                    chosen = [match]
                    break
                chosen.append(match)
            if not chosen:
                logger.warning("resolve_tickers: акций не найдено для %r", sanitise(query, 120))
                lines.append(f"{query}: акций не найдено.")
                continue
            for match in chosen[:safe_limit]:
                symbol = str(match.get("symbol", "")).strip().upper()
                name = (
                    match.get("longname")
                    or match.get("shortname")
                    or match.get("displayName")
                    or ""
                )
                exchange = match.get("exchange", "")
                sector = match.get("sector", "")
                description = f"{name}, {exchange}, {sector}".strip(", ")
                lines.append(f"{query} -> {symbol} ({description})" if description else f"{query} -> {symbol}")
        except Exception as exc:
            logger.warning(
                "resolve_tickers: ошибка поиска для %r: %s: %s",
                sanitise(query, 120),
                type(exc).__name__,
                sanitise(exc),
            )
            lines.append(f"{query}: ошибка поиска ({type(exc).__name__}).")
    logger.debug("resolve_tickers: сформировано строк=%d", len(lines))
    return "\n".join(lines)


@tool
def get_quotes(
    tickers: list[str],
    fields: list[str] | None = None,
) -> str:
    """Возвращает текущие рыночные котировки для списка тикеров.

    Args:
        tickers: Список тикеров, например ["AAPL", "MSFT"].
        fields: Нужные поля: price, change_percent, marketCap, pe, volume.
            По умолчанию возвращаются все поля.
    """
    normalised_tickers = [str(t).strip().upper() for t in tickers if str(t).strip()]
    logger.info(
        "get_quotes: тикеров=%d, полей=%s",
        len(normalised_tickers),
        sanitise(fields or SUPPORTED_FIELDS, 200),
    )
    if not normalised_tickers:
        logger.warning("get_quotes: пустой список тикеров")
        return "Ошибка: пустой список тикеров."
    invalid = [t for t in normalised_tickers if not TICKER_PATTERN.fullmatch(t)]
    if invalid:
        logger.warning("get_quotes: некорректные тикеры: %s", sanitise(invalid, 200))
        return f"Некорректные тикеры: {', '.join(invalid)}."

    if len(normalised_tickers) > config.MAX_TICKERS:
        normalised_tickers = normalised_tickers[: config.MAX_TICKERS]
    normalised_fields = _normalise_fields(fields)
    allowed = set(SUPPORTED_FIELDS)
    unsupported = [f for f in (fields or []) if FIELD_ALIASES.get(str(f).lower().replace(" ", "")) not in allowed]
    if unsupported:
        logger.warning("get_quotes: неподдерживаемые поля: %s", sanitise(unsupported, 200))
        return f"Неподдерживаемые поля: {', '.join(map(str, unsupported))}. Доступные: {', '.join(SUPPORTED_FIELDS)}."

    lines = []
    for symbol in normalised_tickers:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info or {}
            try:
                fast = ticker.fast_info or {}
            except Exception:
                fast = {}

            previous_close = _first_value(info, fast, keys=("previousClose", "previous_close"))
            values = {}
            for field in normalised_fields:
                value = _first_value(info, fast, keys=INFO_KEYS[field])
                if value is None:
                    value = _first_value(fast, keys=FAST_KEYS[field])
                if field == "change_percent" and value is None and previous_close:
                    price = _first_value(info, fast, keys=INFO_KEYS["price"])
                    if price is not None:
                        value = (float(price) / float(previous_close) - 1) * 100
                values[field] = value

            lines.append(
                format_market_snapshot.invoke(
                    {
                        "ticker": symbol,
                        "price": values.get("price"),
                        "change_percent": values.get("change_percent"),
                        "market_cap": values.get("marketCap"),
                        "pe": values.get("pe"),
                    }
                )
            )
            if "volume" in normalised_fields:
                volume = values.get("volume")
                if volume is not None:
                    lines.append(f"Объём: {_format_number(volume, 'volume')}.")
            missing = [
                field for field in normalised_fields
                if field != "price" and values.get(field) is None
            ]
            if missing:
                labels = {
                    "change_percent": "изменение за день",
                    "marketCap": "капитализация",
                    "pe": "P/E",
                    "volume": "объём",
                }
                lines.append("Нет данных: " + ", ".join(labels[field] for field in missing) + ".")
        except Exception as exc:
            logger.warning(
                "get_quotes: ошибка для %s: %s: %s",
                symbol,
                type(exc).__name__,
                sanitise(exc),
            )
            lines.append(f"{symbol}: не удалось получить данные ({type(exc).__name__}).")

    lines.append("Источник: Yahoo Finance (yfinance). Данные могут быть с задержкой; P/E — trailing.")
    result = "\n".join(lines)
    logger.debug("get_quotes: сформировано строк=%d, длина=%d", len(lines), len(result))
    if len(result) > config.MAX_OUTPUT_CHARS:
        logger.warning(
            "get_quotes: вывод обрезан с %d до %d символов",
            len(result),
            config.MAX_OUTPUT_CHARS,
        )
        return result[: config.MAX_OUTPUT_CHARS] + "\n… вывод обрезан."
    return result


TOOLS = [resolve_tickers, get_quotes, format_market_snapshot]
