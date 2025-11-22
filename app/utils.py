import os
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

from aiogram.filters.callback_data import CallbackData
from sqlalchemy import delete, select

from database.models import async_session, Worker, Pair, Survey
from database.requests import (
    get_all_answers,
    clear_table,
    bulk_insert_shifts, get_all_shifts, get_shifts_by_date,
)


# Авторизация Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("../q-bot-key2.json", scope)
client = gspread.authorize(creds)

spreadsheet = client.open(os.environ.get("TABLE"))
answers_spreadsheet = client.open(os.environ.get("ANSWERS_TABLE"))

WORKERS_SHEET_NAME = os.getenv("WORKERS_SHEET_NAME", "Список сотрудников")
PAIRS_SHEET_NAME = os.getenv("PAIRS_SHEET_NAME", "Пары сотрудников")
SURVEYS_SHEET_NAME = os.getenv("SURVEYS_SHEET_NAME", "Опросы")
SHIFTS_SOURCE_SHEET_NAME = os.getenv("SHIFTS_SOURCE_SHEET_NAME", "Расписание смен")
SHIFT_REPORT_SHEET_NAME = os.getenv("SHIFT_REPORT_SHEET_NAME", "Отчёт по сменам")
ANSWERS_SHEET_NAME = os.getenv("ANSWERS_SHEET_NAME", "Ответы")


async def update_workers_from_sheet() -> None:
    async with async_session() as session:
        # Загружаем всех сотрудников из БД
        existing_workers = {
            worker.full_name: worker
            async for worker in await session.stream_scalars(select(Worker))
        }

        worksheet = spreadsheet.worksheet(WORKERS_SHEET_NAME)
        rows1 = worksheet.get_all_values()[1:]  # пропускаем заголовок
        created = 0

        for row in rows1:
            full_name = row[0].strip()
            file_id = row[1].strip() if len(row) > 1 else ""
            chat_id = row[2].strip() if len(row) > 2 else ""
            speciality = row[3].strip() if len(row) > 3 else ""
            phone = row[4].strip() if len(row) > 4 else ""

            if not full_name:
                continue

            existing = existing_workers.get(full_name)

            if existing:
                # Обновляем chat_id, если он есть в таблице и отсутствует в БД
                if chat_id and not existing.chat_id:
                    existing.chat_id = chat_id
                # Обновляем file_id, если он есть в таблице и отсутствует в БД
                if file_id and not existing.file_id:
                    existing.file_id = file_id

            else:
                # Новый сотрудник
                worker = Worker(
                    full_name=full_name,
                    file_id=file_id,
                    chat_id=chat_id,
                    speciality=speciality,
                    phone=phone,
                )
                session.add(worker)
                created += 1

        await session.commit()
        print(f"✅ Загружено новых: {created}")


async def update_pairs_from_sheet() -> None:
    today_str = datetime.now().strftime("%d.%m.%Y")

    async with async_session() as session:
        worksheet = spreadsheet.worksheet(PAIRS_SHEET_NAME)
        rows2 = worksheet.get_all_values()[1:]

        for row in rows2:
            if len(row) >= 5 and row[4].strip() == today_str:
                pair = Pair(
                    subject=row[0].strip(),
                    object=row[1].strip(),
                    survey=row[2].strip(),
                    weekday=row[3].strip(),
                    date=row[4].strip(),
                )
                session.add(pair)

        await session.commit()
        print("✅ Данные о парах успешно загружены в базу данных.")


async def update_surveys_from_sheet() -> None:
    await clear_table(Survey)
    async with async_session() as session:

        worksheet = spreadsheet.worksheet(SURVEYS_SHEET_NAME)
        rows3 = worksheet.get_all_values()[1:]  # Пропускаем заголовок

        for row in rows3:
            id_value = row[0].strip()
            if not id_value.isdigit():
                print(f"⛔ Пропущена строка с некорректным ID: {row}")
                continue

            survey = Survey(
                id=int(id_value),
                speciality=row[1].strip(),
                question1=row[2].strip(),
                question1_type=row[3].strip(),
                question2=row[4].strip(),
                question2_type=row[5].strip(),
                question3=row[6].strip(),
                question3_type=row[7].strip(),
                question4=row[8].strip(),
                question4_type=row[9].strip(),
                question5=row[10].strip(),
                question5_type=row[11].strip(),
            )
            session.add(survey)

        await session.commit()
        print("✅ Данные об опросах успешно загружены в базу данных.")


async def update_shifts_from_sheet() -> None:
    worksheet = spreadsheet.worksheet(SHIFTS_SOURCE_SHEET_NAME)
    rows = worksheet.get_all_values()[1:]
    schedule: list[tuple[str, str, str]] = []
    for row in rows:
        if len(row) < 3:
            continue
        doctor_name = row[0].strip()
        date = row[1].strip()
        shift_type = row[2].strip()
        if not doctor_name or not date or not shift_type:
            continue
        schedule.append((doctor_name, date, shift_type))

    if schedule:
        await bulk_insert_shifts(schedule)
    print("✅ Данные о сменах успешно загружены в базу данных.")


async def update_data_from_sheets() -> None:
    """
    Загружает данные из Google Sheets и сохраняет в PostgreSQL
    """
    await update_workers_from_sheet()
    await update_pairs_from_sheet()
    await update_surveys_from_sheet()
    await update_shifts_from_sheet()
    print("✅ Данные из Google Sheets успешно загружены в базу данных.")


async def export_answers_to_google_sheet() -> None:
    # Получаем все записи из таблицы Answer
    answers = await get_all_answers()

    worksheet = answers_spreadsheet.worksheet(ANSWERS_SHEET_NAME)

    # Поля, которые берём из модели (в нужном порядке)
    fields = [
        "object", "subject", "survey", "survey_date", "completed_at",
        "question1", "answer1",
        "question2", "answer2",
        "question3", "answer3",
        "question4", "answer4",
        "question5", "answer5",
    ]

    # Очищаем лист
    worksheet.clear()

    # Пишем заголовки
    worksheet.append_row(fields)

    # Готовим данные пачкой
    values = []
    for ans in answers:
        row = [getattr(ans, f, "") for f in fields]
        # приведение к строке и None -> ""
        row = ["" if cell is None else str(cell) for cell in row]
        values.append(row)

    # Одной операцией заливаем все строки (если они есть)
    if values:
        worksheet.append_rows(values, value_input_option="RAW")


async def export_shifts_to_google_sheet() -> None:
    # Берём только смены за сегодня
    today_str = datetime.now().strftime("%d.%m.%Y")
    shifts = await get_shifts_by_date(today_str)

    worksheet = answers_spreadsheet.worksheet(SHIFT_REPORT_SHEET_NAME)

    # Поля, которые выгружаем (и порядок колонок)
    headers = [
        "assistant_id",
        "assistant_name",
        "doctor_name",
        "date",
        "type",
        "manual",
    ]

    # Смотрим, есть ли что-то в листе
    existing_values = worksheet.get_all_values()
    if not existing_values:
        # Лист пустой — пишем заголовки
        worksheet.append_row(headers)

    # Готовим данные
    values = []
    for shift in shifts:
        row = [
            shift.assistant_id,
            shift.assistant_name or "",
            shift.doctor_name,
            shift.date,
            shift.type,
            "Да" if shift.manual else "Нет",
        ]
        row = ["" if v is None else str(v) for v in row]
        values.append(row)

    if values:
        worksheet.append_rows(values, value_input_option="RAW")


class SelectDoctor(CallbackData, prefix="msd"):
    doctor_id: int


class DoctorsPage(CallbackData, prefix="dpg"):
    page: int
