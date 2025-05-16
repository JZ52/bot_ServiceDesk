import requests
import asyncio
import json
import os
import aioschedule
import aiohttp
import datetime
import functools
from dotenv import load_dotenv

load_dotenv('key.env')

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
THREAD_ID = os.getenv("THREAD_ID")

PROCESSED_IDS_FILE = "processed_ids.json"


# Загрузка обработанных ID
def load_processed_ids():
    if os.path.exists(PROCESSED_IDS_FILE):
        with open(PROCESSED_IDS_FILE, "r") as file:
            return set(json.load(file))
    return set()


# Сохранение обработанных ID
def save_processed_ids(processed_ids):
    with open(PROCESSED_IDS_FILE, "w") as file:
        json.dump(list(processed_ids), file)


processed_ids = load_processed_ids()


# Отправка сообщения в Telegram
async def send_to_telegram(message, thread_id=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    if thread_id:
        payload["message_thread_id"] = thread_id

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as response:
            if response.status != 200:
                print(f"Ошибка отправки: {await response.text()}")

# Получение новых заявок из ManageEngine
def fetch_requests():
    headers = {"TECHNICIAN_KEY": API_KEY}
    response = requests.get(API_URL, headers=headers)
    if response.status_code == 200:
        data = response.json()
        new_requests = []
        for request in data["requests"]:
            id_task = request["id"]
            if id_task not in processed_ids:
                processed_ids.add(id_task)
                new_requests.append(request)
        return new_requests
    return []

# Обработка заявок
async def process_requests():
    while True:
        new_requests = fetch_requests()
        for request in new_requests:
            id_task = request["id"]
            title = request["subject"]
            requester = request["requester"]["name"]
            link = f"http://192.168.11.13:8080/WorkOrder.do?woMode=viewWO&woID={ id_task }"
            message = (
                f"🆕 <b>Новая заявка!</b>\n"
                f"🔢 <b>Номер заявки:</b> <a href = '{ link }'>{ id_task }</a>\n"
                f"📌 <b>Тема:</b> { title }\n"
                f"👤 <b>Написал:</b> { requester }"
            )
            await send_to_telegram(message, thread_id=THREAD_ID)

        save_processed_ids(processed_ids)
        await asyncio.sleep(60)

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


# Основной цикл
async def main():
    await asyncio.gather(
        process_requests(),
    )

if __name__ == "__main__":
    asyncio.run(main())