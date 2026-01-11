import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient, errors

# --- НАСТРОЙКА ПУТЕЙ ---
BASE_DIR = Path(__file__).parent.resolve()
ENV_PATH = BASE_DIR / '.env'
SESSION_DIR = BASE_DIR / 'sessions'
SESSION_FILE = SESSION_DIR / 'tester.session'

load_dotenv(dotenv_path=ENV_PATH)

API_ID = os.getenv("TELEGRAM_API_ID") or os.getenv("API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH") or os.getenv("API_HASH")
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

SESSION_DIR.mkdir(parents=True, exist_ok=True)

async def main():
    print(f"--- Создание сессии для Telegram (Ручной режим) ---")
    
    if not API_ID or not API_HASH:
        print("\n❌ ОШИБКА: Не найдены ключи API в .env")
        return

    client = TelegramClient(
        str(SESSION_FILE),
        int(API_ID),
        API_HASH,
        timeout=REQUEST_TIMEOUT,
        connection_retries=CONNECTION_RETRIES,
        retry_delay=RETRY_DELAY,
    )

    if TELEGRAM_DC:
        dc_id, dc_ip, dc_port = TELEGRAM_DC
        print(f"📡 Используем тестовый DC {dc_id} ({dc_ip}:{dc_port}).")
        client.session.set_dc(dc_id, dc_ip, dc_port)
        client.session.save()

    print("⏳ Подключаемся к серверам Telegram...")
    try:
        await asyncio.wait_for(client.connect(), timeout=CONNECT_TIMEOUT)
    except asyncio.TimeoutError:
        print(
            "❌ Таймаут подключения к Telegram. "
            "Проверьте TELEGRAM_DC_* или сеть/прокси."
        )
        return

    if await client.is_user_authorized():
        print("\n✅ Сессия уже активна! Файл session валиден.")
        print("Ничего делать не нужно. Можно запускать тесты.")
        await client.disconnect()
        return

    print("\n👇 Введите ваш номер телефона в международном формате.")
    print("Пример: +79001234567")
    phone = input("Ваш телефон: ").strip()

    try:
        print(f"\n📤 Отправляем запрос кода на номер {phone}...")
        # Явная отправка запроса на код
        send_status = await client.send_code_request(phone)
        print("✅ Telegram принял запрос! Код должен прийти в приложение или СМС.")
    except errors.FloodWaitError as e:
        print(f"\n❌ ОШИБКА: Слишком много попыток. Telegram просит подождать {e.seconds} секунд.")
        return
    except errors.PhoneNumberInvalidError:
        print("\n❌ ОШИБКА: Неверный формат номера телефона. Обязательно используйте +7...")
        return
    except Exception as e:
        print(f"\n❌ Ошибка при отправке запроса: {e}")
        return
