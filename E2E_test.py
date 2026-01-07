import asyncio
import pytest
from telethon import TelegramClient
from telethon.tl.custom.message import Message

# Данные для авторизации (получить на my.telegram.org)
API_ID = 'YOUR_API_ID'
API_HASH = 'YOUR_API_HASH'
BOT_USERNAME = '@jugru_conf_bot'
SESSION_NAME = 'test_user_session'

@pytest.fixture(scope="session")
async def client():
    """Инициализация клиента Telegram для тестов."""
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start()
    yield client
    await client.disconnect()

@pytest.mark.asyncio
async def test_start_command(client: TelegramClient):
    """Проверка команды /start и наличия приветственного сообщения."""
    async with client.conversation(BOT_USERNAME, timeout=10) as conv:
        await conv.send_message('/start')
        response: Message = await conv.get_response()
        
        assert '/start' not in response.text
        assert len(response.text) > 0
        print(f"Лог: Бот ответил: {response.text[:50]}...")

@pytest.mark.asyncio
async def test_recommendation_scenario(client: TelegramClient):
    """Сценарий: Запрос рекомендации и проверка кнопок."""
    async with client.conversation(BOT_USERNAME, timeout=15) as conv:
        await conv.send_message('Хочу рекомендацию')
        response: Message = await conv.get_response()
        
        # Проверяем, что бот прислал инлайновые кнопки (ReplyMarkup)
        assert response.reply_markup is not None, "Бот не прислал кнопки выбора!"
        
        # Имитируем нажатие на первую кнопку (например, выбор темы)
        await response.click(0)
        follow_up = await conv.get_response()
        
        assert "Выберите" in follow_up.text or "Доклад" in follow_up.text
        print("Лог: Сценарий рекомендаций пройден успешно.")

# Для запуска: pytest tests/e2e_test.py