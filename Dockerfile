# Используем официальный образ Python
FROM python:3.9-slim

# Устанавливаем переменную окружения для временной зоны
ENV TZ=Europe/Moscow

# Устанавливаем tzdata и настраиваем временную зону
RUN apt-get update && apt-get install -y tzdata && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл требований и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY . .

# Указываем команду запуска
CMD ["python", "bot.py"]