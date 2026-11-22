import uuid

import config
from agent import build_agent
from config import require_api_key
from logging_config import get_logger, sanitise, setup_logging

logger = get_logger("main")


def message_text(message) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif hasattr(block, "text"):
                parts.append(block.text)
        return "".join(parts)
    return str(content)


def log_user_message(user_input: str) -> None:
    if config.LOG_USER_MESSAGES:
        logger.info("Запрос пользователя: %s", sanitise(user_input, 200))
    else:
        logger.info("Получен запрос длиной %d символов", len(user_input))


def main() -> None:
    setup_logging()
    logger.info("Запуск приложения")
    require_api_key()
    agent = build_agent()
    thread = {"configurable": {"thread_id": str(uuid.uuid4())}}
    logger.info("Агент готов, thread_id=%s", thread["configurable"]["thread_id"])
    print("Финансовый аналитик-агент готов. Источник данных: Yahoo Finance (yfinance).")
    print("Команды: exit — выход, new — начать новый диалог.")

    while True:
        try:
            user_input = input("You> ").strip()
        except (EOFError, KeyboardInterrupt):
            logger.info("Завершение работы по действию пользователя")
            print()
            break
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "выход"}:
            logger.info("Выход по команде пользователя")
            break
        if user_input.lower() in {"new", "новый"}:
            thread = {"configurable": {"thread_id": str(uuid.uuid4())}}
            logger.info("Начат новый диалог, thread_id=%s", thread["configurable"]["thread_id"])
            print("Начат новый диалог.")
            continue

        log_user_message(user_input)
        try:
            result = agent.invoke(
                {"messages": [{"role": "user", "content": user_input}]},
                config=thread,
            )
            answer = message_text(result["messages"][-1])
            logger.info(
                "Ответ агента сформирован, сообщений=%d, длина=%d",
                len(result.get("messages", [])),
                len(answer),
            )
            print(f"Agent> {answer}")
        except Exception as exc:
            logger.error(
                "Ошибка обработки запроса: %s: %s",
                type(exc).__name__,
                sanitise(exc),
            )
            print(f"Ошибка: {exc}")


if __name__ == "__main__":
    main()
