import logging
from logging.handlers import TimedRotatingFileHandler
import os

LOG_DIR = "../logs"

def setup_logger(name: str, filename: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:  # чтобы не добавлять хендлеры повторно
        handler = TimedRotatingFileHandler(
            filename=os.path.join(LOG_DIR, filename),
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8"
        )
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
