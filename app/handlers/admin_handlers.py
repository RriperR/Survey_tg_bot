from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from utils import update_data_from_sheets, export_answers_to_google_sheet


router = Router()


@router.message(Command('upd'))
async def update_db(message: Message):
    msg = await message.answer('⏳ Загрузка...')
    await update_data_from_sheets()
    await msg.edit_text('✅ Данные из Google Sheets успешно загружены в базу данных.')


@router.message(Command('export'))
async def export_data(message: Message):
    msg = await message.answer('⏳ Выгрузка...')
    await export_answers_to_google_sheet()
    await msg.edit_text('✅ Ответы успешно перенесены в Google Sheets.')
