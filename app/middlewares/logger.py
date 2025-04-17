import logging
import os
from pathlib import Path
from dotenv import load_dotenv

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from typing import Callable, Awaitable, Dict, Any


# Папка для логов
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Основной лог-файл
LOG_FILE = LOG_DIR / "user_activity.log"

# Конфигурация логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ]
)

logger = logging.getLogger("user_logger")


load_dotenv()

LOG_CHAT_ID = os.getenv("LOG_CHAT_ID")


class GroupLoggerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем бота и пользователя
        bot = data["bot"]
        user = event.from_user

        username = f"@{user.username}" if user.username else "[без username]"
        full_name = user.full_name

        if event.text:
            if event.text.startswith("/"):
                log_text = f'Пользователь {username} "{full_name}" использовал команду {event.text}'
            else:
                log_text = f'Пользователь {username} "{full_name}" пишет "{event.text.strip()}"'

            # 🧾 Лог в файл
            logger.info(log_text)


        return await handler(event, data)
