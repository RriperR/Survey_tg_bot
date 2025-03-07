import time
import datetime
import logging

from telebot import types
from init import *
from models import DatabaseManager


# Настройка логирования
logger = logging.getLogger("survey")  # Отдельный логгер "survey"
logger.setLevel(logging.INFO)

handler = logging.FileHandler("/code/logs/survey.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)


# Функции для опросов
def start_next_survey(chat_id):
    data = user_data.get(chat_id)
    if not data:
        logger.warning(f"Нет данных для пользователя {chat_id}")
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

        logger.info(f"Запущен опрос '{survey_info['questionary']}' для {chat_id}")

        # Загружаем вопросы для этого опроса
        load_questions_for_survey(chat_id)

        # Получаем строку для `obj` из Google Sheets, чтобы извлечь file_id
        obj_names = worksheet.col_values(1)[1:]  # Все имена в первом столбце, пропуская заголовок
        found_row = None
        for index, name in enumerate(obj_names):
            if name.strip() == survey_info['obj']:
                found_row = index + 2  # +2 из-за заголовка

        # Проверка, если row найден, и получение file_id
        if found_row:
            file_id = worksheet.cell(found_row, 2).value  # Получаем file_id из второго столбца

            if file_id:
                # Отправляем фотографию по file_id
                message = f"На этой неделе с вами работал(-а): {survey_info['obj']}. Пожалуйста, пройдите опрос: {survey_info['questionary']}"
                bot.send_photo(chat_id, photo=file_id, caption=message)
            else:
                # Если file_id отсутствует, отправляем стандартное изображение
                send_unknown_image(chat_id, survey_info)
        else:
            # Если не найдено имя, отправляем стандартное изображение
            send_unknown_image(chat_id, survey_info)

        # Начинаем опрос
        time.sleep(1)
        send_next_question(chat_id)
    else:
        # Очередь опросов пуста
        data['current_survey'] = None
        logger.info(f"Очередь опросов пуста для {chat_id}")




# Функция отправки стандартного изображения при отсутствии file_id
def send_unknown_image(chat_id, survey_info):
    with open("images/unknown.png", 'rb') as image_file:
        message = f"На этой неделе с вами работал(-а): {survey_info['obj']}. Пожалуйста, пройдите опрос: {survey_info['questionary']}"
        bot.send_photo(chat_id, photo=image_file, caption=message)



def load_questions_for_survey(chat_id):
    data = user_data.get(chat_id)
    if not data or not data['current_survey']:
        logger.warning(f"Нет активного опроса для {chat_id} (load_questions_for_survey)")
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
            logger.info(f"Опрос {questionary} для {chat_id} найден")
            break  # Нашли нужный опрос, выходим из цикла



def send_next_question(chat_id):
    data = user_data.get(chat_id)
    if not data or not data['current_survey']:
        logger.warning(f"Нет активного опроса для {chat_id} (send_next_question)")
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
            time.sleep(1)
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
        logger.warning(f"Получена оценка '{message.text}', но нет активного опроса для {chat_id}")
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
            logger.warning(f"Получена оценка {rating}, но нет активного опроса для {chat_id}")
            return

        survey = data['current_survey']
        index = survey['current_question_index']
        survey['answers'].append((survey['questions'][index][0], rating))
        survey['current_question_index'] += 1
        # Отвечаем на колбэк, чтобы убрать "часики"
        bot.answer_callback_query(call.id)
        send_next_question(chat_id)
    except Exception as e:
        logger.error(f"Ошибка при обработке рейтинга: {e}")



# Функция для завершения опроса
def finalize_questionnaire(chat_id):
    data = user_data.get(chat_id)
    if not data or not data['current_survey']:
        logger.warning(f"Попытка завершить опрос, но нет активного опроса для {chat_id}")
        return

    survey = data['current_survey']

    row_data = [survey['subj'], survey['obj'], survey['questionary'], str(datetime.datetime.now())]
    for question, answer in survey['answers']:
        row_data.extend([question, answer])

    worksheet4 = spreadsheet.get_worksheet(3)
    worksheet4.append_row(row_data[1::])

    second_spreadsheet = client.open("survey_answers")
    second_worksheet = second_spreadsheet.sheet1
    second_worksheet.append_row(row_data)

    bot.send_message(chat_id, "Спасибо за обратную связь!")

    while len(row_data) < 14:
        row_data.append(None)

    try:
        with DatabaseManager(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD) as db:
            db.insert_survey_response(row_data)
    except Exception as ex:
        bot.send_message(chat_id, f"Не удалось сохранить в базу данных: {ex}")

    data['current_survey'] = None
    start_next_survey(chat_id)



# Функция для запуска опросов
def run_survey_dispatch():
    global user_data, fio_chatid_dict, spreadsheet
    logger.info("Запуск процесса назначения опросов")

    # Открываем второй лист (назначения опросов)
    worksheet2 = spreadsheet.get_worksheet(1)  # Индексация начинается с 0

    # Получаем все строки со второго листа, пропуская заголовок
    rows = worksheet2.get_all_values()[1:]  # Пропускаем заголовок

    # Обрабатываем опросы для каждого пользователя
    for row in rows:
        subj = row[0].strip()    # ФИО субъекта (кто будет проходить опрос)
        obj = row[1].strip()     # ФИО объекта (кого оценивают)
        questionary = row[2].strip()  # Название опроса
        date_from_sheet = row[4].strip() # Дата для отправки опроса

        try:
            day = datetime.datetime.strptime(date_from_sheet, "%d.%m.%Y").date()
        except ValueError:
            continue  # Пропускаем этот опрос и переходим к следующему

        # Проверяем, есть ли chat_id для данного ФИО
        chat_id = fio_chatid_dict.get(subj)

        if day == datetime.date.today():
            if chat_id:
                try:
                    chat_id = int(chat_id)  # Преобразуем chat_id в целое число

                    # Создаём опрос, если его нет
                    user_data.setdefault(chat_id, {'survey_queue': [], 'current_survey': None})

                    # Добавляем опрос в очередь пользователя
                    user_data[chat_id]['survey_queue'].append({
                        'subj': subj,
                        'obj': obj,
                        'questionary': questionary
                    })

                    # Если пользователь не проходит опрос, запускаем следующий
                    if user_data[chat_id]['current_survey'] is None:
                        start_next_survey(chat_id)

                    logger.info(f"Опрос '{questionary}' добавлен в очередь для {subj} (chat_id: {chat_id})")
                except Exception as e:
                    logger.error(f"Не удалось добавить опрос для {subj}. Ошибка: {e}")
            else:
                logger.warning(f"Чат ID для {subj} не найден")
        else:
            logger.info(f"Дата проведения опроса для {subj} не совпадает с сегодняшней: {day}")