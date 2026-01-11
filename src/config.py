import os
from pathlib import Path

# --- КОНФИГУРАЦИЯ ---
# Замени эти данные на свои с my.telegram.org
API_ID_RAW = os.getenv("TELEGRAM_API_ID")
API_ID = int(API_ID_RAW) if API_ID_RAW else None
API_HASH = os.getenv("TELEGRAM_API_HASH")
CONNECT_TIMEOUT = int(os.getenv("TELEGRAM_CONNECT_TIMEOUT", "20"))
REQUEST_TIMEOUT = int(os.getenv("TELEGRAM_REQUEST_TIMEOUT", "10"))
CONNECTION_RETRIES = int(os.getenv("TELEGRAM_CONNECTION_RETRIES", "2"))
RETRY_DELAY = float(os.getenv("TELEGRAM_RETRY_DELAY", "1"))

DC_ID_RAW = os.getenv("TELEGRAM_DC_ID")
DC_IP = os.getenv("TELEGRAM_DC_IP")
DC_PORT_RAW = os.getenv("TELEGRAM_DC_PORT")
TELEGRAM_DC = (
    (int(DC_ID_RAW), DC_IP, int(DC_PORT_RAW))
    if DC_ID_RAW and DC_IP and DC_PORT_RAW
    else None
)

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
