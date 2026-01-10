# Используем легкий образ Python
FROM python:3.10-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект внутрь контейнера
COPY . .

# Создаем папку для логов и сессий, чтобы не было ошибок прав доступа
RUN mkdir -p /app/logs /app/sessions

# Указываем команду для запуска веб-приложения
# host 0.0.0.0 делает сайт доступным снаружи контейнера
CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]