from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

import database.requests as rq
from keyboards import build_doctors_keyboard
from logger import setup_logger
from utils import get_doctors_from_sheet

router = Router()

logger = setup_logger("shift", "shift.log")


@router.message(Command("shift"))
async def show_doctors(message: Message):
    doctors = get_doctors_from_sheet()
    if not doctors:
        await message.answer("Список врачей пуст")
        return
    await message.answer(
        "Выберите врача:",
        reply_markup=await build_doctors_keyboard(doctors)
    )


@router.callback_query(F.data.startswith("select_doctor:"))
async def mark_shift(callback: CallbackQuery):
    doctor_name = callback.data.split(":", 1)[1]
    now = datetime.now()
    hour = now.hour
    if 8 <= hour < 14:
        shift_type = "morning"
    elif 14 <= hour < 20:
        shift_type = "evening"
    else:
        await callback.answer(
            "Отмечать смену можно с 8 до 20", show_alert=True
        )
        return

    worker = await rq.get_worker_by_chat_id(callback.from_user.id)
    if not worker:
        await callback.answer("Вы не зарегистрированы", show_alert=True)
        return

    date_str = now.strftime("%d.%m.%Y")
    success = await rq.add_shift(worker.id, doctor_name, shift_type, date_str)
    if success:
        await callback.message.edit_text(
            f"Смена {shift_type} для {doctor_name} отмечена"
        )
    else:
        await callback.message.edit_text("Смена уже была отмечена")
    await callback.answer()
