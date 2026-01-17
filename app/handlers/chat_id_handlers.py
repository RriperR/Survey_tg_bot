from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.logger import setup_logger


logger = setup_logger("chat_id", "chat_id.log")


def create_chat_id_router() -> Router:
    router = Router()

    @router.message(Command("chat_id"))
    async def show_chat_id(message: Message):
        chat_id = message.from_user.id
        await message.answer(f"Ваш chat id: {chat_id}")
        logger.info("User requested chat id: %s", chat_id)

    return router
