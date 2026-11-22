import logging
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import config
import logging_config


class LoggingTests(unittest.TestCase):
    def setUp(self):
        self._reset_logger()

    def tearDown(self):
        self._reset_logger()

    @staticmethod
    def _reset_logger():
        logger = logging.getLogger(logging_config.LOGGER_NAME)
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    def test_sanitise_hides_api_key(self):
        with patch.object(config, "API_KEY", "super-secret"):
            result = logging_config.sanitise("key=super-secret end")
        self.assertEqual(result, "key=*** end")

    def test_sanitise_truncates_long_text(self):
        result = logging_config.sanitise("x" * 120, limit=10)
        self.assertEqual(result, "xxxxxxxxxx…")

    def test_setup_logging_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch.multiple(
                config,
                LOG_DIR=Path(tmp),
                LOG_FILE="app.log",
                LOG_LEVEL="INFO",
                LOG_CONSOLE_LEVEL="CRITICAL",
            ):
                logger = logging_config.setup_logging()
                logger.info("тестовая запись")
                for handler in logger.handlers:
                    handler.flush()
                content = (Path(tmp) / "app.log").read_text(encoding="utf-8")
                self.assertIn("тестовая запись", content)
                self.assertIn("finance_agent", content)


if __name__ == "__main__":
    unittest.main()
