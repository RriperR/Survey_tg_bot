import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import schedule
import time
import subprocess
import datetime

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
user_names = {}


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
    user_names[chat_id] = selected_name

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
        # Если пользователь подтвердил выбор, проверяем, зарегистрирован ли уже этот chat_id
        chat_ids = worksheet.col_values(3)[1:]  # Предполагаем, что chat_id находится в 3 столбце, пропускаем заголовок

        # Проверка, есть ли chat_id в столбце
        if str(chat_id) in chat_ids:
            # Если chat_id найден, ищем соответствующее имя (в этом же ряду)
            row_index = chat_ids.index(str(chat_id)) + 2  # +2 потому что индекс с 0 и пропускаем заголовок
            registered_name = worksheet.cell(row_index, 1).value  # Предполагаем, что ФИО находится в 1 столбце

            bot.send_message(chat_id, f"Вы уже зарегистрировались как {registered_name}.")
        else:
            # Если chat_id не найден, добавляем его в таблицу
            selected_name = user_names.get(chat_id).strip()  # Убираем лишние пробелы

            # Получаем все имена из первого столбца
            names_in_sheet = worksheet.col_values(1)[1:]  # Пропускаем заголовок

            # Ищем строку с именем, игнорируя пробелы
            found_row = None
            for index, name in enumerate(names_in_sheet):
                if name.strip() == selected_name:  # Сравниваем имена без пробелов
                    found_row = index + 2  # +2, потому что пропускаем заголовок

            if found_row:
                worksheet.update_cell(found_row, 3, chat_id)  # Записываем chat_id в 3 столбец
                bot.send_message(chat_id, f"Вы успешно зарегистрировались как {selected_name}.")
            else:
                bot.send_message(chat_id, "Произошла ошибка: не удалось найти ваше имя в таблице.")
    elif call.data == "confirm_no":
        # Если пользователь отменил выбор, предлагаем выбрать снова
        bot.send_message(chat_id, "Пожалуйста, выберите ФИО снова с помощью меню /start")
        del user_names[chat_id]  # Очищаем сохраненное имя для пользователя


# Функция для запуска sender.py
def run_sender():
    try:
        print("Запускаем файл sender.py")
        subprocess.run(['python', 'sender.py'])
        print("Рассылка завершена успешно!")
    except Exception as e:
        print(f"Ошибка при запуске рассылки: {e}")

schedule.every().day.at("19:45").do(run_sender)

# Асинхронный запуск планировщика
def scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # Запускаем планировщик в отдельном потоке
    import threading
    scheduler_thread = threading.Thread(target=scheduler)
    scheduler_thread.start()

# Запуск бота
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