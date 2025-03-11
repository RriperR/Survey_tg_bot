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

        # Находим file_id для оцениваемого сотрудника
        obj_info = cached_employees.get(survey_info['obj'])
        if obj_info and obj_info['file_id']:
            file_id = obj_info['file_id']
            message = (
                f"На этой неделе с вами работал(-а): {survey_info['obj']}.\n"
                f"Пожалуйста, пройдите опрос: {survey_info['questionary']}"
            )
            bot.send_photo(chat_id, photo=file_id, caption=message)
        else:
            # Если file_id не найден, отправляем стандартное изображение
            send_unknown_image(chat_id, survey_info)

        # Небольшая задержка и отправка первого вопроса
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
    questions = cached_questionnaires.get(questionary, [])

    if questions:
        data['current_survey']['questions'] = questions
        logger.info(f"Опрос {questionary} для {chat_id} найден в кешированных данных.")
    else:
        logger.warning(f"Опрос {questionary} не найден в локальном кеше.")



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

    # worksheet4 = spreadsheet.get_worksheet(3)
    # worksheet4.append_row(row_data[1::])

    second_worksheet.append_row(row_data)

    bot.send_message(chat_id, "Спасибо за обратную связь!")

    while len(row_data) < 14:
        row_data.append(None)

    try:
        with DatabaseManager(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD) as db:
            db.insert_survey_response(row_data)
    except Exception as ex:
        bot.send_message(chat_id, f"Не удалось сохранить ответы в базу данных")
        logger.error(f"Не удалось сохранить ответы в базу данных: {ex}")

    data['current_survey'] = None
    start_next_survey(chat_id)



# Функция для запуска опросов
def run_survey_dispatch():
    global user_data
    logger.info("Запуск процесса назначения опросов")

    today = datetime.date.today()

    # Проходимся по кешированным назначениям
    for assignment in cached_assignments:
        subj = assignment['subj']
        obj = assignment['obj']
        questionary = assignment['questionary']
        date_str = assignment['date']

        try:
            day = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
        except ValueError:
            continue  # Пропускаем этот опрос и переходим к следующему


        if day == today:
            # Ищем chat_id для субъекта
            subj_info = cached_employees.get(subj)
            if subj_info and subj_info['chat_id']:
                try:
                    chat_id = int(subj_info['chat_id'])

                    # Создаём опрос, если его нет
                    user_data.setdefault(chat_id, {'survey_queue': [], 'current_survey': None})

                    # Добавляем опрос в очередь пользователя
                    user_data[chat_id]['survey_queue'].append({
                        'subj': subj,
                        'obj': obj,
                        'questionary': questionary
                    })

                    # Если в данный момент опрос не запущен, запускаем сразу
                    if user_data[chat_id]['current_survey'] is None:
                        start_next_survey(chat_id)

                    logger.info(f"Опрос '{questionary}' добавлен в очередь для {subj} (chat_id: {chat_id})")
                except Exception as e:
                    logger.error(f"Не удалось добавить опрос для {subj}. Ошибка: {e}")
            else:
                logger.warning(f"Чат ID для {subj} не найден")
        else:
            logger.info(f"Дата проведения опроса для {subj} не совпадает с сегодняшней: {day}")