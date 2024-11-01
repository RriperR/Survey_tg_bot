# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем часовой пояс
RUN ln -sf /usr/share/zoneinfo/Europe/Moscow /etc/localtime && \
    echo "Europe/Moscow" > /etc/timezone

ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию
WORKDIR /code

# Копируем файл требований и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Меняем рабочую директорию на /code/app
WORKDIR /code/app

# Указываем команду запуска
CMD ["python", "bot.py"]