# Используем официальный образ Python
FROM python:3.9-slim

# Установим необходимые системные зависимости
RUN apt-get update && apt-get install -y \
    default-libmysqlclient-dev build-essential

# Устанавливаем зависимости через pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект в контейнер
COPY . /app
WORKDIR /app

# Команда для запуска бота
CMD ["python", "main.py"]