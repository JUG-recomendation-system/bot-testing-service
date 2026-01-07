import logging
import os
from pathlib import Path
from locust import HttpUser, task, between
import random

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOAD_LOG_FILE = Path(os.getenv("LOAD_LOG_FILE", LOG_DIR / "load_test.log"))

logger = logging.getLogger("load_test")
logger.setLevel(logging.INFO)
if not logger.handlers:
    file_handler = logging.FileHandler(LOAD_LOG_FILE, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.propagate = False


class BotBackendUser(HttpUser):
    """
    Имитация пользователя, который обращается напрямую к API бота 
    или к schedule-service, минуя интерфейс Telegram.
    """
    wait_time = between(1, 3) # Пауза между действиями пользователя

    @task(3)
    def get_schedule(self):
        """Имитация запроса расписания (нагрузка на presentations-crud и DB)."""
        response = self.client.get("/api/v1/schedule", name="Get Schedule")
        logger.info("Schedule response status: %s", response.status_code)

    @task(1)
    def ask_recommendation(self):
        """
        Имитация запроса рекомендации. 
        Тут проверяем связку: Bot -> Rec-Engine -> Qdrant.
        """
        payload = {
            "user_id": random.randint(1000, 9999),
            "query": "Расскажи про микросервисы"
        } 
        # Предполагаем, что у вашего сервиса есть внутренний эндпоинт для этого
        with self.client.post("/api/v1/recommend", json=payload, catch_response=True, name="Get Recommendation") as response:
            if response.status_code == 200:
                response.success()
                logger.info("Recommendation OK for user_id=%s", payload["user_id"])
            else:
                response.failure(f"Ошибка поиска: {response.status_code}")
                logger.warning(
                    "Recommendation failed for user_id=%s status=%s",
                    payload["user_id"],
                    response.status_code,
                )

# Для запуска: locust -f tests/load_test.py --host=http://localhost:8000
