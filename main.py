import telebot
import pandas as pd
from telebot import types
import pymysql
import datetime
import os

from config import host, user, password, db_name, bot_token

bot = telebot.TeleBot(bot_token)

user_info = {'fullname':'', 'phone' : '', 'username' : '', 'photo' : ''}



# try:
#     connection = pymysql.connect(
#                 host=h ost,
#                 port=3306,
#                 user=user,
#                 password=password,
#                 database=db_name,
#                 cursorclass=pymysql.cursors.DictCursor
#     )
#     print('connection success')
#
#     try:
#         # with connection.cursor() as cursor:
#         #     cursor.execute('CREATE TABLE `respondents` (id serial PRIMARY KEY, fullname varchar(128), phone_number varchar(32), tg_username varchar(32), photo varchar(32))')
#         #     print('successfully created table')
#         pass
#     finally:
#         connection.close()
#         print('closed')
#
# except Exception as ex:
#     print('Connection error')
#     print(ex)


def log_user(message):
    try:
        connection = pymysql.connect(
            host=host,
            port=3306,
            user=user,
            password=password,
            database=db_name,
            cursorclass=pymysql.cursors.DictCursor
        )

        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM respondents WHERE fullname = %s", (user_info['fullname'],))
            result = cursor.fetchone()

            if result:
                return
            try:
                sql = "INSERT INTO respondents (fullname) VALUES (%s)"
                cursor.execute(sql, user_info['fullname'])
                connection.commit()
                bot.send_message(message.chat.id, 'Данные успешно добавлены!')
            except Exception as ex:
                bot.send_message(message.chat.id, "Что-то пошло не так")
                bot.send_message(message.chat.id, f"Error while logging action: {ex}")

    except Exception as ex:
        bot.send_message(message.chat.id, f"Error while logging action: {ex}")

    finally:
        connection.close()


def registration(message):
    mesg = bot.send_message(message.chat.id, 'Введите своё ФИО: (Магомедов Магомед Магомедович)')
    bot.register_next_step_handler(mesg, fullname_input)

def fullname_input(message):
    user_info['fullname'] = message.text
    log_user(message)


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Бот для проведения опросов')
    registration(message)


bot.polling(non_stop=True)