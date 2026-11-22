from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI


@tool
def format_market_snapshot(
    ticker: str,
    price: float,
    change_percent: float,
    market_cap: float | None = None,
    pe: float | None = None,
) -> str:
    """Форматирует рыночный снимок по одной акции в краткую сводку.

    Args:
        ticker: Биржевой тикер, например AAPL.
        price: Текущая цена акции.
        change_percent: Изменение цены за день в процентах.
        market_cap: Рыночная капитализация, опционально.
        pe: Коэффициент P/E, опционально.
    """
    lines = [
        f"{ticker}: цена ${price:.2f}, изменение за день {change_percent:+.2f}%."
    ]

    if market_cap is not None:
        lines.append(f"Капитализация: ${market_cap:,.0f}.")
    if pe is not None:
        lines.append(f"P/E: {pe:.2f}.")

    if change_percent > 0:
        lines.append("Акция растёт в течение текущей сессии.")
    elif change_percent < 0:
        lines.append("Акция снижается в течение текущей сессии.")
    else:
        lines.append("Цена практически не изменилась.")

    return " ".join(lines)


# Собственный tool агента: здесь он получает уже подготовленные данные.
# В полноценной версии этот tool сам вызывал бы finance_tickers_lookup
# и finance_quotes, а затем передавал результат в format_market_snapshot.
@tool
def get_market_snapshot(ticker: str) -> str:
    """Возвращает краткую рыночную сводку по тикеру.

    Args:
        ticker: Биржевой тикер, например AAPL.
    """
    # Демонстрационные значения; замените на вызов финансового API.
    return format_market_snapshot.invoke(
        {
            "ticker": ticker,
            "price": 250.0,
            "change_percent": 1.25,
            "market_cap": 3_700_000_000_000,
            "pe": 33.4,
        }
    )


agent = create_agent(
    model=ChatOpenAI(model="gpt-4o-mini"),
    tools=[get_market_snapshot],
    system_prompt=(
        "Ты финансовый аналитик-ассистент. "
        "Отвечай кратко, по-русски и всегда указывай, что данные "
        "нужно перепроверить перед принятием инвестиционных решений. "
        "Для вопросов о текущей цене или динамике акции используй "
        "инструмент get_market_snapshot."
    ),
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "Дай краткую сводку по AAPL"}]}
)

print(result["messages"][-1].content)

from langchain.agents import create_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from finance_client import FinanceClient  # ваш клиент или SDK финансового источника

finance = FinanceClient(api_key="ВАШ_API_КЛЮЧ")


@tool
def resolve_tickers(queries: list[str]) -> dict[str, str]:
    """Преобразует названия компаний, ETF, индексов или криптовалют в биржевые тикеры.

    Args:
        queries: Список названий или приблизительных тикеров,
            например ["Apple", "Microsoft", "S&P 500"].
    """
    result = finance.tickers_lookup(queries=queries)

    # Приводим ответ API к простому словарю: название -> тикер.
    return {
        item["query"]: item["symbol"]
        for item in result["matches"]
    }


@tool
def get_quotes(tickers: list[str], fields: list[str]) -> list[dict]:
    """Получает текущие рыночные котировки для списка тикеров.

    Args:
        tickers: Список тикеров, например ["AAPL", "MSFT"].
        fields: Нужные поля, например ["price", "change", "marketCap", "pe"].
    """
    result = finance.quotes(
        ticker_symbols=tickers,
        fields=fields,
    )

    return result["quotes"]


@tool
def compare_companies(tickers: list[str]) -> str:
    """Сравнивает компании по цене, изменению за день, капитализации и P/E.

    Args:
        tickers: Список тикеров для сравнения, например ["AAPL", "MSFT"].
    """
    quotes = finance.quotes(
        ticker_symbols=tickers,
        fields=["price", "change", "marketCap", "pe"],
    )["quotes"]

    rows = []
    for quote in quotes:
        rows.append(
            f"{quote['symbol']}: цена ${quote['price']}, "
            f"изменение {quote['change']:+.2f}%, "
            f"капитализация ${quote['marketCap']:,.0f}, "
            f"P/E {quote['pe']}"
        )

    return "\n".join(rows)


agent = create_agent(
    model=ChatOpenAI(model="gpt-4o-mini"),
    tools=[resolve_tickers, get_quotes, compare_companies],
    system_prompt=(
        "Ты финансовый аналитик-ассистент.\n"
        "Правила:\n"
        "1. Если пользователь назвал компанию словами, сначала вызови resolve_tickers.\n"
        "2. Для текущих котировок используй get_quotes.\n"
        "3. Для сравнения нескольких компаний используй compare_companies.\n"
        "4. Не выдумывай цифры: используй только результаты tools.\n"
        "5. Отвечай по-русски, кратко и с оговоркой, что это не инвестиционная рекомендация."
    ),
)

response = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Сравни Apple и Microsoft по цене, капитализации и P/E",
            }
        ]
    }
)

print(response["messages"][-1].content)
