import asyncio
from contextlib import asynccontextmanager, suppress

import pytest
from telethon import TelegramClient, events
from telethon.tl.custom.message import Message


class ReplyCollector:
    def __init__(self, client: TelegramClient, bot_username: str) -> None:
        self.client = client
        self.bot_username = bot_username
        self.collected_replies: list[Message] = []
        self.collected_exception: Exception | None = None
        self.collection_event = asyncio.Event()
        self.collection_required_amount = 0
        self._handler_registered = False

    async def collect_replies_callback(self, event: events.NewMessage.Event) -> None:
        try:
            self.collected_replies.append(event.message)
            if len(self.collected_replies) == self.collection_required_amount:
                self.collection_event.set()
        except Exception as exc:
            self.collected_exception = exc
            self.collection_event.set()

    async def collection_max_timeout_waiting(self, timeout: float) -> None:
        await asyncio.sleep(timeout)
        self.collection_event.set()

    def _register_handler(self) -> None:
        if not self._handler_registered:
            self.client.add_event_handler(
                self.collect_replies_callback,
                events.NewMessage(from_users=self.bot_username),
            )
            self._handler_registered = True

    def _unregister_handler(self) -> None:
        if self._handler_registered:
            self.client.remove_event_handler(
                self.collect_replies_callback,
                events.NewMessage(from_users=self.bot_username),
            )
            self._handler_registered = False

    @asynccontextmanager
    async def collect(self, *, amount: int, timeout: float = 2.0):
        self.collection_required_amount = amount
        self.collected_replies.clear()
        self.collected_exception = None
        self.collection_event = asyncio.Event()
        self._register_handler()

        try:
            yield self.collected_replies
        finally:
            timeout_task = asyncio.create_task(
                self.collection_max_timeout_waiting(timeout)
            )
            await self.collection_event.wait()
            timeout_task.cancel()
            with suppress(asyncio.CancelledError):
                await timeout_task
            self._unregister_handler()

            if self.collected_exception:
                raise self.collected_exception
            assert (
                len(self.collected_replies) == amount
            ), "Received unexpected messages amount."

# Данные для авторизации (получить на my.telegram.org)
API_ID = 'YOUR_API_ID'
API_HASH = 'YOUR_API_HASH'
BOT_USERNAME = '@your_cool_bot'
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
