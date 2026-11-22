import logging
from logging.handlers import RotatingFileHandler

import config

LOGGER_NAME = "finance_agent"


def sanitise(value: object, limit: int = 500) -> str:
    text = str(value)
    if config.API_KEY:
        text = text.replace(config.API_KEY, "***")
    if len(text) > limit:
        return text[:limit] + "…"
    return text


def get_logger(name: str = "") -> logging.Logger:
    return logging.getLogger(f"{LOGGER_NAME}.{name}" if name else LOGGER_NAME)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    level = getattr(logging, config.LOG_LEVEL, logging.INFO)
    logger.setLevel(level)
    logger.propagate = False
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = config.LOG_DIR / config.LOG_FILE
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_level = getattr(logging, config.LOG_CONSOLE_LEVEL, logging.WARNING)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    logger.debug("Логирование настроено: %s", log_path)
    return logger
