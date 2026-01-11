import asyncio
import os
import re
import sys
from getpass import getpass
from pathlib import Path

from dotenv import load_dotenv
from pyrogram import Client
from pyrogram.errors import (
    PhoneCodeEmpty,
    PhoneCodeExpired,
    PhoneCodeInvalid,
    PhoneNumberBanned,
    PhoneNumberInvalid,
    SessionPasswordNeeded,
)

# --- ИНСТРУКЦИЯ ---
# 1. Запустите скрипт: python generate_session.py
# 2. Введите номер (для Test DC: 9996612023)
# 3. Введите код (для Test DC: 11111 или вычислится из номера)
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


def get_confirmation_code(phone: str) -> str | None:
    match = re.match(r"99966(?P<dc>[0-3]{1})(?P<rand_part>[0-9]{4})", phone)
    if not match:
        return None
    return match.group("dc") * 5

SESSION_DIR.mkdir(parents=True, exist_ok=True)

def print_header(title: str) -> None:
    print("\n" + "=" * 40, flush=True)
    print(title, flush=True)
    print("=" * 40, flush=True)

def get_input(prompt: str) -> str:
    print(prompt, end="", flush=True)
    value = sys.stdin.readline().strip()
    if not value:
        value = input().strip()
    return value

async def main():
    print("\n--- Создание сессии для Telegram ---", flush=True)

    if not API_ID or not API_HASH:
        print("❌ ОШИБКА: Проверьте API_ID и API_HASH в .env", flush=True)
        return

    client = None
    phone = None
    code = None
    password = None

    print_header("ШАГ 1: Введите номер телефона")
    if USE_TEST_DC:
        print(
            f"Подсказка: тестовые номера выглядят как 99966XYYYY (например {DEFAULT_TEST_PHONE}).",
            flush=True,
        )

    await asyncio.sleep(0.5)

    phone = get_input("Номер телефона >> ")
    if not phone and USE_TEST_DC:
        phone = DEFAULT_TEST_PHONE
        print(phone, flush=True)

    if not phone:
        print("❌ Номер не введен. Прерывание.", flush=True)
        return

    print_header("ШАГ 2: Введите код подтверждения")
    if USE_TEST_DC:
        print(
            "Подсказка: код для Test DC вычисляется как X*5, где X — цифра после 99966.",
            flush=True,
        )

    code = get_input("Код подтверждения >> ")

    client = Client(
        "tester",
        api_id=int(API_ID),
        api_hash=API_HASH,
        test_mode=USE_TEST_DC,
        in_memory=False,
        workdir=str(SESSION_DIR),
    )

    print("⏳ Соединение с сервером...", flush=True)
    try:
        await asyncio.wait_for(client.connect(), timeout=CONNECT_TIMEOUT)
        sent_code = await client.send_code(phone)
        if not code and USE_TEST_DC:
            code = get_confirmation_code(phone)
            if code:
                print(f"Автокод для Test DC: {code}", flush=True)
        if not code:
            code = get_input("Код подтверждения >> ")
        if not code:
            print("❌ Код не введен. Прерывание.", flush=True)
            return

        await client.sign_in(
            phone_number=phone,
            phone_code_hash=sent_code.phone_code_hash,
            phone_code=code,
        )
        print(
            f"\n✅ УСПЕХ! Сессия сохранена в {SESSION_FILE}",
            flush=True,
        )
    except SessionPasswordNeeded:
        print("\n🔐 Требуется пароль 2FA.", flush=True)
        password = getpass("Пароль >> ")
        if not password:
            print("❌ Пароль не введен. Прерывание.", flush=True)
            return
        try:
            await client.check_password(password=password)
            print(
                f"\n✅ УСПЕХ! Сессия сохранена в {SESSION_FILE}",
                flush=True,
            )
        except Exception as inner_exc:
            print(f"\n❌ Ошибка 2FA: {inner_exc}", flush=True)
    except PhoneNumberInvalid:
        print("\n❌ Неверный номер телефона.", flush=True)
    except PhoneNumberBanned:
        print("\n❌ Номер телефона заблокирован в Telegram.", flush=True)
    except PhoneCodeInvalid:
        print("\n❌ Неверный код подтверждения.", flush=True)
    except PhoneCodeExpired:
        print("\n❌ Код подтверждения истек. Запустите скрипт заново.", flush=True)
    except PhoneCodeEmpty:
        print("\n❌ Код подтверждения не введен.", flush=True)
    except Exception as exc:
        print(f"\n❌ Ошибка: {exc}", flush=True)
    finally:
        if client and client.is_connected:
            await client.disconnect()

if __name__ == '__main__':
    # Фикс для корректной работы ввода/вывода в Windows
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
