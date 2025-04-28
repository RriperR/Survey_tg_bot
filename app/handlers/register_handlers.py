import logging

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery

import database.requests as rq
import keyboards as kb


router = Router()

logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start(message: Message):
    user = message.from_user
    logger.info(
        f"Пользователь (id={user.id}, username={user.username}) использовал '/start'"
    )
    await message.answer('Выберите своё ФИО, чтобы зарегистрироваться', reply_markup=await kb.build_worker_keyboard())


@router.callback_query(F.data.startswith("select_worker:"))
async def register_worker(callback: CallbackQuery):
    worker_id = int(callback.data.split(":", 1)[1])
    worker = await rq.get_worker_by_id(worker_id)

    logger.info(
        f"Пользователь (id={callback.from_user.id}) выбрал {worker.full_name}"
    )

    await callback.message.edit_text(
        f"Вы уверены, что хотите выбрать:\n<b>{worker.full_name}</b>?",
        reply_markup=await kb.build_confirm_keyboard(worker_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_yes:"))
async def confirm_register(callback: CallbackQuery):
    worker_id = int(callback.data.split(":", 1)[1])
    success = await rq.set_chat_id(worker_id, str(callback.from_user.id))

    if not success:
        worker = await rq.get_worker_by_chat_id(callback.from_user.id)
        await callback.message.edit_text(
            f"⚠️ Вы уже зарегистрированы как {worker.full_name}"
        )
        await callback.answer()
        logger.info(
            f"Пользователь (id={callback.from_user.id}) уже зарегистрирован"
        )
        return

    await callback.message.edit_text("🎉 Регистрация прошла успешно! Вы можете отправить своё фото в любое время,"
                                     " чтобы оно появлялось у других в опросах ")
    await callback.answer()

    logger.info(
        f"Пользователь (id={callback.from_user.id}) успешно зарегистрировался"
    )


@router.callback_query(F.data == "confirm_no")
async def cancel_register(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите своё ФИО, чтобы зарегистрироваться:",
        reply_markup=await kb.build_worker_keyboard()
    )
    await callback.answer()

    logger.info(
        f"Пользователь (id={callback.from_user.id} отменил выбор ФИО"
    )


@router.message(F.photo)
async def handle_worker_photo(message: Message):
    # Получаем последний (самый качественный) вариант фото
    photo = message.photo[-1]
    file_id = photo.file_id

    # Получаем worker по chat_id
    worker = await rq.get_worker_by_chat_id(message.from_user.id)

    if not worker:
        await message.answer("❗️ Вы ещё не зарегистрированы. Пожалуйста, сначала подтвердите свою личность.")
        return

    # Сохраняем file_id в БД
    try:
        await rq.set_worker_file_id(worker.id, file_id)
        await message.answer("✅ Фото получено и сохранено. Спасибо!")

    except:
        await message.answer("❗️ Что-то пошло не так")
