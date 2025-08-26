from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

import database.requests as rq
from keyboards import (
    build_shift_keyboard,
    build_all_doctors_keyboard,
    build_cancel_shift_keyboard,
)
from logger import setup_logger

from utils import DoctorsPage, SelectDoctor

router = Router()

logger = setup_logger("shift", "shift.log")


def get_shift_type(hour):
    if 8 <= hour < 14:
        return "morning"
    elif 14 <= hour < 20:
        return "evening"
    return None


@router.message(Command("shift"))
async def show_doctors(message: Message):
    now = datetime.now()
    shift_type = get_shift_type(now.hour)
    if not shift_type:
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

    free_shifts = await rq.get_free_doctors(date_str, shift_type)
    if not free_shifts:
        await message.answer("Список смен пуст")
        return
    await message.answer(
        "Выберите смену:",
        reply_markup=await build_shift_keyboard(free_shifts)
    )


@router.callback_query(F.data.startswith("select_shift:"))
async def mark_shift(callback: CallbackQuery):
    shift_id = int(callback.data.split(":", 1)[1])
    now = datetime.now()
    shift_type = get_shift_type(now.hour)
    if not shift_type:
        await callback.answer(
            "Отмечать смену можно с 8 до 20", show_alert=True
        )
        return

    worker = await rq.get_worker_by_chat_id(callback.from_user.id)
    if not worker:
        await callback.answer("Вы не зарегистрированы", show_alert=True)
        return

    date_str = now.strftime("%d.%m.%Y")
    shift = await rq.get_shift_by_id(shift_id)
    if not shift or shift.date != date_str or shift.type != shift_type:
        await callback.answer("Слот недоступен", show_alert=True)
        return

    success = await rq.add_shift_by_id(
        worker.id,
        worker.full_name,
        shift_id,
    )
    if success:
        await callback.message.edit_text(
            f"✅ Смена {shift_type} с {shift.doctor_name} отмечена"
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
    now = datetime.now()
    shift_type = get_shift_type(now.hour)
    if not shift_type:
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
    shift_type = get_shift_type(now.hour)
    if not shift_type:
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
