import asyncio
import os
from telethon import TelegramClient
from src.config import API_ID, API_HASH, SESSION_FILE, SESSION_DIR

# Убедимся, что папка существует
SESSION_DIR.mkdir(parents=True, exist_ok=True)

async def main():
    print(f"--- Создание сессии для Telegram ---")
    print(f"Путь к файлу: {SESSION_FILE}")
    print(f"API ID: {API_ID}")
    
    # Инициализируем клиент
    # При первом запуске он попросит ввести номер телефона и код из Telegram в консоли
    client = TelegramClient(str(SESSION_FILE), API_ID, API_HASH)
    
    await client.start()
    
    print("------------------------------------------------")
    print("УСПЕХ! Файл сессии создан.")
    print("Теперь можно запускать основной сервис.")
    print("------------------------------------------------")
    
    await client.disconnect()

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())