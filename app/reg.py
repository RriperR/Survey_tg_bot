from init import bot, worksheet, user_names, fio_chatid_dict
from telebot import types


# Обработчик команды /start для регистрации пользователя
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Загрузка данных.....")

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

            bot.send_message(chat_id, f"Вы уже зарегистрировались как {registered_name}.", reply_markup=types.ReplyKeyboardRemove())
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
                bot.send_message(chat_id, f"Вы успешно зарегистрировались как {selected_name}.", reply_markup=types.ReplyKeyboardRemove())
                bot.send_message(chat_id, "Пожалуйста, отправьте ваше фото:")

                # Обновляем словарь fio_chatid_dict
                fio_chatid_dict[selected_name] = str(chat_id)
            else:
                bot.send_message(chat_id, "Не удалось найти ваше имя в таблице.")
    elif call.data == "confirm_no":
        # Если пользователь отменил выбор, предлагаем выбрать снова
        bot.send_message(chat_id, "Пожалуйста, выберите ФИО снова с помощью команды /start")
        del user_names[chat_id]  # Очищаем сохраненное имя для пользователя



# Обработчик для получения фото и сохранения file_id в 2-й столбец
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    chat_id = message.chat.id

    # Проверяем, зарегистрирован ли пользователь и подтвердил ли он ФИО
    if chat_id in user_names and isinstance(user_names[chat_id], dict):
        # Получаем file_id фото
        file_id = message.photo[-1].file_id

        # Получаем все chat_id из 3 столбца
        ids_in_sheet = worksheet.col_values(3)[1:]  # Пропускаем заголовок

        # Ищем строку с именем
        found_row = None
        for index, id in enumerate(ids_in_sheet):
            if str(id) == str(chat_id):
                found_row = index + 2  # +2 из-за пропуска заголовка

        if found_row:
            worksheet.update_cell(found_row, 2, file_id)  # Записываем file_id в 2 столбец
            bot.send_message(chat_id, "Фото успешно сохранено! Регистрация завершена.")
    else:
        bot.send_message(chat_id, "Пожалуйста, сначала зарегистрируйтесь с помощью команды /start.")