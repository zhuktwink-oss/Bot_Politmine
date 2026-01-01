FROM python:3.11-slim

WORKDIR /app

# Копируем список зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь код проекта в рабочую директорию контейнера
COPY . .

# Указываем, что база данных будет храниться в смонтированном томе /app/data
ENV DATABASE_PATH=/app/data/bot_database.db

# Команда для запуска приложения
CMD ["python", "bot_webhook.py"]