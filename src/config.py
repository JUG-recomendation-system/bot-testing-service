import os
from pathlib import Path

# --- КОНФИГУРАЦИЯ ---
# Замени эти данные на свои с my.telegram.org
API_ID_RAW = os.getenv("TELEGRAM_API_ID")
API_ID = int(API_ID_RAW) if API_ID_RAW else None
API_HASH = os.getenv("TELEGRAM_API_HASH")

# Имя бота, которого тестируем
BOT_USERNAME = '@jugru_conf_bot'

# Пути к файлам
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / "logs"
SESSION_DIR = BASE_DIR / "sessions"
SCENARIO_FILE = BASE_DIR / "scenarios.csv"

# Создаем папки
LOG_DIR.mkdir(exist_ok=True)
SESSION_DIR.mkdir(exist_ok=True)

SESSION_FILE = SESSION_DIR / "tester.session"
