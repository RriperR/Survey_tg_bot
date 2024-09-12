import csv
import telebot
import pandas as pd
from telebot import types
import pymysql
import datetime
import os

from config import host, user, password, db_name

bot = telebot.TeleBot('7402075843:AAGrh9drV5TvHCR0T9qeFR932MHAbgbSyg0')

try:
    connection = pymysql.connect(
                host=host,
                port=3306,
                user=user,
                password=password,
                database=db_name,
                cursorclass=pymysql.cursors.DictCursor
    )
    print('connection success')

    try:
        # with connection.cursor() as cursor:
        #     cursor.execute('CREATE TABLE `respondents` (id serial PRIMARY KEY, fullname varchar(128), phone_number varchar(32), tg_username varchar(32), photo varchar(32))')
        #     print('successfully created table')
        pass
    finally:
        connection.close()
        print('closed')

except Exception as ex:
    print('Connection error')
    print(ex)