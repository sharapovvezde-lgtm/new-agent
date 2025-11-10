# Используем официальный образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем libmagic, необходимый для python-magic
RUN apt-get update && apt-get install -y libmagic1 && rm -rf /var/lib/apt/lists/*

# Копируем код приложения
COPY ./app /app
COPY promt_for_llm .

# Создаем пользователя без root-прав
RUN useradd -ms /bin/bash appuser

# Устанавливаем владельца для директории приложения
RUN chown -R appuser:appuser /app

# Переключаемся на нового пользователя
USER appuser

# Открываем порт
EXPOSE 8000

# Запускаем приложение
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
