FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем зависимости Python
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# Копируем проект
COPY . .

# Указываем PYTHONPATH, чтобы Python всегда видел папку /app как корень для импортов
ENV PYTHONPATH=/app
# Отключаем буферизацию логов, чтобы видеть ошибки мгновенно
ENV PYTHONUNBUFFERED=1

RUN mkdir -p logs sessions

EXPOSE 8000

# Используем прямой вызов uvicorn. 
# Если файл лежит в src/app.py, то путь src.app:app верный при условии правильного PYTHONPATH
CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]