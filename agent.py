from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

import config
from logging_config import get_logger
from tools import TOOLS

logger = get_logger("agent")

SYSTEM_PROMPT = """Ты финансовый аналитик-ассистент. Твоя задача — собрать и объяснить рыночные данные, а не принимать инвестиционные решения.

## Маршрут работы

1. Если в вопросе названы компании или неявные тикеры, вызови `resolve_tickers` и получи биржевые тикеры.
2. Вызови `get_quotes` с найденными тикерами и нужными полями: `price`, `change_percent`, `marketCap`, `pe`, `volume`.
3. Если нужен краткий текстовый снимок по одному тикеру, вызови `format_market_snapshot`.
4. Ответь по-русски тремя блоками:
   - **Данные** — только значения, полученные от инструментов.
   - **Краткий вывод** — фактологическое сравнение (например, у кого выше P/E), без советов что покупать или продавать.
   - **Ограничения анализа** — источник Yahoo Finance, возможная задержка котировок, P/E обычно trailing, пропущенные поля помечены как «нет данных», ответ не является инвестиционной рекомендацией.

## Правила

- Не используй рыночные числа из памяти: все значения должны прийти из tools.
- Не давай рекомендаций «покупать», «продавать», «держать» и не обещай доходность.
- Если инструмент вернул ошибку или «нет данных», скажи об этом прямо.
- Отвечай кратко, в языке вопроса пользователя.
"""


def build_agent():
    logger.info(
        "Сборка агента: model=%s, base_url=%s, tools=%d",
        config.MODEL,
        config.PROXYAPI_BASE_URL,
        len(TOOLS),
    )
    model = init_chat_model(
        config.MODEL,
        api_key=config.get_api_key(),
        base_url=config.PROXYAPI_BASE_URL,
        temperature=config.TEMPERATURE,
        timeout=config.REQUEST_TIMEOUT,
        max_retries=2,
    )
    agent = create_agent(
        model=model,
        tools=TOOLS,
        system_prompt=SYSTEM_PROMPT,
        checkpointer=InMemorySaver(),
    )
    logger.info("Агент собран")
    return agent
