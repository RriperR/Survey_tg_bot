# Используем официальный образ Python
FROM python:3.13-alpine

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

# Меняем рабочую директорию на /code/app
WORKDIR /code/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/code/app"

# Указываем команду запуска
CMD ["python", "bot.py"]