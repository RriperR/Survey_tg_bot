import telebot
from telebot import types
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

# Создаем словарь ФИО: индекс
for index, name in enumerate(names, start=2):  # Нумерация начинается с 2, так как первая строка - заголовок
    stuff[name] = index

# Создаем словарь ФИО: chat_id
fio_chatid_dict = {name: chat_id for name, chat_id in zip(names, chat_ids) if chat_id}

# Открываем второй лист
worksheet2 = spreadsheet.get_worksheet(1)  # Открываем второй лист

# Получаем все строки второго листа
rows = worksheet2.get_all_values()[1:]  # Пропускаем заголовок

# Функция для начала следующего опроса
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

        # Отправляем сообщение с приглашением пройти опрос
        message = f"На этой неделе с вами работал(-а): {survey_info['obj']}. Пожалуйста, пройдите опрос: {survey_info['questionary']}"
        bot.send_message(chat_id, message)

        # Начинаем опрос
        send_next_question(chat_id)
    else:
        # Очередь опросов пуста
        data['current_survey'] = None

# Функция для загрузки вопросов опроса
def load_questions_for_survey(chat_id):
    data = user_data.get(chat_id)
    if not data or not data['current_survey']:
        return

    questionary = data['current_survey']['questionary']

    # Открываем 3 лист
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

# Функция для отправки следующего вопроса
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
    answer = message.text
    survey['answers'].append((survey['questions'][index][0], answer))
    survey['current_question_index'] += 1
    send_next_question(chat_id)

# Обработчик колбэков для оценок
@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_"))
def handle_rating_callback(call):
    try:
        _, rating = call.data.split("_")
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

    # Открываем 4 лист
    worksheet4 = spreadsheet.get_worksheet(3)
    worksheet4.append_row(row_data[1::])

    bot.send_message(chat_id, "Спасибо за обратную связь!")

    # Очищаем текущий опрос и запускаем следующий, если есть
    data['current_survey'] = None
    start_next_survey(chat_id)

# Обработка опросов для каждого пользователя
for row in rows:
    subj = row[0].strip()  # ФИО из первого столбца
    obj = row[1]           # ФИО из второго столбца
    questionary = row[2]   # Название опроса из третьего столбца

    # Проверяем, есть ли chat_id для данного ФИО в словаре
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
    #else:
    #    print(f"Чат ID для {subj} не найден")

bot.polling(none_stop=True)
