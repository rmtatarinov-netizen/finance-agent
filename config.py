import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
PROXYAPI_BASE_URL = (
    os.getenv("PROXYAPI_BASE_URL")
    or os.getenv("OPENAI_BASE_URL")
    or "https://api.proxyapi.ru/v1"
)
API_KEY = os.getenv("PROXYAPI_API_KEY") or os.getenv("OPENAI_API_KEY")
TEMPERATURE = float(os.getenv("MODEL_TEMPERATURE", "0.2"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "30"))
LOOKUP_LIMIT = int(os.getenv("LOOKUP_LIMIT", "5"))
MAX_TICKERS = int(os.getenv("MAX_TICKERS", "10"))
MAX_SEARCH_QUERIES = int(os.getenv("MAX_SEARCH_QUERIES", "10"))
MAX_OUTPUT_CHARS = int(os.getenv("MAX_OUTPUT_CHARS", "4000"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_CONSOLE_LEVEL = os.getenv("LOG_CONSOLE_LEVEL", "WARNING").upper()
LOG_DIR = Path(os.getenv("LOG_DIR", "logs"))
if not LOG_DIR.is_absolute():
    LOG_DIR = Path(__file__).resolve().parent / LOG_DIR
LOG_FILE = os.getenv("LOG_FILE", "app.log")
LOG_MAX_BYTES = int(os.getenv("LOG_MAX_BYTES", str(10 * 1024 * 1024)))
LOG_BACKUP_COUNT = int(os.getenv("LOG_BACKUP_COUNT", "5"))
LOG_USER_MESSAGES = os.getenv("LOG_USER_MESSAGES", "false").lower() in {
    "1", "true", "yes", "y",
}


def get_api_key() -> str:
    """Возвращает ключ ProxyAPI (или OPENAI_API_KEY для совместимости)."""
    if not API_KEY:
        raise RuntimeError(
            "PROXYAPI_API_KEY не задан. Добавьте ключ ProxyAPI в .env "
            "или переменные окружения."
        )
    return API_KEY


def require_api_key() -> None:
    """Проверяет наличие ключа для доступа к модели."""
    get_api_key()
