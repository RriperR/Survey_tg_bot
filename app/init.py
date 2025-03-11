import os

import telebot
import gspread

from telebot import apihelper
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv


# Настройка авторизации Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name("../q-bot-key2.json", scope)
client = gspread.authorize(creds)

# Открываем таблицы по имени
spreadsheet = client.open(os.environ.get('TABLE'))
worksheet = spreadsheet.sheet1
second_spreadsheet = client.open(os.environ.get('ANSWERS_TABLE'))
second_worksheet = second_spreadsheet.sheet1

# Получение переменных окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.environ.get('BOT_TOKEN')
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')

# Инициализируем бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
apihelper.RETRY_ON_ERROR = True

# Глобальные переменные и словари
cached_employees = {}        # { 'ФИО': {'file_id': '...', 'chat_id': '...', 'spec': '...'} }
cached_assignments = []      # [{'subj': '...', 'obj': '...', 'questionary': '...', 'date': '...'}, ...]
cached_questionnaires = {}   # {'Название опросника': [(вопрос1, тип1), (вопрос2, тип2), ...]}
user_data = {}               # Состояния пользователей (очередь опросов, текущие опросы)

# Получаем данные из первой таблицы
names = worksheet.col_values(1)[1:]     # ФИО из первого столбца, пропускаем заголовок
chat_ids = worksheet.col_values(3)[1:]  # chat_id из третьего столбца, пропускаем заголовок


def update_local_cache():
    """
    Загружает/обновляет данные из Google Sheets в локальные переменные (или БД),
    чтобы снизить кол-во обращений к API Google.
    """
    global cached_employees, cached_assignments, cached_questionnaires

    # Перед перезаписью чистим текущие данные
    cached_employees.clear()
    cached_assignments.clear()
    cached_questionnaires.clear()


    # ================== Загрузка данных из 1-й вкладки: Список сотрудников ==================
    worksheet1 = spreadsheet.get_worksheet(0)                # 0 - первая вкладка
    all_rows_1 = worksheet1.get_all_values()[1:]             # Пропускаем заголовок
    for row in all_rows_1:
        fio = row[0].strip()
        file_id = row[1].strip()
        chat_id = row[2].strip()
        spec = row[3].strip() if len(row) > 3 else ""

        cached_employees[fio] = {
            'file_id': file_id,
            'chat_id': chat_id,
            'spec': spec
        }


    # ================== Загрузка данных из 2-й вкладки: Назначения опросов ==================
    worksheet2 = spreadsheet.get_worksheet(1)                # 1 - вторая вкладка
    all_rows_2 = worksheet2.get_all_values()[1:]             # Пропускаем заголовок
    for row in all_rows_2:
        subj = row[0].strip()
        obj = row[1].strip()
        questionary = row[2].strip()
        day_of_week = row[3].strip()
        date_str = row[4].strip()

        cached_assignments.append({
            'subj': subj,
            'obj': obj,
            'questionary': questionary,
            'day_of_week': day_of_week,
            'date': date_str
        })


    # ================== Загрузка данных из 3-й вкладки: Вопросы по опросникам ===============
    worksheet3 = spreadsheet.get_worksheet(2)                # 2 - третья вкладка
    all_rows_3 = worksheet3.get_all_values()[1:]             # Пропускаем заголовок
    # Форматируем в виде: cached_questionnaires['Название опросника'] = [(вопрос, тип), ...]
    for row in all_rows_3:
        questionary_name = row[0].strip()
        if questionary_name not in cached_questionnaires:
            cached_questionnaires[questionary_name] = []

        i = 1
        while i < len(row):
            question_text = row[i].strip()
            question_type = ""
            if i + 1 < len(row):
                question_type = row[i+1].strip()
            cached_questionnaires[questionary_name].append((question_text, question_type))
            i += 2

