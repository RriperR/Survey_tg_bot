import telebot
from telebot import types
import pymysql
import datetime
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


stuff = {}
user_data = {}
questions = {}



# Получаем ФИО из первого столбца и chat_id из третьего
names = worksheet.col_values(1)[1:]  # Пропускаем заголовок
chat_ids = worksheet.col_values(3)[1:]  # Пропускаем заголовок


# Проходим по именам и записываем их в словарь stuff
for index, name in enumerate(names, start=2):  # Нумерация начинается с 2, так как первая строка - заголовок
    stuff[name] = index


# Создание обратного словаря
reverse_stuff = {v: k for k, v in stuff.items()}


# Создаем словарь
fio_chatid_dict = {name: chat_id for name, chat_id in zip(names, chat_ids) if chat_id}


# Открываем второй лист
worksheet2 = spreadsheet.get_worksheet(1)  # Открываем второй лист

# Получаем все строки второго листа
rows = worksheet2.get_all_values()[1:]  # Пропускаем заголовок


def send_q(chat_id, questionary, obj):
    user_data[chat_id] = [obj, questionary]

    stuff_id = stuff[obj]

    # Открываем 3 лист
    worksheet3 = spreadsheet.get_worksheet(2)

    # Получаем все строки 3 листа
    rows = worksheet3.get_all_values()[1:]  # Пропускаем заголовок

    for row in rows:
        if row[0] == questionary:
            for i in range(1, len(row) - 1):
                #Добавляем вопрос и его индекс в словарь
                questions[i] = row[i]

                if row[i + 1] == 'int':
                    # Создаем клавиатуру для оценки
                    markup = types.InlineKeyboardMarkup()
                    markup.row(
                        types.InlineKeyboardButton(text="1", callback_data=f"rate_1_{stuff_id}_{speciality}_{i}"),
                        types.InlineKeyboardButton(text="2", callback_data=f"rate_2_{stuff_id}_{speciality}_{i}"),
                        types.InlineKeyboardButton(text="3", callback_data=f"rate_3_{stuff_id}_{speciality}_{i}"),
                        types.InlineKeyboardButton(text="4", callback_data=f"rate_4_{stuff_id}_{speciality}_{i}"),
                        types.InlineKeyboardButton(text="5", callback_data=f"rate_5_{stuff_id}_{speciality}_{i}")
                    )

                    bot.send_message(chat_id, row[i], reply_markup=markup)

                if row[i + 1] == 'str':
                    mesg = bot.send_message(chat_id, row[i])
                    bot.register_next_step_handler(mesg, str_saver)

def str_saver(message):
    try:
        user_data[str(message.chat.id)].append(message.text)
        user_data[str(message.chat.id)].insert(2, str(datetime.datetime.now()))

        # Открываем 4 лист
        worksheet4 = spreadsheet.get_worksheet(3)

        worksheet4.append_row(user_data[str(message.chat.id)])

        bot.send_message(message.chat.id, "Спасибо за обратную связь!")

    except Exception as e:
        bot.send_message(message.chat.id,f"Ошибка при попытке записи ответов: {e}")



# Обработчик колбэков для оценок
@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_"))
def handle_rating_callback(call):
    try:
        print(f"Получено callback_data: {call.data}")  # Для отладки
        # Разбиваем callback_data чтобы получить оценку, obj, speciality и сам вопрос
        _, rating, obj_id, speciality, i = call.data.split("_")
        print(f"rating: {rating}, obj_id: {obj_id}, speciality: {speciality}, i: {i}")  # Для отладки

        obj = reverse_stuff[int(obj_id)]  # Преобразование ID объекта в int

        i = int(i)  # Преобразование индекса вопроса в int

        chat_id_str = str(call.message.chat.id)

        user_data[chat_id_str].append(questions[i])
        user_data[chat_id_str].append(rating)
        #print(user_data)
        #bot.send_message(call.message.chat.id, f"{questions[i]}\n\nОценка: {rating}")

    except Exception as e:
        print(f"Ошибка при обработке рейтинга: {e}")







# Проходим по каждой строке
for row in rows:
    fio = row[0].strip()  # Берем ФИО из первого столбца
    obj = row[1]   # Текст из второго столбца
    speciality = row[2]   # Текст из третьего столбца

    # Проверяем, есть ли chat_id для данного ФИО в словаре
    chat_id = fio_chatid_dict.get(fio)

    if chat_id:
        try:
            # Отправляем сообщение
            message = f"На этой неделе с вами работал(-а): {obj}. Пожалуйста, пройдите опрос: {speciality}"
            bot.send_message(chat_id, message)
            send_q(chat_id, speciality, obj)

            print(f"Сообщение отправлено пользователю {fio} (chat_id: {chat_id})")
        except Exception as e:
            print(f"Не удалось отправить сообщение для {fio}. Ошибка: {e}")
    else:
        print(f"Чат ID для {fio} не найден")



bot.polling(none_stop=True)