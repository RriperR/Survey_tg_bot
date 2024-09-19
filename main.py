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

# Глобальная переменная для хранения выбранного имени
user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Загрузка данных...")

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

    # Сохраняем выбранное имя в глобальной переменной для пользователя
    user_data[chat_id] = selected_name

    # Создаем клавиатуру для подтверждения выбора
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="Да", callback_data="confirm_yes"))
    markup.add(types.InlineKeyboardButton(text="Нет", callback_data="confirm_no"))

    bot.send_message(chat_id, f"Вы выбрали {selected_name}. Всё верно?", reply_markup=markup)

# Обработка нажатия на кнопку подтверждения
@bot.callback_query_handler(func=lambda call: True)
def handle_confirmation(call):
    chat_id = call.message.chat.id
    if call.data == "confirm_yes":
        # Если пользователь подтвердил выбор, добавляем chat_id в таблицу
        selected_name = user_data.get(chat_id)
        cell = worksheet.find(selected_name)
        worksheet.update_cell(cell.row, cell.col + 2, chat_id)  # Записываем в соседний столбец

        bot.send_message(chat_id, f"Вы успешно зарегистрировались как {selected_name}.")
    elif call.data == "confirm_no":
        # Если пользователь отменил выбор, предлагаем выбрать снова
        bot.send_message(chat_id, "Пожалуйста, выберите ФИО снова с помощью меню /start")
        del user_data[chat_id]  # Очищаем сохраненное имя для пользователя

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
#             try:
#     finally:
#         connection.close()
#