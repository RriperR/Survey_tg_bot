import os
from datetime import datetime

import gspread

from aiogram.filters.callback_data import CallbackData

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from oauth2client.service_account import ServiceAccountCredentials

from database.models import async_session, Worker, Pair, Survey
from database.requests import (
    get_all_answers,
    clear_shifts,
    bulk_insert_shifts, get_all_shifts,
)


# Авторизация Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("../q-bot-key2.json", scope)
client = gspread.authorize(creds)

spreadsheet = client.open(os.environ.get("TABLE"))


async def update_workers_from_sheet() -> None:
    async with async_session() as session:
        # Загружаем всех сотрудников из БД
        existing_workers = {
            worker.full_name: worker
            async for worker in await session.stream_scalars(select(Worker))
        }

        worksheet1 = spreadsheet.get_worksheet(0)
        rows1 = worksheet1.get_all_values()[1:]  # пропускаем заголовок
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
        worksheet2 = spreadsheet.get_worksheet(1)
        rows2 = worksheet2.get_all_values()[1:]

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
    async with async_session() as session:
        await clear_table(session, Survey)

        worksheet3 = spreadsheet.get_worksheet(2)
        rows3 = worksheet3.get_all_values()[1:]  # Пропускаем заголовок

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
    worksheet = spreadsheet.get_worksheet(3)
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

    await clear_shifts()
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


async def clear_table(session: AsyncSession, model) -> None:
    await session.execute(delete(model))
    await session.commit()


async def export_answers_to_google_sheet() -> None:
    # Получаем все записи из таблицы Answer
    answers = await get_all_answers()

    worksheet4 = spreadsheet.get_worksheet(4)

    # Очищаем гугл таблицу
    worksheet4.clear()

    # Заголовки, исключая 'id' и 'subject'
    headers = [
        "object", "survey", "survey_date", "completed_at",
        "question1", "answer1",
        "question2", "answer2",
        "question3", "answer3",
        "question4", "answer4",
        "question5", "answer5"
    ]
    worksheet4.append_row(headers)

    # Заполняем таблицу строками из БД
    for ans in answers:
        row = [
            ans.object, ans.survey, ans.survey_date, ans.completed_at,
            ans.question1, ans.answer1,
            ans.question2, ans.answer2,
            ans.question3, ans.answer3,
            ans.question4, ans.answer4,
            ans.question5, ans.answer5
        ]
        worksheet4.append_row([str(cell) if cell is not None else "" for cell in row])


async def export_shifts_to_google_sheet() -> None:
    # Получаем все смены из БД
    shifts = await get_all_shifts()  # функция аналогичная get_all_answers()

    worksheet5 = spreadsheet.get_worksheet(5)  # например, 5-й лист (индекс 4)

    # Очищаем таблицу
    worksheet5.clear()

    # Заголовки
    headers = [
        "assistant_id", "assistant_name",
        "doctor_name", "date", "type", "manual"
    ]
    worksheet5.append_row(headers)

    # Заполняем данными
    for shift in shifts:
        row = [
            shift.assistant_id,
            shift.assistant_name or "",
            shift.doctor_name,
            shift.date,
            shift.type,
            "Да" if shift.manual else "Нет"
        ]
        worksheet5.append_row([str(cell) if cell is not None else "" for cell in row])


class SelectDoctor(CallbackData, prefix="msd"):
    doctor_id: int

class DoctorsPage(CallbackData, prefix="dpg"):
    page: int