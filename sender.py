import telebot
import pandas as pd
from telebot import types
import pymysql
import datetime
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Настройка авторизации Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name('q-bot-435919-f9cd6316f9b0.json', scope)
client = gspread.authorize(creds)

# Открываем таблицу по имени
spreadsheet = client.open("Сотрудник 2.0 Таблица")
worksheet = spreadsheet.sheet1

# Замените YOUR_TELEGRAM_BOT_TOKEN на ваш токен
bot = telebot.TeleBot("7402075843:AAGrh9drV5TvHCR0T9qeFR932MHAbgbSyg0")

# Получаем ФИО из первого столбца и chat_id из третьего
names = worksheet.col_values(1)[1:]  # Пропускаем заголовок
chat_ids = worksheet.col_values(3)[1:]  # Пропускаем заголовок

# Создаем словарь
fio_chatid_dict = {name: chat_id for name, chat_id in zip(names, chat_ids) if chat_id}

# Выводим словарь
print(fio_chatid_dict)

# Открываем второй лист
worksheet2 = spreadsheet.get_worksheet(1)  # Открываем второй лист

# Получаем все строки второго листа
rows = worksheet2.get_all_values()[1:]  # Пропускаем заголовок

# Проходим по каждой строке
for row in rows:
    fio = row[0].strip()  # Берем ФИО из первого столбца
    text_part1 = row[1]   # Текст из второго столбца
    text_part2 = row[2]   # Текст из третьего столбца

    # Проверяем, есть ли chat_id для данного ФИО в словаре
    chat_id = fio_chatid_dict.get(fio)

    if chat_id:
        try:
            # Отправляем сообщение
            message = f"На этой неделе с вами работал(-а): {text_part1}. Пожалуйста, пройдите опрос: {text_part2}"
            bot.send_message(chat_id, message)
            print(f"Сообщение отправлено пользователю {fio} (chat_id: {chat_id})")
        except Exception as e:
            print(f"Не удалось отправить сообщение для {fio}. Ошибка: {e}")
    else:
        print(f"Чат ID для {fio} не найден")








def send_q(questionary):
    # Открываем 3 лист
    worksheet3 = spreadsheet.get_worksheet(2)  # Открываем второй лист

    # Получаем все строки 3 листа
    rows = worksheet3.get_all_values()[1:]  # Пропускаем заголовок

    for row in rows:
        if row[0] == questionary:
            pass