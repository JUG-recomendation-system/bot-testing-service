import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

import pandas as pd
import pytest

from src.app import BotTester


@dataclass
class FakeButton:
    text: str

    async def click(self) -> None:
        return None


@dataclass
class FakeMessage:
    text: str
    buttons: list[list[FakeButton]] | None = None


class FakeConversation:
    def __init__(self, responses: list[FakeMessage]):
        self._responses = list(responses)
        self.sent_messages: list[str] = []

    async def send_message(self, message: str) -> None:
        self.sent_messages.append(message)

    async def get_response(self) -> FakeMessage:
        if not self._responses:
            raise asyncio.TimeoutError("No more fake responses")
        return self._responses.pop(0)


class FakeConversationAdapter:
    def __init__(self, responses: list[FakeMessage]):
        self.responses = responses

    async def connect(self) -> None:
        return None

    async def disconnect(self) -> None:
        return None

    async def is_user_authorized(self) -> bool:
        return True

    @asynccontextmanager
    async def conversation(self, bot_username: str, timeout: int = 15) -> Any:
        yield FakeConversation(self.responses)


@pytest.fixture
def happy_path_steps() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Сценарий": "happy",
                "Шаги": 1,
                "Действие юзера": "/start",
                "Ответ бота": "Welcome",
                "Как запишем ошибку": "No welcome",
            },
            {
                "Сценарий": "happy",
                "Шаги": 2,
                "Действие юзера": "Нажимает кнопку 'Go'",
                "Ответ бота": "Next",
                "Как запишем ошибку": "Button failed",
            },
        ]
    )


@pytest.fixture
def negative_steps() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Сценарий": "negative",
                "Шаги": 1,
                "Действие юзера": "/start",
                "Ответ бота": "Expected",
                "Как запишем ошибку": "Mismatch",
            }
        ]
    )


@pytest.fixture
def repeat_steps() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Сценарий": "repeat",
                "Шаги": 1,
                "Действие юзера": "Ping",
                "Ответ бота": "Pong",
                "Как запишем ошибку": "Repeat mismatch",
            },
            {
                "Сценарий": "repeat",
                "Шаги": 2,
                "Действие юзера": "REPEAT 1-1 2",
                "Ответ бота": "",
                "Как запишем ошибку": "Repeat failed",
            },
            {
                "Сценарий": "repeat",
                "Шаги": 3,
                "Действие юзера": "Done",
                "Ответ бота": "Ok",
                "Как запишем ошибку": "Done mismatch",
            },
        ]
    )


@pytest.fixture
def until_reply_steps() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Сценарий": "until",
                "Шаги": 1,
                "Действие юзера": "Ping",
                "Ответ бота": "Wait",
                "Как запишем ошибку": "Wait mismatch",
            },
            {
                "Сценарий": "until",
                "Шаги": 2,
                "Действие юзера": "UNTIL_REPLY 1 'Ready'",
                "Ответ бота": "",
                "Как запишем ошибку": "Trigger failed",
            },
        ]
    )


@pytest.mark.asyncio
async def test_start_and_button_flow(happy_path_steps: pd.DataFrame) -> None:
    responses = [
        FakeMessage("Welcome", buttons=[[FakeButton("Go")]]),
        FakeMessage("Next"),
    ]
    tester = BotTester(conversation_adapter=FakeConversationAdapter(responses))

    assert await tester.run_scenario("happy", happy_path_steps) is True


@pytest.mark.asyncio
async def test_repeat_flow(repeat_steps: pd.DataFrame) -> None:
    responses = [
        FakeMessage("Pong"),
        FakeMessage("Pong"),
        FakeMessage("Ok"),
    ]
    tester = BotTester(conversation_adapter=FakeConversationAdapter(responses))

    assert await tester.run_scenario("repeat", repeat_steps) is True


@pytest.mark.asyncio
async def test_until_reply_flow(until_reply_steps: pd.DataFrame) -> None:
    responses = [
        FakeMessage("Wait"),
        FakeMessage("Ready"),
    ]
    tester = BotTester(conversation_adapter=FakeConversationAdapter(responses))

    assert await tester.run_scenario("until", until_reply_steps) is True


@pytest.mark.asyncio
async def test_negative_scenario(negative_steps: pd.DataFrame) -> None:
    responses = [FakeMessage("Actual")]
    tester = BotTester(conversation_adapter=FakeConversationAdapter(responses))

    assert await tester.run_scenario("negative", negative_steps) is False
