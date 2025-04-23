from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery

from utils import update_data_from_sheets
import database.requests as rq
import keyboards as kb


router = Router()


@router.message(CommandStart())
async def start(message: Message):
    await message.answer("Hey!")
    await message.answer('Выберите своё ФИО, чтобы зарегистрироваться', reply_markup=await kb.build_worker_keyboard())


@router.message(Command('upd'))
async def get_chat_id(message: Message):
    await message.answer('Загрузка...')
    await update_data_from_sheets()
    await message.answer('✅ Данные из Google Sheets успешно загружены в базу данных.')



@router.callback_query(F.data.startswith("select_worker:"))
async def register_worker(callback: CallbackQuery):
    worker_id = int(callback.data.split(":", 1)[1])
    worker = await rq.get_worker_by_id(worker_id)

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
        await callback.message.edit_text(
            "⚠️ Вы уже зарегистрированы и не можете выбрать другое ФИО."
        )
        await callback.answer()
        return

    await callback.message.edit_text("🎉 Регистрация прошла успешно! Вы можете отправить своё фото в любое время,"
                                     " чтобы оно появлялось у других в опросах ")
    await callback.answer()


@router.callback_query(F.data == "confirm_no")
async def cancel_register(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите своё ФИО, чтобы зарегистрироваться:",
        reply_markup=await kb.build_worker_keyboard()
    )
    await callback.answer()


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
