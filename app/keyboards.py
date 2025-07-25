from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.requests import get_unregistered_workers


async def build_worker_keyboard() -> InlineKeyboardMarkup:

    workers = await get_unregistered_workers()
    print(f"Found {len(workers)} unregistered workers")

    builder = InlineKeyboardBuilder()

    if not workers:
        builder.button(
            text="Нет доступных сотрудников",
            callback_data="noop"
        )

    for worker in workers:
        builder.button(
            text=worker.full_name,
            callback_data=f"select_worker:{worker.id}"
        )

    builder.adjust(1)
    return builder.as_markup()


async def build_confirm_keyboard(worker_id: int) -> InlineKeyboardMarkup:
    print('building confirm kb')
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Да", callback_data=f"confirm_yes:{worker_id}"
            ),
            InlineKeyboardButton(
                text="❌ Нет", callback_data="confirm_no"
            )
        ]
    ])


async def build_int_keyboard(question_index) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    timestamp = int(datetime.now().timestamp())

    for i in range(1,6):
        builder.button(
            text=str(i),
            callback_data=f"rate:{question_index}:{i}:{timestamp}"
        )
    builder.adjust(5)
    return builder.as_markup()


async def build_doctors_keyboard(doctors: list[str]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for doc in doctors:
        builder.button(
            text=doc,
            callback_data=f"select_doctor:{doc}"
        )
    builder.adjust(1)
    return builder.as_markup()