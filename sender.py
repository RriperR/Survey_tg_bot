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


def send_q(questionary, chat_id):
    # Открываем 3 лист
    worksheet3 = spreadsheet.get_worksheet(2)  # Открываем второй лист

    # Получаем все строки 3 листа
    rows = worksheet3.get_all_values()[1:]  # Пропускаем заголовок

    for row in rows:
        if row[0] == questionary:
            for i in range(1, len(row) - 1):
                if row[i + 1] == 'int':
                    # Создаем клавиатуру для оценки
                    markup = types.InlineKeyboardMarkup()
                    markup.row(
                        types.InlineKeyboardButton(text="1", callback_data="1"),
                        types.InlineKeyboardButton(text="2", callback_data="2"),
                        types.InlineKeyboardButton(text="3", callback_data="3"),
                        types.InlineKeyboardButton(text="4", callback_data="4"),
                        types.InlineKeyboardButton(text="5", callback_data="5")
                    )

                    bot.send_message(chat_id, row[i], reply_markup=markup)

                if row[i + 1] == 'y/n':
                    # Создаем клавиатуру для оценки
                    markup = types.InlineKeyboardMarkup()
                    markup.add(types.InlineKeyboardButton(text="Да", callback_data="Y"))
                    markup.add(types.InlineKeyboardButton(text="Нет", callback_data="N"))

                    bot.send_message(chat_id, row[i], reply_markup=markup)

                if row[i + 1] == 'str':
                    mesg = bot.send_message(chat_id, row[i])
                    bot.register_next_step_handler(mesg, str_saver)


def str_saver(message):
    pass



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
            send_q(text_part2, chat_id)

            print(f"Сообщение отправлено пользователю {fio} (chat_id: {chat_id})")
        except Exception as e:
            print(f"Не удалось отправить сообщение для {fio}. Ошибка: {e}")
    else:
        print(f"Чат ID для {fio} не найден")

