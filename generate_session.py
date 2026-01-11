import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient, errors

# --- ИНСТРУКЦИЯ ---
# 1. Запустите скрипт: python generate_session.py
# 2. Введите номер (для Test DC 2: 9996621111)
# 3. Введите код (для Test DC 2: 22222)
# 4. Если приглашение ">>" не появилось через 5 секунд, нажмите Enter.

BASE_DIR = Path(__file__).parent.resolve()
ENV_PATH = BASE_DIR / '.env'
SESSION_DIR = BASE_DIR / 'sessions'
SESSION_FILE = SESSION_DIR / 'tester.session'

load_dotenv(dotenv_path=ENV_PATH)

API_ID = os.getenv("TELEGRAM_API_ID") or os.getenv("API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH") or os.getenv("API_HASH")

# Настройки из вашего примера или дефолты
CONNECT_TIMEOUT = int(os.getenv("TELEGRAM_CONNECT_TIMEOUT", "20"))
CONNECTION_RETRIES = int(os.getenv("TELEGRAM_CONNECTION_RETRIES", "5"))

# Параметры Test DC
USE_TEST_DC = True # Переключите в False для реального номера

SESSION_DIR.mkdir(parents=True, exist_ok=True)

async def main():
    print(f"\n--- Создание сессии для Telegram ---", flush=True)
    
    if not API_ID or not API_HASH:
        print("❌ ОШИБКА: Проверьте API_ID и API_HASH в .env", flush=True)
        return

    client = TelegramClient(
        str(SESSION_FILE), 
        int(API_ID), 
        API_HASH,
        connection_retries=CONNECTION_RETRIES,
        retry_delay=2
    )
    
    if USE_TEST_DC:
        # Принудительно ставим DC 2 (самый стабильный тестовый)
        print("📡 Настройка на Test DC 2...", flush=True)
        client.session.set_dc(2, '149.154.167.40', 443)

    print("⏳ Соединение с сервером...", flush=True)
    try:
        await asyncio.wait_for(client.connect(), timeout=CONNECT_TIMEOUT)
    except Exception as e:
        print(f"❌ Не удалось подключиться: {e}", flush=True)
        return

    if await client.is_user_authorized():
        print("✅ Вы уже авторизованы! Файл сессии готов.", flush=True)
        await client.disconnect()
        return

    print("\n" + "="*40, flush=True)
    print("ШАГ 1: Введите номер телефона", flush=True)
    if USE_TEST_DC:
        print("Подсказка: используйте 9996621111", flush=True)
    print("="*40, flush=True)
    
    # Небольшая пауза для корректной отрисовки в терминалах Anaconda
    await asyncio.sleep(0.5)
    
    print("Номер телефона >> ", end='', flush=True)
    phone = sys.stdin.readline().strip()

    if not phone:
        # Если readline вернул пустоту, пробуем обычный input как запасной вариант
        phone = input().strip()

    if not phone:
        print("❌ Номер не введен. Прерывание.", flush=True)
        return

    try:
        print(f"\n📤 Запрашиваем код для {phone}...", flush=True)
        await client.send_code_request(phone)
        
        print("\n" + "="*40, flush=True)
        print("ШАГ 2: Введите код подтверждения", flush=True)
        if USE_TEST_DC:
            print(f"Подсказка: для DC 2 код всегда 22222", flush=True)
        print("="*40, flush=True)
        
        print("Код подтверждения >> ", end='', flush=True)
        code = sys.stdin.readline().strip()
        if not code:
            code = input().strip()
        
        # Завершаем авторизацию
        await client.sign_in(phone, code)
        print("\n✅ УСПЕХ! Сессия сохранена в /sessions/tester.session", flush=True)
        
    except errors.SessionPasswordNeededError:
        print("\n🔐 Требуется пароль 2FA:", flush=True)
        print("Пароль >> ", end='', flush=True)
        pw = sys.stdin.readline().strip()
        if not pw: pw = input().strip()
        await client.sign_in(password=pw)
        print("\n✅ УСПЕХ! Авторизация по 2FA пройдена.", flush=True)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}", flush=True)
    finally:
        await client.disconnect()

if __name__ == '__main__':
    # Фикс для корректной работы ввода/вывода в Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")