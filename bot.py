import telebot
from telebot import types
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import schedule
import threading
import time
import datetime
import psycopg2
import subprocess
import os
from dotenv import load_dotenv

# Настройка авторизации Google Sheets API
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
# Замените 'your_credentials_file.json' на имя вашего файла с учетными данными
creds = ServiceAccountCredentials.from_json_keyfile_name('q-bot-435919-f9cd6316f9b0.json', scope)
client = gspread.authorize(creds)

# Открываем таблицу по имени
# Замените "Сотрудник 2.0 Таблица" на имя вашей таблицы
spreadsheet = client.open("Сотрудник 2.0 Таблица")
worksheet = spreadsheet.sheet1



load_dotenv()
# Получение переменных окружения
TELEGRAM_BOT_TOKEN = os.environ.get('BOT_TOKEN')
DB_HOST = os.environ.get('DB_HOST')
DB_NAME = os.environ.get('DB_NAME')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')

# Инициализируем бота
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

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


def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn

# try:
#     get_db_connection()
#     print('Success')
# except Exception as ex:
#     print(ex)

# Обработчик команды /start для регистрации пользователя
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Загрузка данных...")

    # Получаем список ФИО из первого столбца
    names = worksheet.col_values(1)[1:]  # Пропускаем заголовок

    # Создаем клавиатуру
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for name in names:
        markup.add(name)

    bot.send_message(chat_id, "Выберите ФИО:", reply_markup=markup)

# Обработчик выбора имени
@bot.message_handler(func=lambda message: True)
def handle_name_selection(message):
    chat_id = message.chat.id
    selected_name = message.text.strip()

    # Сохраняем выбранное имя в глобальной переменной для пользователя
    user_names[chat_id] = selected_name

    # Создаем клавиатуру для подтверждения выбора
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text="Да", callback_data="confirm_yes"))
    markup.add(types.InlineKeyboardButton(text="Нет", callback_data="confirm_no"))

    bot.send_message(chat_id, f"Вы выбрали {selected_name}. Всё верно?", reply_markup=markup)

# Обработка нажатия на кнопку подтверждения
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
def handle_confirmation(call):
    chat_id = call.message.chat.id
    if call.data == "confirm_yes":
        # Проверяем, зарегистрирован ли уже этот chat_id
        chat_ids = worksheet.col_values(3)[1:]  # chat_id в 3 столбце, пропускаем заголовок

        if str(chat_id) in chat_ids:
            # Если chat_id найден, ищем соответствующее имя
            row_index = chat_ids.index(str(chat_id)) + 2  # +2 из-за пропуска заголовка и индексации с 0
            registered_name = worksheet.cell(row_index, 1).value  # ФИО в 1 столбце

            bot.send_message(chat_id, f"Вы уже зарегистрировались как {registered_name}.")
        else:
            selected_name = user_names.get(chat_id).strip()

            # Получаем все имена из первого столбца
            names_in_sheet = worksheet.col_values(1)[1:]  # Пропускаем заголовок

            # Ищем строку с именем
            found_row = None
            for index, name in enumerate(names_in_sheet):
                if name.strip() == selected_name:
                    found_row = index + 2  # +2 из-за пропуска заголовка

            if found_row:
                worksheet.update_cell(found_row, 3, chat_id)  # Записываем chat_id в 3 столбец
                bot.send_message(chat_id, f"Вы успешно зарегистрировались как {selected_name}.")

                # Обновляем словарь fio_chatid_dict
                fio_chatid_dict[selected_name] = str(chat_id)
            else:
                bot.send_message(chat_id, "Произошла ошибка: не удалось найти ваше имя в таблице.")
    elif call.data == "confirm_no":
        # Если пользователь отменил выбор, предлагаем выбрать снова
        bot.send_message(chat_id, "Пожалуйста, выберите ФИО снова с помощью команды /start")
        del user_names[chat_id]  # Очищаем сохраненное имя для пользователя

# Функции для опросов
def start_next_survey(chat_id):
    data = user_data.get(chat_id)
    if not data:
        return

    if data['survey_queue']:
        # Берем следующий опрос из очереди
        survey_info = data['survey_queue'].pop(0)
        # Устанавливаем текущий опрос
        data['current_survey'] = {
            'subj': survey_info['subj'],
            'obj': survey_info['obj'],
            'questionary': survey_info['questionary'],
            'current_question_index': 0,
            'questions': [],
            'answers': []
        }

        # Загружаем вопросы для этого опроса
        load_questions_for_survey(chat_id)

        # Путь к изображению
        image_path = f"images/{survey_info['obj']}.png"

        # Проверка, существует ли файл изображения
        if os.path.exists(image_path):
            with open(image_path, 'rb') as image_file:
                # Отправляем фотографию с сообщением
                message = f"На этой неделе с вами работал(-а): {survey_info['obj']}. Пожалуйста, пройдите опрос: {survey_info['questionary']}"
                bot.send_photo(chat_id, photo=image_file, caption=message)
        else:
            with open("images/unknown.png", 'rb') as image_file:
                # Отправляем фотографию с сообщением
                message = f"На этой неделе с вами работал(-а): {survey_info['obj']}. Пожалуйста, пройдите опрос: {survey_info['questionary']}"
                bot.send_photo(chat_id, photo=image_file, caption=message)

        # Начинаем опрос
        send_next_question(chat_id)
    else:
        # Очередь опросов пуста
        data['current_survey'] = None

def load_questions_for_survey(chat_id):
    data = user_data.get(chat_id)
    if not data or not data['current_survey']:
        return

    questionary = data['current_survey']['questionary']

    # Открываем 3 лист (вопросы)
    worksheet3 = spreadsheet.get_worksheet(2)
    rows = worksheet3.get_all_values()[1:]  # Пропускаем заголовок

    for row in rows:
        if row[0] == questionary:
            # Предполагаем, что вопросы и их типы идут попарно начиная с индекса 1
            for i in range(1, len(row), 2):
                question = row[i]
                q_type = row[i + 1] if i + 1 < len(row) else ''
                data['current_survey']['questions'].append((question, q_type))
            break  # Нашли нужный опрос, выходим из цикла

def send_next_question(chat_id):
    data = user_data.get(chat_id)
    if not data or not data['current_survey']:
        return

    survey = data['current_survey']
    index = survey['current_question_index']
    if index < len(survey['questions']):
        question, q_type = survey['questions'][index]
        if q_type == 'int':
            # Создаем клавиатуру для оценки
            markup = types.InlineKeyboardMarkup()
            markup.row(
                types.InlineKeyboardButton(text="1", callback_data="rate_1"),
                types.InlineKeyboardButton(text="2", callback_data="rate_2"),
                types.InlineKeyboardButton(text="3", callback_data="rate_3"),
                types.InlineKeyboardButton(text="4", callback_data="rate_4"),
                types.InlineKeyboardButton(text="5", callback_data="rate_5")
            )
            bot.send_message(chat_id, question, reply_markup=markup)
        elif q_type == 'str':
            msg = bot.send_message(chat_id, question)
            bot.register_next_step_handler(msg, handle_text_response)
    else:
        # Вопросы закончились, завершаем опрос
        finalize_questionnaire(chat_id)

# Обработчик текстовых ответов
def handle_text_response(message):
    chat_id = message.chat.id
    data = user_data.get(chat_id)
    if not data or not data['current_survey']:
        return

    survey = data['current_survey']
    index = survey['current_question_index']
    survey['answers'].append((survey['questions'][index][0], message.text))
    survey['current_question_index'] += 1
    finalize_questionnaire(chat_id)

# Обработчик оценок
@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_"))
def handle_rating_callback(call):
    try:
        rating = call.data.split("_")[1]
        chat_id = call.message.chat.id
        data = user_data.get(chat_id)
        if not data or not data['current_survey']:
            return

        survey = data['current_survey']
        index = survey['current_question_index']
        survey['answers'].append((survey['questions'][index][0], rating))
        survey['current_question_index'] += 1
        # Отвечаем на колбэк, чтобы убрать "часики"
        bot.answer_callback_query(call.id)
        send_next_question(chat_id)
    except Exception as e:
        print(f"Ошибка при обработке рейтинга: {e}")

# Функция для завершения опроса
def finalize_questionnaire(chat_id):
    data = user_data.get(chat_id)
    if not data or not data['current_survey']:
        return

    survey = data['current_survey']

    # Подготовка данных для записи
    row_data = [survey['subj'], survey['obj'], survey['questionary'], str(datetime.datetime.now())]
    for question, answer in survey['answers']:
        row_data.append(question)
        row_data.append(answer)

    # Открываем 4 лист (результаты)
    worksheet4 = spreadsheet.get_worksheet(3)
    worksheet4.append_row(row_data[1::])

    bot.send_message(chat_id, "Спасибо за обратную связь!")

    while len(row_data) < 14:
        row_data.append(None)

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
                INSERT INTO survey_responses (respondent, subject, questionnaire, timestamp, question1, answer1, question2, answer2, question3, answer3, question4, answer4, question5, answer5)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (row_data[0], row_data[1], row_data[2], datetime.datetime.now(), row_data[4], row_data[5], row_data[6], row_data[7], row_data[8], row_data[9], row_data[10], row_data[11], row_data[12], row_data[13]))

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as ex:
        bot.send_message(chat_id, f"Не удалось сохранить в базу данных: {ex}")

    # Очищаем текущий опрос и запускаем следующий, если есть
    data['current_survey'] = None
    start_next_survey(chat_id)

# Функция для запуска опросов
def run_survey_dispatch():
    global user_data, fio_chatid_dict, spreadsheet

    # Открываем второй лист (назначения опросов)
    worksheet2 = spreadsheet.get_worksheet(1)  # Индексация начинается с 0

    # Получаем все строки со второго листа, пропуская заголовок
    rows = worksheet2.get_all_values()[1:]  # Пропускаем заголовок

    # Обрабатываем опросы для каждого пользователя
    for row in rows:
        subj = row[0].strip()    # ФИО субъекта (кто будет проходить опрос)
        obj = row[1].strip()     # ФИО объекта (кого оценивают)
        questionary = row[2].strip()  # Название опроса

        # Проверяем, есть ли chat_id для данного ФИО
        chat_id = fio_chatid_dict.get(subj)

        if chat_id:
            try:
                chat_id = int(chat_id)  # Преобразуем chat_id в целое число

                if chat_id not in user_data:
                    user_data[chat_id] = {
                        'survey_queue': [],
                        'current_survey': None
                    }

                # Добавляем опрос в очередь пользователя
                user_data[chat_id]['survey_queue'].append({
                    'subj': subj,
                    'obj': obj,
                    'questionary': questionary
                })

                # Если пользователь не проходит опрос, запускаем следующий
                if user_data[chat_id]['current_survey'] is None:
                    start_next_survey(chat_id)

                print(f"Опрос '{questionary}' добавлен в очередь для пользователя {subj} (chat_id: {chat_id})")
            except Exception as e:
                print(f"Не удалось добавить опрос для {subj}. Ошибка: {e}")
        else:
            print(f"Чат ID для {subj} не найден")

schedule.every().day.at("19:26").do(run_survey_dispatch)

# Функция для запуска планировщика
def scheduler():
    print('run sh')
    while True:
        schedule.run_pending()
        time.sleep(1)

# Запускаем планировщик в отдельном потоке
scheduler_thread = threading.Thread(target=scheduler)
scheduler_thread.start()

# Запуск бота
bot.polling(none_stop=True)