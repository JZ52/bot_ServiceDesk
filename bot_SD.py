import os
import json
import asyncio
import logging
import random
import aiohttp
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Загрузка переменных окружения
load_dotenv('key.env')

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
THREAD_ID = os.getenv("THREAD_ID")

PROCESSED_IDS_FILE = "processed_ids.json"

# ---
# Функции для работы с файлами
# ---
def load_processed_ids():
    """Загружает обработанные ID из файла."""
    if os.path.exists(PROCESSED_IDS_FILE):
        try:
            with open(PROCESSED_IDS_FILE, "r") as file:
                return set(json.load(file))
        except (IOError, json.JSONDecodeError) as e:
            logging.error(f"Ошибка при загрузке processed_ids.json: {e}")
            return set()
    return set()

def save_processed_ids(processed_ids):
    """Сохраняет обработанные ID в файл."""
    try:
        with open(PROCESSED_IDS_FILE, "w") as file:
            json.dump(list(processed_ids), file, indent=4)
    except IOError as e:
        logging.error(f"Ошибка при сохранении processed_ids.json: {e}")

processed_ids = load_processed_ids()

# ---
# Асинхронные функции для работы с API
# ---
async def send_to_telegram(session, message, thread_id=None):
    """Асинхронно отправляет сообщение в Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    if thread_id:
        payload["message_thread_id"] = thread_id

    try:
        async with session.post(url, json=payload, timeout=10) as response:
            if response.status != 200:
                logging.error(f"Ошибка отправки в Telegram: {response.status}, ответ: {await response.text()}")
            else:
                logging.info("Сообщение успешно отправлено в Telegram.")
    except aiohttp.ClientError as e:
        logging.error(f"Сетевая ошибка при отправке в Telegram: {e}")
    except asyncio.TimeoutError:
        logging.error("Таймаут при отправке сообщения в Telegram.")

async def fetch_requests(session):
    """Асинхронно получает новые заявки из ManageEngine."""
    headers = {"TECHNICIAN_KEY": API_KEY}
    try:
        async with session.get(API_URL, headers=headers, ssl=False, timeout=10) as response:
            response.raise_for_status() # Вызывает исключение для статусов 4xx/5xx
            data = await response.json()
            return data.get("requests", [])
    except aiohttp.ClientResponseError as e:
        logging.error(f"HTTP-ошибка при получении заявок: {e.status} - {e.message}")
    except aiohttp.ClientError as e:
        logging.error(f"Сетевая ошибка при получении заявок: {e}")
    except asyncio.TimeoutError:
        logging.error("Таймаут при получении заявок.")
    return []

# ---
# Основная логика
# ---
async def process_requests():
    """Основной цикл обработки и отправки заявок."""
    while True:
        async with aiohttp.ClientSession() as session:
            all_requests = await fetch_requests(session)
            
            new_requests = []
            for request in all_requests:
                id_task = str(request.get("id")) # Убедимся, что ID — строка
                if id_task not in processed_ids:
                    processed_ids.add(id_task)
                    new_requests.append(request)
            
            if new_requests:
                logging.info(f"Найдено {len(new_requests)} новых заявок.")
                for request in new_requests:
                    id_task = str(request.get("id"))
                    title = request.get("subject", "Без темы")
                    requester = request.get("requester", {}).get("name", "Неизвестно")
                    link = f"https://192.168.110.13:8080/WorkOrder.do?woMode=viewWO&woID={ id_task }"
                    
                    message = (
                        f"🆕 <b>Новая заявка!</b>\n"
                        f"🔢 <b>Номер заявки:</b> <a href='{link}'>{id_task}</a>\n"
                        f"📌 <b>Тема:</b> {title}\n"
                        f"👤 <b>Написал:</b> {requester}"
                    )
                    await send_to_telegram(session, message, thread_id=THREAD_ID)

            save_processed_ids(processed_ids)
            
        # Добавляем случайную задержку, чтобы избежать 'стаи' запросов
        sleep_duration = 60 + random.randint(1, 15)
        logging.info(f"Ожидание {sleep_duration} секунд до следующей проверки...")
        await asyncio.sleep(sleep_duration)

# ---
# Точка входа в программу
# ---
if __name__ == "__main__":
    try:
        asyncio.run(process_requests())
    except KeyboardInterrupt:
        logging.info("Бот остановлен пользователем.")
    except Exception as e:
        logging.critical(f"Критическая ошибка: {e}", exc_info=True)
