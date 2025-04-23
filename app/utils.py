import os
import gspread
import subprocess

from datetime import datetime
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from oauth2client.service_account import ServiceAccountCredentials

from database.models import async_session, Worker, Pair, Survey


# Авторизация Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("../q-bot-key2.json", scope)
client = gspread.authorize(creds)

spreadsheet = client.open(os.environ.get("TABLE"))


async def update_workers_from_sheet():
    async with async_session() as session:
        #create_postgres_dump()
        #print("дамп бд перед очисткой")
        await clear_table(session, Worker)

        # Вкладка 0: Сотрудники
        worksheet1 = spreadsheet.get_worksheet(0)
        rows1 = worksheet1.get_all_values()[1:]  # пропускаем заголовок
        for row in rows1:
            worker = Worker(
                full_name=row[0].strip(),
                file_id=row[1].strip(),
                chat_id=row[2].strip(),
                speciality=row[3].strip(),
                phone=row[4].strip(),
            )
            session.add(worker)

        await session.commit()
        print("✅ Данные о работниках успешно загружены в базу данных.")


async def update_pairs_from_sheet():
    async with async_session() as session:

        # Вкладка 1: Назначения опросов
        worksheet2 = spreadsheet.get_worksheet(1)
        rows2 = worksheet2.get_all_values()[1:]
        for row in rows2:
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


async def update_surveys_from_sheet():
    async with async_session() as session:
        #create_postgres_dump()
        #print("дамп бд перед очисткой")
        await clear_table(session, Survey)

        # Вкладка 2: Опросники
        worksheet3 = spreadsheet.get_worksheet(2)
        rows3 = worksheet3.get_all_values()[1:]

        for row in rows3:
            survey = Survey(
                speciality=row[0].strip(),
                question1=row[1].strip(),
                question1_type=row[2].strip(),
                question2=row[3].strip(),
                question2_type=row[4].strip(),
                question3=row[5].strip(),
                question3_type=row[6].strip(),
                question4=row[7].strip(),
                question4_type=row[8].strip(),
                question5=row[9].strip(),
                question5_type=row[10].strip(),
            )
            session.add(survey)

        await session.commit()
        print("✅ Данные об опросах успешно загружены в базу данных.")


async def update_data_from_sheets():
    """
    Загружает данные из Google Sheets и сохраняет в PostgreSQL
    """
    await update_workers_from_sheet()
    await update_pairs_from_sheet()
    await update_surveys_from_sheet()
    print("✅ Данные из Google Sheets успешно загружены в базу данных.")


async def clear_table(session: AsyncSession, model):
    await session.execute(delete(model))
    await session.commit()


async def clear_all_tables(session: AsyncSession):
    """
    Удаляет старые записи из таблиц Worker, Pair, Survey
    """
    for model in (Worker, Pair, Survey):
        await session.execute(delete(model))
    await session.commit()


def create_postgres_dump():
    """
    Создаёт дамп PostgreSQL перед очисткой таблиц
    """
    print("начало работы create_postgres_dump")
    dump_dir = Path("db_backups")
    dump_dir.mkdir(exist_ok=True)
    print("директория создана")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dump_file = dump_dir / f"backup_{timestamp}.sql"
    print("создание команды")
    command = [
        "pg_dump",
        "-h", os.environ.get("DB_HOST", "localhost"),
        "-p", os.environ.get("DB_PORT", "5432"),
        "-U", os.environ["DB_USER"],
        "-d", os.environ["DB_NAME"],
        "-f", str(dump_file)
    ]

    env = os.environ.copy()
    # Убедись, что переменная окружения PGPASSWORD установлена
    if "DB_PASSWORD" in env:
        env["PGPASSWORD"] = env["DB_PASS"]

    try:
        subprocess.run(command, env=env, check=True)
        print(f"✅ Дамп базы сохранён в {dump_file}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка при создании дампа базы: {e}")


