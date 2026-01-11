import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from telethon import TelegramClient, errors

# --- ИНСТРУКЦИЯ ПОСЛЕ ЗАПУСКА ---
# 1. Если сессия создана успешно, закройте этот скрипт (Ctrl+C).
# 2. Запустите основное приложение через Docker: docker-compose up --build

# --- НАСТРОЙКА ПУТЕЙ ---
BASE_DIR = Path(__file__).parent.resolve()
ENV_PATH = BASE_DIR / '.env'
SESSION_DIR = BASE_DIR / 'sessions'
SESSION_FILE = SESSION_DIR / 'tester.session'

load_dotenv(dotenv_path=ENV_PATH)

API_ID = os.getenv("TELEGRAM_API_ID") or os.getenv("API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH") or os.getenv("API_HASH")

# РЕЖИМ ТЕСТОВОГО СЕРВЕРА
# Установите True для номеров 99966... (код 22222)
# Установите False для вашего реального номера
USE_TEST_DC = True 

SESSION_DIR.mkdir(parents=True, exist_ok=True)

async def main():
    print(f"\n--- Создание сессии для Telegram ---")
    
    if not API_ID or not API_HASH:
        print("❌ ОШИБКА: Проверьте API_ID и API_HASH в .env")
        return

    # Инициализируем клиент с таймаутами
    client = TelegramClient(
        str(SESSION_FILE), 
        int(API_ID), 
        API_HASH,
        connection_retries=5,
        retry_delay=2
    )
    
    if USE_TEST_DC:
        # Ставим DC 2 (149.154.167.40) для тестовых номеров
        client.session.set_dc(2, '149.154.167.40', 443)

    print("⏳ Соединение с сервером...")
    try:
        await client.connect()
    except Exception as e:
        print(f"❌ Не удалось подключиться: {e}")
        return

    if await client.is_user_authorized():
        print("✅ Вы уже авторизованы! Файл сессии готов.")
        await client.disconnect()
        return

    # Важно: используем flush, чтобы текст появился до ожидания ввода
    print("\nВведите номер телефона (для Test DC 2 это 9996621111):", flush=True)
    phone = input(">> ").strip()

    if not phone:
        print("❌ Номер не введен. Выход.")
        await client.disconnect()
        return

    try:
        print(f"📤 Запрос кода для {phone}...", flush=True)
        await client.send_code_request(phone)
        
        print(f"\nВведите код подтверждения (для номера {phone} это {phone[5]*5 if USE_TEST_DC else 'код из ТГ'}):", flush=True)
        code = input(">> ").strip()
        
        await client.sign_in(phone, code)
        print("\n✅ УСПЕХ! Сессия авторизована и сохранена в /sessions/tester.session")
        
    except errors.SessionPasswordNeededError:
        print("\n🔐 Требуется пароль двухфакторной аутентификации (2FA):", flush=True)
        pw = input(">> ")
        await client.sign_in(password=pw)
        print("\n✅ УСПЕХ! Сессия сохранена.")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()

if __name__ == '__main__':
    # Специальная политика для Windows, чтобы избежать зависания и ошибок Loop
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nПрервано пользователем.")
    except Exception as e:
        print(f"\nПроизошла ошибка при запуске: {e}")