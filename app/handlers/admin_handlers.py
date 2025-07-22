from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from utils import (
    update_data_from_sheets,
    update_surveys_from_sheet,
    update_pairs_from_sheet,
    update_workers_from_sheet,
    update_shifts_from_sheet,
    export_answers_to_google_sheet,
)

router = Router()


@router.message(Command('upd'))
async def update_db(message: Message):
    msg = await message.answer('⏳ Загрузка...')
    await update_data_from_sheets()
    await msg.edit_text('✅ Данные из Google Sheets успешно загружены в базу данных.')


@router.message(Command('upd_workers'))
async def update_workers(message: Message):
    msg = await message.answer('⏳ Загрузка...')
    await update_workers_from_sheet()
    await msg.edit_text("✅ Данные о сотрудниках успешно загружены в базу данных.")


@router.message(Command('upd_pairs'))
async def update_pairs(message: Message):
    msg = await message.answer('⏳ Загрузка...')
    await update_pairs_from_sheet()
    await msg.edit_text("✅ Данные о парах успешно загружены в базу данных.")


@router.message(Command('upd_surveys'))
async def update_surveys(message: Message):
    msg = await message.answer('⏳ Загрузка...')
    await update_surveys_from_sheet()
    await msg.edit_text("✅ Данные об опросах успешно загружены в базу данных.")


@router.message(Command('upd_shifts'))
async def update_shifts(message: Message):
    msg = await message.answer('⏳ Загрузка...')
    await update_shifts_from_sheet()
    await msg.edit_text("✅ Данные о сменах успешно загружены в базу данных.")


@router.message(Command('export'))
async def export_data(message: Message):
    msg = await message.answer('⏳ Выгрузка...')
    await export_answers_to_google_sheet()
    await msg.edit_text('✅ Ответы успешно перенесены в Google Sheets.')