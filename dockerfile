FROM python:3.11-slim

WORKDIR /app

# Копируем requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY . .

# Создаем необходимые директории
RUN mkdir -p static/uploads/avatars static/uploads/todos static/images templates/partials

# Запуск uvicorn
CMD ["uvicorn", "my_todo_app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]