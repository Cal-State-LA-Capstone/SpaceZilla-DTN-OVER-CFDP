import logging
import os
from logging.handlers import RotatingFileHandler

ROOT_LOGGER_NAME = "spacezilla"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
LOG_FILE = "spacezilla.log"
MAX_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 3


def setup_logging(
    log_dir: str = "logs",
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG,
) -> None:
    """Call once at app startup to configure logging handlers."""
    logger = logging.getLogger(ROOT_LOGGER_NAME)

    if logger.handlers:
        return

    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter(LOG_FORMAT)

    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(formatter)
    logger.addHandler(console)

    os.makedirs(log_dir, exist_ok=True)
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, LOG_FILE),
        maxBytes=MAX_BYTES,
        backupCount=BACKUP_COUNT,
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the spacezilla namespace."""
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")
