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

# Открываем таблицу по имени
spreadsheet = client.open("Worker-2.0_Table")
worksheet = spreadsheet.sheet1

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
user_names = {}
user_data = {}
fio_chatid_dict = {}
questions = {}
stuff = {}

# Получаем данные из первой таблицы
names = worksheet.col_values(1)[1:]     # ФИО из первого столбца, пропускаем заголовок
chat_ids = worksheet.col_values(3)[1:]  # chat_id из третьего столбца, пропускаем заголовок

# Создаем словарь ФИО: chat_id
fio_chatid_dict = {name.strip(): chat_id for name, chat_id in zip(names, chat_ids) if chat_id}

# Создаем словарь ФИО: индекс строки в таблице
for index, name in enumerate(names, start=2):  # Индексация с 2, так как первая строка - заголовок
    stuff[name.strip()] = index
