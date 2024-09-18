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

@bot.message_handler(commands=['start'])
def start(message):
    # Получаем список ФИО из первого столбца
    names = worksheet.col_values(1)[1:]  # Пропускаем заголовок

    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for name in names:
        markup.add(name)

    bot.send_message(message.chat.id, "Выберите ФИО:", reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_name_selection(message):
    chat_id = message.chat.id
    selected_name = message.text

    # Добавляем id чата в другой столбец
    cell = worksheet.find(selected_name)
    worksheet.update_cell(cell.row, cell.col + 2, chat_id)  # Записываем в соседний столбец

    bot.send_message(message.chat.id, f"Вы выбрали: {selected_name}.\nChat ID {chat_id} добавлен в таблицу.")

if __name__ == '__main__':
    bot.polling(none_stop=True)

# from config import host, user, password, db_name, bot_token
#
# bot = telebot.TeleBot(bot_token)
#
# user_info = {'fullname':'', 'phone' : '', 'username' : '', 'photo' : ''}
#
#
#
# # try:
# #     connection = pymysql.connect(
# #                 host=h ost,
# #                 port=3306,
# #                 user=user,
# #                 password=password,
# #                 database=db_name,
# #                 cursorclass=pymysql.cursors.DictCursor
# #     )
# #     print('connection success')
# #
# #     try:
# #         # with connection.cursor() as cursor:
# #         #     cursor.execute('CREATE TABLE `respondents` (id serial PRIMARY KEY, fullname varchar(128), phone_number varchar(32), tg_username varchar(32), photo varchar(32))')
# #         #     print('successfully created table')
# #         pass
# #     finally:
# #         connection.close()
# #         print('closed')
# #
# # except Exception as ex:
# #     print('Connection error')
# #     print(ex)
#
#
# def log_user(message):
#     try:
#         connection = pymysql.connect(
#             host=host,
#             port=3306,
#             user=user,
#             password=password,
#             database=db_name,
#             cursorclass=pymysql.cursors.DictCursor
#         )
#
#         with connection.cursor() as cursor:
#             cursor.execute("SELECT * FROM respondents WHERE fullname = %s", (user_info['fullname'],))
#             result = cursor.fetchone()
#
#             if result:
#                 return
#             try:
#                 sql = "INSERT INTO respondents (fullname) VALUES (%s)"
#                 cursor.execute(sql, user_info['fullname'])
#                 connection.commit()
#                 bot.send_message(message.chat.id, 'Данные успешно добавлены!')
#             except Exception as ex:
#                 bot.send_message(message.chat.id, "Что-то пошло не так")
#                 bot.send_message(message.chat.id, f"Error while logging action: {ex}")
#
#     except Exception as ex:
#         bot.send_message(message.chat.id, f"Error while logging action: {ex}")
#
#     finally:
#         connection.close()
#
#
# def registration(message):
#     mesg = bot.send_message(message.chat.id, 'Введите своё ФИО: (Магомедов Магомед Магомедович)')
#     bot.register_next_step_handler(mesg, fullname_input)
#
# def fullname_input(message):
#     user_info['fullname'] = message.text
#     log_user(message)
#
#
# @bot.message_handler(commands=['start'])
# def start(message):
#     bot.send_message(message.chat.id, 'Бот для проведения опросов')
#     registration(message)
#
#
# bot.polling(non_stop=True)