from locust import HttpUser, task, between
import random

class BotBackendUser(HttpUser):
    """
    Имитация пользователя, который обращается напрямую к API бота 
    или к schedule-service, минуя интерфейс Telegram.
    """
    wait_time = between(1, 3) # Пауза между действиями пользователя

    @task(3)
    def get_schedule(self):
        """Имитация запроса расписания (нагрузка на presentations-crud и DB)."""
        self.client.get("/api/v1/schedule", name="Get Schedule")

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
            else:
                response.failure(f"Ошибка поиска: {response.status_code}")

# Для запуска: locust -f tests/load_test.py --host=http://localhost:8000