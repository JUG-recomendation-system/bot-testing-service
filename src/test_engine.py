import logging
import asyncio
import re
import random
import pandas as pd
from telethon import TelegramClient
from src.config import API_ID, API_HASH, BOT_USERNAME, SESSION_FILE, SCENARIO_FILE, LOG_DIR

# Настройка логирования
logger = logging.getLogger("TestEngine")
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

def setup_file_logging():
    log_file = LOG_DIR / "test_run.log"
    file_handler = logging.FileHandler(log_file, mode='w', encoding="utf-8")
    file_handler.setFormatter(formatter)
    if logger.hasHandlers():
        logger.handlers.clear()
    logger.addHandler(file_handler)
    return log_file

class BotTester:
    def __init__(self):
        self.client = None
        self.last_bot_response = "" 

    async def start_client(self):
        self.client = TelegramClient(str(SESSION_FILE), API_ID, API_HASH)
        await self.client.connect()
        if not await self.client.is_user_authorized():
            raise Exception("Нужна авторизация! Запустите generate_session.py")

    def smart_compare(self, expected, actual):
        """Умное сравнение: игнорирует регистр и поддерживает плейсхолдеры <...>"""
        if not expected or pd.isna(expected): return True
        expected, actual = str(expected).strip().lower(), str(actual).strip().lower()
        
        # Заменяем <любой текст> на .* для регулярного выражения
        pattern = re.escape(expected).replace(r'\<', '<').replace(r'\>', '>')
        pattern = re.sub(r'<.*?>', r'.*', pattern)
        return re.search(pattern, actual, re.DOTALL) is not None

    async def run_scenario(self, scenario_name, steps_df):
        logger.info(f"=== ЗАПУСК: {scenario_name} ===")
        steps = steps_df.to_dict('records')
        i = 0
        
        async with self.client.conversation(BOT_USERNAME, timeout=20) as conv:
            while i < len(steps):
                row = steps[i]
                action = str(row.get('Действие юзера', '')).strip()
                expected = row.get('Ответ бота', '')
                error_msg = str(row.get('Как запишем ошибку', 'Ошибка'))
                step_id = row.get('Шаги', i+1)

                try:
                    # Логика динамического цикла UNTIL_REPLY
                    if action.startswith("UNTIL_REPLY"):
                        match = re.search(r'UNTIL_REPLY\s+(\d+)\s+["\'](.*?)["\']', action)
                        if match:
                            target_step_id = int(match.group(1))
                            trigger_text = match.group(2)
                            
                            # Если триггера НЕТ в последнем ответе бота — прыгаем назад
                            if not self.smart_compare(trigger_text, self.last_bot_response):
                                logger.info(f"🔄 Повтор: Триггер '{trigger_text}' не найден. Прыжок на шаг {target_step_id}")
                                target_idx = next((idx for idx, s in enumerate(steps) if s['Шаги'] == target_step_id), None)
                                if target_idx is not None:
                                    i = target_idx
                                    continue
                            else:
                                logger.info(f"🎯 Условие выхода '{trigger_text}' выполнено.")
                                i += 1
                                continue

                    # Выполнение обычного шага
                    logger.info(f"👉 Шаг {step_id}: {action[:50]}")
                    
                    if action.startswith('/'):
                        await conv.send_message(action)
                    elif "Нажимает" in action:
                        btn_name = re.search(r'["\'](.*?)["\']', action).group(1)
                        # Ждем сообщение с кнопками (если оно еще не пришло)
                        msg = await conv.get_response()
                        if msg.buttons:
                            found = False
                            for row_btns in msg.buttons:
                                for btn in row_btns:
                                    if btn_name.lower() in btn.text.lower():
                                        await btn.click()
                                        found = True
                                        break
                            if not found:
                                logger.error(f"❌ {error_msg}. Кнопка '{btn_name}' не найдена.")
                                return False
                        else:
                            logger.error(f"❌ {error_msg}. В ответе нет кнопок.")
                            return False
                    else:
                        await conv.send_message(action)

                    # Получаем и сохраняем ответ бота
                    resp = await conv.get_response()
                    self.last_bot_response = resp.text
                    
                    # Проверяем ответ, если он задан в CSV
                    if expected and not pd.isna(expected):
                        if not self.smart_compare(expected, self.last_bot_response):
                            logger.error(f"❌ {error_msg}")
                            return False
                    
                    i += 1
                    await asyncio.sleep(1)

                except Exception as e:
                    logger.error(f"💥 Ошибка на шаге {step_id}: {e}")
                    return False
        return True