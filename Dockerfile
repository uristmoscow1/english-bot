# Базовый образ Python 3.11
FROM python:3.11-alpine

# Рабочая папка
WORKDIR /app

# Установка системных зависимостей
RUN apk add --no-cache gcc musl-dev

# Копируем и ставим пакеты
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код
COPY bot.py .

# Порт
EXPOSE 10000

# Запуск
CMD ["gunicorn", "bot:app", "-b", "0.0.0.0:10000"]
