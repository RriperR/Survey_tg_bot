import logging

from init import bot, worksheet, cached_employees
from telebot import types


# Настройка логирования
logger = logging.getLogger("reg")
logger.setLevel(logging.INFO)

handler = logging.FileHandler("/code/logs/reg.log", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger.addHandler(handler)


# Словарь для хранения выбранных ФИО перед подтверждением
pending_registration = {}  # { chat_id: 'ФИО' }

# Обработчик команды /start для регистрации пользователя
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    logger.info(f"Получена команда /start от chat_id={chat_id}")

    bot.send_message(chat_id, "Загрузка данных...")

    if not cached_employees:
        bot.send_message(chat_id, "Ошибка: данные сотрудников не загружены.")
        logger.warning(f"Пустой кеш сотрудников для chat_id={chat_id}")
        return

    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for name in cached_employees.keys():
        markup.add(name)

    bot.send_message(chat_id, "Выберите ФИО:", reply_markup=markup)



# Обработчик выбора имени
@bot.message_handler(func=lambda message: message.text in cached_employees.keys())
def handle_name_selection(message):
    chat_id = message.chat.id
    selected_name = message.text.strip()
    logger.info(f"Пользователь chat_id={chat_id} выбрал ФИО: {selected_name}")

    pending_registration[chat_id] = selected_name  # Сохраняем ФИО для подтверждения

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
        str_chat_id = str(chat_id)

        if any(data['chat_id'] == str_chat_id for data in cached_employees.values()):
            # Находим имя (ФИО), чтобы вывести пользователю
            registered_name = next(
                name for name, data in cached_employees.items()
                if data['chat_id'] == str_chat_id
            )
            bot.send_message(chat_id, f"Вы уже зарегистрированы как {registered_name}.",
                             reply_markup=types.ReplyKeyboardRemove())
            logger.info(f"chat_id={chat_id} уже зарегистрирован как {registered_name}")
            return

        selected_name = pending_registration.get(chat_id)
        if not selected_name:
            bot.send_message(chat_id, "Произошла ошибка, попробуйте снова с помощью /start.")
            return

        # Обновляем кеш и записываем chat_id
        cached_employees[selected_name]['chat_id'] = str(chat_id)

        # Записываем chat_id в Google Sheets
        try:
            all_names = worksheet.col_values(1)[1:]  # Получаем ФИО из 1-го столбца, пропуская заголовок
            row_index = all_names.index(selected_name) + 2  # +2 из-за заголовка

            worksheet.update_cell(row_index, 3, chat_id)  # Записываем chat_id в 3-й столбец
            logger.info(f"chat_id={chat_id} зарегистрирован как {selected_name}, записан в строку {row_index}")

            bot.send_message(chat_id, f"Вы успешно зарегистрировались как {selected_name}.",
                             reply_markup=types.ReplyKeyboardRemove())
            bot.send_message(chat_id, "Пожалуйста, отправьте ваше фото:")

        except Exception as e:
            logger.error(f"Ошибка записи chat_id в таблицу: {e}", exc_info=True)
            bot.send_message(chat_id, "Произошла ошибка при сохранении данных.")

    elif call.data == "confirm_no":
        # Если пользователь отменил выбор, предлагаем выбрать снова
        bot.send_message(chat_id, "Пожалуйста, выберите ФИО снова с помощью команды /start")
        pending_registration.pop(chat_id, None)  # Удаляем сохранённый выбор
        logger.info(f"chat_id={chat_id} отменил выбор имени")



# Обработчик для получения фото и сохранения file_id в 2-й столбец
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id
    logger.info(f"Получено фото от chat_id={chat_id}")

    # Проверяем, зарегистрирован ли пользователь
    registered_name = next((name for name, data in cached_employees.items() if data['chat_id'] == str(chat_id)), None)

    if registered_name:
        file_id = message.photo[-1].file_id

        try:
            all_names = worksheet.col_values(1)[1:]  # Получаем ФИО из 1-го столбца, пропуская заголовок
            row_index = all_names.index(registered_name) + 2  # +2 из-за заголовка

            worksheet.update_cell(row_index, 2, file_id)  # Записываем file_id во 2-й столбец
            logger.info(f"Фото записано в строку {row_index} для chat_id={chat_id}")

            bot.send_message(chat_id, "Фото успешно сохранено! Регистрация завершена.")

        except Exception as e:
            logger.error(f"Ошибка записи фото в таблицу: {e}", exc_info=True)
            bot.send_message(chat_id, "Ошибка при сохранении фото.")

    else:
        bot.send_message(chat_id, "Пожалуйста, сначала зарегистрируйтесь с помощью команды /start.")
        logger.warning(f"chat_id={chat_id} попытался отправить фото без регистрации")
