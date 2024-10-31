# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем часовой пояс
RUN ln -sf /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    echo "Europe/Moscow" > /etc/timezone

# Устанавливаем рабочую директорию
WORKDIR /code

# Копируем файл требований и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Указываем команду запуска
CMD ["python", "./app/bot.py"]