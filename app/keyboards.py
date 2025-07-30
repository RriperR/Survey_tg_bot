from datetime import datetime
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils import SelectDoctor, DoctorsPage
from database.requests import get_unregistered_workers, get_all_workers


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


PER_PAGE = 10

# --- Клавиатура со списком врачей (пагинация) ---
async def build_all_doctors_keyboard(page: int = 0) -> InlineKeyboardMarkup:
    workers = await get_all_workers()  # -> list[Worker] (Worker имеет id и full_name)
    total = len(workers)
    start = page * PER_PAGE
    end = min(start + PER_PAGE, total)

    builder = InlineKeyboardBuilder()

    # Кнопки врачей: короткий callback_data с id
    for w in workers[start:end]:
        builder.button(
            text=w.full_name[:64],  # на всякий случай ограничим текст кнопки
            callback_data=SelectDoctor(doctor_id=w.id).pack()
        )

    # Навигация
    nav = InlineKeyboardBuilder()
    if start > 0:
        nav.button(text="◀️ Назад", callback_data=DoctorsPage(page=page-1).pack())
    if end < total:
        nav.button(text="Вперёд ▶️", callback_data=DoctorsPage(page=page+1).pack())

    builder.adjust(1)  # по одной кнопке в ряд
    if nav.buttons:
        builder.row(*nav.buttons)  # ряд с навигацией

    return builder.as_markup()


def build_cancel_shift_keyboard(shift_type: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Отменить запись",
        callback_data=f"cancel_shift:{shift_type}"
    )
    builder.adjust(1)
    return builder.as_markup()