import asyncio
import os
import sys
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv
from pyrogram import Client

# --- ИНСТРУКЦИЯ ---
# 1. Запустите скрипт: python generate_session.py
# 2. Введите номер (для Test DC: 9996612023)
# 3. Введите код (для Test DC: 11111)
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

# Параметры Test DC
USE_TEST_DC = True  # Переключите в False для реального номера
DEFAULT_TEST_PHONE = "99966" + "1" + "2023"
DEFAULT_TEST_CODE = "1" * 5

SESSION_DIR.mkdir(parents=True, exist_ok=True)

async def main():
    print("\n--- Создание сессии для Telegram ---", flush=True)

    if not API_ID or not API_HASH:
        print("❌ ОШИБКА: Проверьте API_ID и API_HASH в .env", flush=True)
        return

    client = None
    phone = None
    code = None
    password = None

    print("\n" + "=" * 40, flush=True)
    print("ШАГ 1: Введите номер телефона", flush=True)
    if USE_TEST_DC:
        print(f"Подсказка: используйте {DEFAULT_TEST_PHONE}", flush=True)
    print("=" * 40, flush=True)

    await asyncio.sleep(0.5)

    print("Номер телефона >> ", end="", flush=True)
    phone = sys.stdin.readline().strip()
    if not phone and USE_TEST_DC:
        phone = DEFAULT_TEST_PHONE
        print(phone, flush=True)
    if not phone:
        phone = input().strip()

    if not phone:
        print("❌ Номер не введен. Прерывание.", flush=True)
        return

    print("\n" + "=" * 40, flush=True)
    print("ШАГ 2: Введите код подтверждения", flush=True)
    if USE_TEST_DC:
        print(f"Подсказка: для Test DC код всегда {DEFAULT_TEST_CODE}", flush=True)
    print("=" * 40, flush=True)

    print("Код подтверждения >> ", end="", flush=True)
    code = sys.stdin.readline().strip()
    if not code and USE_TEST_DC:
        code = DEFAULT_TEST_CODE
        print(code, flush=True)
    if not code:
        code = input().strip()

    if not code:
        print("❌ Код не введен. Прерывание.", flush=True)
        return

    client = Client(
        "tester",
        api_id=int(API_ID),
        api_hash=API_HASH,
        test_mode=USE_TEST_DC,
        in_memory=False,
        workdir=str(SESSION_DIR),
        phone_number=phone,
        phone_code=code,
    )

    print("⏳ Соединение с сервером...", flush=True)
    try:
        await asyncio.wait_for(client.start(password=password), timeout=CONNECT_TIMEOUT)
        print(
            f"\n✅ УСПЕХ! Сессия сохранена в {SESSION_FILE}",
            flush=True,
        )
    except Exception as exc:
        if "password" in str(exc).lower():
            print("\n🔐 Требуется пароль 2FA:", flush=True)
            password = getpass("Пароль >> ")
            try:
                await client.start(password=password)
                print(
                    f"\n✅ УСПЕХ! Сессия сохранена в {SESSION_FILE}",
                    flush=True,
                )
            except Exception as inner_exc:
                print(f"\n❌ Ошибка: {inner_exc}", flush=True)
        else:
            print(f"\n❌ Ошибка: {exc}", flush=True)
    finally:
        if client:
            await client.stop()

if __name__ == '__main__':
    # Фикс для корректной работы ввода/вывода в Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
