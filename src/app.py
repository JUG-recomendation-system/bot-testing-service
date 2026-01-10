import logging
import asyncio
import re
import random
import pandas as pd
from telethon import TelegramClient
from src.config import API_ID, API_HASH, BOT_USERNAME, SESSION_FILE, SCENARIO_FILE, LOG_DIR

# --- НАСТРОЙКА ЛОГГЕРА ---
logger = logging.getLogger("TestEngine")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")


def setup_file_logging():
    """Очищает старые логи и готовит файл для новой сессии тестирования."""
    log_file = LOG_DIR / "test_run.log"
    file_handler = logging.FileHandler(log_file, mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)

    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(file_handler)
    return log_file


class BotTester:
    def __init__(self):
        self.client = None
        self.last_bot_response = ""  # последний текст от бота (для UNTIL_REPLY)

    async def start_client(self):
        """Подключение к Telegram."""
        self.client = TelegramClient(str(SESSION_FILE), API_ID, API_HASH)
        await self.client.connect()

        if not await self.client.is_user_authorized():
            logger.error("ОШИБКА: Клиент не авторизован! Запустите сначала generate_session.py")
            raise Exception("Client not authorized")

    async def stop_client(self):
        """Корректно отключаемся от Telegram."""
        if self.client:
            await self.client.disconnect()

    def load_scenarios(self):
        """Загрузка CSV и группировка по 'Сценарий'."""
        try:
            df = pd.read_csv(SCENARIO_FILE)
            df = df.dropna(subset=["Сценарий"])
            return df.groupby("Сценарий")
        except Exception as e:
            logger.error(f"Критическая ошибка чтения CSV: {e}")
            return {}

    def smart_compare(self, expected, actual):
        """
        Сравнение текстов с поддержкой шаблонов <...> (как wildcard) и без учета регистра.
        Пример expected: "Привет, <username>!" матчится с "Привет, Юля!"
        """
        if not expected or pd.isna(expected):
            return True

        expected = str(expected).strip()
        actual = str(actual).strip()

        # Приводим к lower (логика v2/v3)
        expected_l = expected.lower()
        actual_l = actual.lower()

        if expected_l == actual_l:
            return True

        # Делаем regex из expected, где <...> -> .*
        pattern = re.escape(expected_l).replace(r"\<", "<").replace(r"\>", ">")
        pattern = re.sub(r"<.*?>", r".*", pattern)
        return re.search(pattern, actual_l, re.DOTALL) is not None

    async def run_scenario(self, scenario_name, steps_df):
        """
        Выполняет сценарий. Поддерживает:
        - REPEAT a-b n (как в v0)
        - UNTIL_REPLY step "text" (как в v1+)
        """
        logger.info(f"=== ЗАПУСК СЦЕНАРИЯ: {scenario_name} ===")

        steps = steps_df.to_dict("records")
        i = 0

        # Счетчики циклов REPEAT: {index_of_repeat_row: current_iter}
        repeat_counters = {}

        async with self.client.conversation(BOT_USERNAME, timeout=15) as conv:
            while i < len(steps):
                row = steps[i]
                step_num = row.get("Шаги", i + 1)
                user_action = str(row.get("Действие юзера", "")).strip()
                expected_reply = row.get("Ответ бота", "")
                error_log_msg = str(row.get("Как запишем ошибку", f"Ошибка на шаге {step_num}"))

                try:
                    # -----------------------------
                    # 1) ДИНАМИЧЕСКИЙ ЦИКЛ UNTIL_REPLY
                    # Формат: UNTIL_REPLY 6 "Твой маршрут сформирован"
                    # -----------------------------
                    if user_action.startswith("UNTIL_REPLY"):
                        match = re.search(r'UNTIL_REPLY\s+(\d+)\s+["\'](.*?)["\']', user_action)
                        if not match:
                            logger.warning(f"⚠️ Неверный формат UNTIL_REPLY на шаге {step_num}. Пропускаю.")
                            i += 1
                            continue

                        target_step_num = int(match.group(1))
                        trigger_text = match.group(2)

                        if self.smart_compare(trigger_text, self.last_bot_response):
                            logger.info(f"🎯 ТРИГГЕР НАЙДЕН: '{trigger_text}'. Выходим из цикла.")
                            i += 1
                            continue

                        logger.info(f"🔄 Триггер '{trigger_text}' не найден. Прыгаем назад на шаг {target_step_num}")
                        target_index = next(
                            (idx for idx, s in enumerate(steps) if s.get("Шаги") == target_step_num),
                            None,
                        )
                        if target_index is None:
                            logger.error(f"❌ Ошибка: Шаг {target_step_num} не найден.")
                            return False
                        i = target_index
                        continue

                    # -----------------------------
                    # 2) СТАТИЧЕСКИЙ ЦИКЛ REPEAT (как в v0)
                    # Формат: REPEAT 6-9 3
                    # -----------------------------
                    if user_action.startswith("REPEAT"):
                        match = re.search(r"REPEAT\s+(\d+)-(\d+)\s+(\d+)", user_action)
                        if not match:
                            logger.warning(f"⚠️ Непонятный формат REPEAT на шаге {step_num}. Пропускаю.")
                            i += 1
                            continue

                        start_step_num = int(match.group(1))
                        # end_step_num = int(match.group(2))  # сейчас не используется
                        count = int(match.group(3))

                        current_iter = repeat_counters.get(i, 0)
                        if current_iter < count:
                            logger.info(
                                f"🔄 ЦИКЛ REPEAT: Повтор с шага {start_step_num}. Итерация {current_iter + 1} из {count}"
                            )
                            repeat_counters[i] = current_iter + 1

                            target_index = next(
                                (idx for idx, s in enumerate(steps) if s.get("Шаги") == start_step_num),
                                None,
                            )
                            if target_index is None:
                                logger.error(f"❌ Ошибка цикла: Не найден шаг номер {start_step_num}")
                                return False

                            i = target_index
                            continue
                        else:
                            logger.info("✅ ЦИКЛ REPEAT ЗАВЕРШЕН. Идем дальше.")
                            repeat_counters[i] = 0
                            i += 1
                            continue

                    # -----------------------------
                    # 3) ОБЫЧНЫЕ ДЕЙСТВИЯ
                    # -----------------------------
                    logger.info(f"👉 Шаг {step_num}: '{user_action[:60]}...'")

                    # 3.1 Случайный выбор сообщения
                    if "Отправляет одно из сообщений" in user_action or "Отправляет одно из" in user_action:
                        lines = user_action.split("\n")
                        options = [l for l in lines if l.strip() and not l.strip().startswith("Отправляет")]
                        if options:
                            chosen = random.choice(options).strip()
                            chosen = re.sub(r"^\d+\.\s*", "", chosen)  # убрать нумерацию "1. "
                            # Защита как в v0: если в варианте плейсхолдер вида <...>, отправляем безопасную строку
                            if "<" in chosen and ">" in chosen:
                                chosen = "Тестировщик"
                            logger.info(f"🎲 Выбрано: {chosen}")
                            await conv.send_message(chosen)
                        else:
                            await conv.send_message("Test message")

                    # 3.2 Команды (/start)
                    elif user_action.startswith("/"):
                        await conv.send_message(user_action)

                    # 3.3 Кнопки
                    elif ("Нажимает" in user_action) or ("кнопку" in user_action):
                        # Ждем сообщение, где должны быть кнопки
                        last_msg = await conv.get_response()
                        self.last_bot_response = last_msg.text or ""

                        m = re.search(r'["\'](.*?)["\']', user_action)
                        btn_text = (m.group(1) if m else "").strip()
                        if not btn_text:
                            logger.error(f"❌ {error_log_msg}. Не найден текст кнопки в кавычках.")
                            return False

                        btn_found = False
                        if last_msg.buttons:
                            for row_btns in last_msg.buttons:
                                for btn in row_btns:
                                    if btn_text.lower() in (btn.text or "").lower():
                                        await btn.click()
                                        btn_found = True
                                        logger.info(f"🔘 Нажата: {btn.text}")
                                        break
                                if btn_found:
                                    break

                        if not btn_found:
                            logger.error(f"❌ {error_log_msg}. Кнопка '{btn_text}' не найдена.")
                            return False

                    # 3.4 Просто текст
                    else:
                        await conv.send_message(user_action)

                    # -----------------------------
                    # 4) ПРОВЕРКА ОТВЕТА
                    # -----------------------------
                    if expected_reply and not pd.isna(expected_reply):
                        response = await conv.get_response()
                        self.last_bot_response = response.text or ""
                        if self.smart_compare(expected_reply, self.last_bot_response):
                            logger.info("👌 Ответ корректен.")
                        else:
                            logger.error(f"❌ {error_log_msg}")
                            logger.info(f"   Ждали: {expected_reply}")
                            logger.info(f"   Получили: {self.last_bot_response[:200]}...")
                            return False
                    else:
                        # Если не ждем конкретного текста — не блокируемся ожиданием.
                        await asyncio.sleep(1)

                    i += 1

                except asyncio.TimeoutError:
                    logger.error(f"⏳ Таймаут на шаге {step_num}")
                    return False
                except Exception as e:
                    logger.exception(f"💥 Ошибка на шаге {step_num}: {e}")
                    return False

        logger.info("🏁 Сценарий завершен.")
        return True


tester = BotTester()


async def run_tests(specific_scenario=None):
    setup_file_logging()
    try:
        await tester.start_client()
        grouped = tester.load_scenarios()

        if specific_scenario:
            # grouped может быть {} если CSV не прочитался
            if hasattr(grouped, "groups") and specific_scenario in grouped.groups:
                await tester.run_scenario(specific_scenario, grouped.get_group(specific_scenario))
            else:
                logger.error(f"Сценарий '{specific_scenario}' не найден.")
        else:
            if hasattr(grouped, "__iter__"):
                for name, steps in grouped:
                    await tester.run_scenario(name, steps)
            else:
                logger.error("Не удалось загрузить сценарии (grouped пустой).")
    except Exception as e:
        logger.error(f"Global Error: {e}")
    finally:
        await tester.stop_client()
