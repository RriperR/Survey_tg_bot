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

############################
# Вспомогательные функции
############################

def get_subject_name(chat_id):
    for name, info in cached_employees.items():
        if str(info.get('chat_id')) == str(chat_id):
            return name
    return None

def send_assignment_header(chat_id, object_name, questionnaire_name):
    obj_info = cached_employees.get(object_name)
    message = (
        f"На этой неделе с вами работал(-а): {object_name}.\n"
        f"Пожалуйста, пройдите опрос: {questionnaire_name}"
    )
    if obj_info and obj_info.get('file_id'):
        bot.send_photo(chat_id, photo=obj_info['file_id'], caption=message)
    else:
        with open("images/unknown.png", 'rb') as image_file:
            bot.send_photo(chat_id, photo=image_file, caption=message)


############################
# Основная логика опросов
############################

def start_next_survey(chat_id):
    """
    - Определяем ФИО пользователя.
    - Ищем первый непройденный опрос в survey_assignments.
    - Если найден -> отправляем «шапку» (картинка + текст) и сразу вызываем send_next_question(chat_id).
    - Если нет -> выводим, что опросов нет.
    """
    subject_name = get_subject_name(chat_id)
    if not subject_name:
        logger.warning(f"Не найдено ФИО для chat_id={chat_id}")
        return

    try:
        with DatabaseManager(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD) as db:
            # Первый непройденный опрос
            assignment = db.fetch_one("""
                SELECT id, object, questionnaire
                FROM survey_assignments
                WHERE subject = %s AND completed_at IS NULL
                ORDER BY id
                LIMIT 1
            """, (subject_name,))

            if not assignment:
                logger.info(f"У пользователя {subject_name} (chat_id={chat_id}) нет непройденных опросов.")
                return

            assignment_id, object_name, questionnaire_name = assignment
            # Отправляем «шапку»
            send_assignment_header(chat_id, object_name, questionnaire_name)

            # Сразу отправляем первый вопрос
            send_next_question(chat_id)

    except Exception as e:
        logger.error(f"Ошибка в start_next_survey для chat_id={chat_id}: {e}")


def send_next_question(chat_id):
    """
    1. По chat_id получаем ФИО субъекта.
    2. Ищем первый непройденный опрос.
    3. В этом опросе (survey_assignments) находим первый вопрос (survey_questions) с user_response IS NULL.
    4. Если нет вопросов -> finalize_questionnaire(chat_id).
    5. Иначе отправляем вопрос (с кнопками или текстом).
    """
    subject_name = get_subject_name(chat_id)
    if not subject_name:
        logger.warning(f"send_next_question: Не найдено ФИО для chat_id={chat_id}")
        return

    try:
        with DatabaseManager(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD) as db:
            # Ищем первый непройденный опрос
            assignment = db.fetch_one("""
                SELECT id, object, questionnaire
                FROM survey_assignments
                WHERE subject = %s AND completed_at IS NULL
                ORDER BY id
                LIMIT 1
            """, (subject_name,))

            if not assignment:
                # Нет опроса — всё уже пройдено
                logger.info(f"У пользователя {subject_name} (chat_id={chat_id}) нет непройденных опросов.")
                return

            assignment_id, object_name, questionnaire_name = assignment

            # Ищем первый неотвеченный вопрос
            question_row = db.fetch_one("""
                SELECT id, question_text
                FROM survey_questions
                WHERE survey_id = %s AND user_response IS NULL
                ORDER BY id
                LIMIT 1
            """, (assignment_id,))

            if not question_row:
                # Все вопросы в этом опросе уже отвечены -> завершаем
                finalize_questionnaire(chat_id)
                return

            question_id, question_text = question_row

            # Проверяем, это вопрос с текстовым ответом или рейтинговым
            if "Что бы вы порекомендовали" in question_text:
                msg = bot.send_message(chat_id, question_text)
                # Регистрируем обработчик текстового ответа
                bot.register_next_step_handler(msg, handle_text_response)
            else:
                # Отправляем вопрос + inline-кнопки
                markup = types.InlineKeyboardMarkup()
                markup.row(
                    types.InlineKeyboardButton(text="1", callback_data="rate_1"),
                    types.InlineKeyboardButton(text="2", callback_data="rate_2"),
                    types.InlineKeyboardButton(text="3", callback_data="rate_3"),
                    types.InlineKeyboardButton(text="4", callback_data="rate_4"),
                    types.InlineKeyboardButton(text="5", callback_data="rate_5")
                )
                bot.send_message(chat_id, question_text, reply_markup=markup)

    except Exception as e:
        logger.error(f"Ошибка в send_next_question для chat_id={chat_id}: {e}")


def handle_text_response(message):
    """
    Обработчик текстового ответа:
    1. Находим первый непройденный опрос и первый вопрос (user_response IS NULL).
    2. Обновляем user_response данным текстом.
    3. Вызываем send_next_question(chat_id).
    """
    chat_id = message.chat.id
    text = message.text.strip()

    subject_name = get_subject_name(chat_id)
    if not subject_name:
        logger.warning(f"handle_text_response: Не найдено ФИО для chat_id={chat_id}")
        return

    try:
        with DatabaseManager(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD) as db:
            # 1) находим первый непройденный опрос
            assignment = db.fetch_one("""
                SELECT id
                FROM survey_assignments
                WHERE subject = %s AND completed_at IS NULL
                ORDER BY id
                LIMIT 1
            """, (subject_name,))
            if not assignment:
                logger.info(f"handle_text_response: нет непройденных опросов у {subject_name}")
                bot.send_message(chat_id, "Все опросы пройдены.")
                return
            assignment_id = assignment[0]

            # 2) находим первый вопрос без ответа
            question_row = db.fetch_one("""
                SELECT id
                FROM survey_questions
                WHERE survey_id = %s AND user_response IS NULL
                ORDER BY id
                LIMIT 1
            """, (assignment_id,))
            if not question_row:
                # вопросов нет, завершаем
                finalize_questionnaire(chat_id)
                return
            question_id = question_row[0]

            # 3) обновляем ответ
            db.execute(
                "UPDATE survey_questions SET user_response = %s WHERE id = %s",
                (text, question_id)
            )

        # Переходим к следующему вопросу
        send_next_question(chat_id)

    except Exception as e:
        logger.error(f"Ошибка в handle_text_response для chat_id={chat_id}: {e}")


@bot.callback_query_handler(func=lambda call: call.data.startswith("rate_"))
def handle_rating_callback(call):
    """
    Аналогично handle_text_response, но для inline-кнопок:
    1) Определяем rating из call.data
    2) Смотрим, какой первый вопрос без ответа
    3) Обновляем user_response
    4) send_next_question(chat_id)
    """
    try:
        rating = call.data.split("_")[1]  # "rate_5" -> "5"
        chat_id = call.message.chat.id

        subject_name = get_subject_name(chat_id)
        if not subject_name:
            logger.warning(f"handle_rating_callback: Не найдено ФИО для chat_id={chat_id}")
            return

        with DatabaseManager(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD) as db:
            # 1) Берём первый непройденный опрос
            assignment = db.fetch_one("""
                SELECT id
                FROM survey_assignments
                WHERE subject = %s AND completed_at IS NULL
                ORDER BY id
                LIMIT 1
            """, (subject_name,))

            if not assignment:
                logger.info(f"handle_rating_callback: нет непройденных опросов у {subject_name}")
                bot.send_message(chat_id, "Все опросы пройдены. Не тыкайте по кнопкам лишний раз!!!")
                return

            assignment_id = assignment[0]

            # 2) Берём первый неотвеченный вопрос
            question_row = db.fetch_one("""
                SELECT id
                FROM survey_questions
                WHERE survey_id = %s AND user_response IS NULL
                ORDER BY id
                LIMIT 1
            """, (assignment_id,))
            if not question_row:
                # Нет вопросов -> завершаем
                finalize_questionnaire(chat_id)
                return
            question_id = question_row[0]

            # 3) Обновляем ответ
            db.execute(
                "UPDATE survey_questions SET user_response = %s WHERE id = %s",
                (rating, question_id)
            )

        # Отвечаем на callback (убрать «часики»)
        bot.answer_callback_query(call.id)

        # 4) Отправляем следующий вопрос
        send_next_question(chat_id)

    except Exception as e:
        logger.error(f"Ошибка при обработке рейтинга: {e}")


def finalize_questionnaire(chat_id):
    """
    1. Ставим дату в completed_at, если действительно все вопросы отвечены (проверим).
    2. Говорим «Спасибо».
    3. При желании вызываем start_next_survey(chat_id) для следующего опроса.
    """
    subject_name = get_subject_name(chat_id)
    if not subject_name:
        logger.warning(f"finalize_questionnaire: Не найдено ФИО для chat_id={chat_id}")
        return

    try:
        with DatabaseManager(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD) as db:
            # 1) Определяем первый непройденный опрос
            assignment = db.fetch_one("""
                SELECT id, questionnaire
                FROM survey_assignments
                WHERE subject = %s AND completed_at IS NULL
                ORDER BY id
                LIMIT 1
            """, (subject_name,))
            if not assignment:
                # Нет непройденных опросов, ничего завершать
                return
            assignment_id, questionnaire_name = assignment

            # 2) Проверяем, остались ли ещё вопросы без ответа
            unanswered = db.fetch_one("""
                SELECT id
                FROM survey_questions
                WHERE survey_id = %s AND user_response IS NULL
                LIMIT 1
            """, (assignment_id,))
            if unanswered:
                # Значит, есть вопросы без ответа — нельзя завершать
                return

            # 3) Все вопросы отвечены -> ставим дату
            db.execute("""
                UPDATE survey_assignments
                SET completed_at = NOW()
                WHERE id = %s
            """, (assignment_id,))

        # 4) Сообщаем пользователю
        bot.send_message(chat_id, f"Спасибо за обратную связь! Опрос '{questionnaire_name}' завершён.")

        # 5) Если хотим сразу запускать следующий опрос
        start_next_survey(chat_id)

    except Exception as e:
        logger.error(f"Ошибка в finalize_questionnaire: {e}")


def fill_survey_assignments():
    logger.info("Начало заполнения таблицы survey_assignments")
    today = datetime.date.today()

    try:
        with DatabaseManager(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD) as db:
            for assignment in cached_assignments:
                subj_name = assignment.get('subj')
                obj_name = assignment.get('obj')
                questionnaire = assignment.get('questionary')
                date_str = assignment.get('date')

                try:
                    survey_date = datetime.datetime.strptime(date_str, "%d.%m.%Y").date()
                except ValueError:
                    logger.warning(f"Некорректный формат даты: {date_str} для задания {assignment}")
                    continue

                if survey_date == today:
                    # Вставляем запись в таблицу survey_assignments
                    query = "INSERT INTO survey_assignments (subject, object, questionnaire, survey_date, completed_at) VALUES (%s, %s, %s, %s, NULL)"
                    db.execute(query, (subj_name, obj_name, questionnaire, survey_date))
                    logger.info(f"Добавлено задание: субъект {subj_name}, объект {obj_name}, опросник {questionnaire}")

    except Exception as e:
        logger.error(f"Ошибка при заполнении таблицы survey_assignments: {e}")


def fill_survey_questions():
    logger.info("Начало заполнения таблицы survey_questions")

    try:
        with DatabaseManager(DB_HOST, DB_NAME, DB_USER, DB_PASSWORD) as db:
            # Получаем все активные опросы
            active_surveys = db.fetch_all("SELECT id, questionnaire FROM survey_assignments WHERE completed_at IS NULL")

            for survey_id, questionnaire_name in active_surveys:
                # Проверяем, есть ли опросник в кеше
                questions = cached_questionnaires.get(questionnaire_name)
                if not questions:
                    logger.warning(f"Опросник '{questionnaire_name}' не найден в кеше")
                    continue

                # Записываем вопросы в таблицу survey_questions
                for question_text, question_type in questions:
                    query = "INSERT INTO survey_questions (survey_id, question_text) VALUES (%s, %s)"
                    db.execute(query,(survey_id, question_text))

                logger.info(f"Добавлены вопросы для опроса '{questionnaire_name}' (Survey_id: {survey_id})")

    except Exception as e:
        logger.error(f"Ошибка при заполнении таблицы survey_questions: {e}")


def run_survey_dispatch():
    logger.info("Запуск процесса назначения опросов")

    # Сначала заполняем таблицы, если нужно
    fill_survey_assignments()
    fill_survey_questions()

    # Проходим по всем сотрудникам
    for fio, info in cached_employees.items():
        chat_id = info.get('chat_id')
        if not chat_id:
            continue
        # Пробуем запустить опрос (если есть непройденные)
        start_next_survey(chat_id)



@bot.message_handler(commands=['process'])
def process(message):
    bot.send_message(message.chat.id, "Процесс пошёл")
    run_survey_dispatch()

@bot.message_handler(commands=['update'])
def update(message):
    update_local_cache()
