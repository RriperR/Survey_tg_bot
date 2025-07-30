from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

import database.requests as rq
from keyboards import (
    build_doctors_keyboard,
    build_all_doctors_keyboard,
    build_cancel_shift_keyboard,
)
from logger import setup_logger

from utils import DoctorsPage, SelectDoctor

router = Router()

logger = setup_logger("shift", "shift.log")


@router.message(Command("shift"))
async def show_doctors(message: Message):
    now = datetime.now()
    hour = now.hour
    if 8 <= hour < 14:
        shift_type = "morning"
    elif 14 <= hour < 20:
        shift_type = "evening"
    else:
        await message.answer("Отмечаться можно с 8 до 20")
        return

    date_str = now.strftime("%d.%m.%Y")
    worker = await rq.get_worker_by_chat_id(message.from_user.id)
    if not worker:
        await message.answer("Вы не зарегистрированы")
        return

    current_shift = await rq.get_assistant_shift(worker.id, date_str, shift_type)
    if current_shift:
        await message.answer(
            f"Вы уже записаны к {current_shift.doctor_name}",
            reply_markup=build_cancel_shift_keyboard(shift_type),
        )
        return

    doctor_names = await rq.get_free_doctors(date_str, shift_type)
    if not doctor_names:
        await message.answer("Список врачей пуст")
        return
    await message.answer(
        "Выберите врача:",
        reply_markup=await build_doctors_keyboard(doctor_names)
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
    success = await rq.add_shift(
        worker.id,
        worker.full_name,
        doctor_name,
        shift_type,
        date_str,
    )
    if success:
        await callback.message.edit_text(
            f"✅ Смена {shift_type} с {doctor_name} отмечена"
        )
    else:
        await callback.message.edit_text(
            "❌ Вы уже записаны у другого врача или выбранный слот занят"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("cancel_shift:"))
async def cancel_shift(callback: CallbackQuery):
    shift_type = callback.data.split(":", 1)[1]
    now = datetime.now()
    date_str = now.strftime("%d.%m.%Y")
    worker = await rq.get_worker_by_chat_id(callback.from_user.id)
    if worker:
        await rq.remove_shift(worker.id, date_str, shift_type)
        await callback.message.edit_text("✅ Запись отменена")
    await callback.answer()


@router.message(Command("shift_any"))
async def manual_shift(message: Message):
    from datetime import datetime
    now = datetime.now()
    hour = now.hour
    if 8 <= hour < 14:
        shift_type = "morning"
    elif 14 <= hour < 20:
        shift_type = "evening"
    else:
        await message.answer("Отмечаться можно с 8 до 20")
        return

    date_str = now.strftime("%d.%m.%Y")

    worker = await rq.get_worker_by_chat_id(message.from_user.id)
    if not worker:
        await message.answer("Вы не зарегистрированы")
        return

    current_shift = await rq.get_assistant_shift(worker.id, date_str, shift_type)
    if current_shift:
        await message.answer(
            f"Вы уже записаны к {current_shift.doctor_name}",
            reply_markup=build_cancel_shift_keyboard(shift_type),
        )
        return

    await message.answer(
        "Выберите врача:",
        reply_markup=await build_all_doctors_keyboard(page=0),
    )

# --- Хендлеры пагинации и выбора врача ---
@router.callback_query(DoctorsPage.filter())
async def doctors_paginate(cb: CallbackQuery, callback_data: DoctorsPage):
    await cb.message.edit_reply_markup(
        reply_markup=await build_all_doctors_keyboard(page=callback_data.page)
    )
    await cb.answer()


@router.callback_query(SelectDoctor.filter())
async def doctor_selected(cb: CallbackQuery, callback_data: SelectDoctor):
    now = datetime.now()
    hour = now.hour
    if 8 <= hour < 14:
        shift_type = "morning"
    elif 14 <= hour < 20:
        shift_type = "evening"
    else:
        await cb.answer("Отмечать смену можно с 8 до 20", show_alert=True)
        return

    worker = await rq.get_worker_by_chat_id(cb.from_user.id)
    if not worker:
        await cb.answer("Вы не зарегистрированы", show_alert=True)
        return

    date_str = now.strftime("%d.%m.%Y")
    doctor = await rq.get_worker_by_id(callback_data.doctor_id)
    if not doctor:
        await cb.answer("Врач не найден", show_alert=True)
        return

    success = await rq.add_manual_shift(
        worker.id,
        worker.full_name,
        doctor.full_name,  # фиксируем имя из БД
        shift_type,
        date_str,
    )

    if success:
        await cb.message.edit_text(f"✅ Смена {shift_type} с {doctor.full_name} отмечена (вручную)")
    else:
        await cb.message.edit_text("❌ Вы уже записаны на эту смену")
    await cb.answer()