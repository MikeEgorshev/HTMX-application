# Базовый образ с Python (slim — лёгкий для prod)
FROM python:3.11-slim

# Устанавливаем зависимости
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Копируем код (включая под-папку my_todo_app)
COPY . .

# Запуск как модуль пакета my_todo_app.main:app
CMD ["uvicorn", "my_todo_app.main:app", "--host", "0.0.0.0", "--port", "8000"]