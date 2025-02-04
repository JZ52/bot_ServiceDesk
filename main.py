import requests
import asyncio
import json
import os
import aioschedule
import aiohttp
import datetime
import functools
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
from models import get_daily_summary

load_dotenv('key.env')

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
THREAD_ID = os.getenv("THREAD_ID")
MEDOC_URL = os.getenv("MEDOC_URL")
VERSION_FILE = "version.txt"
LOG_FILE = "medoc_log.txt"

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


# Сводка за день
async def send_summary():
    summary = get_daily_summary()
    if not summary:
        return

    message = "Сводка за сегодня: \n"
    for user_name, count in summary:
        message += f"{user_name}: {count} сообщений\n"

    await send_to_telegram(message, thread_id=THREAD_ID)


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
            message = (
                f"🆕 <b>Новая заявка!</b>\n"
                f"🔢 <b>Номер заявки:</b> {id_task}\n"
                f"📌 <b>Тема:</b> {title}\n"
                f"👤 <b>Написал:</b> {requester}"
            )
            await send_to_telegram(message, thread_id=THREAD_ID)

        save_processed_ids(processed_ids)
        await asyncio.sleep(60)


# Проверка обновлений M.E.Doc
async def check_medoc_updates():
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service)
    try:
        driver.get(MEDOC_URL)
        version_new = driver.find_element(By.CLASS_NAME, "js-update-num").text
        if os.path.exists(VERSION_FILE):
            with open(VERSION_FILE, "r") as file:
                version_actual = file.read().strip()
        else:
            version_actual = ""
        if version_new != version_actual:
            with open(VERSION_FILE, "w") as file:
                file.write(version_new)
            message = (
                f"\U0001F195Вышла новая версия M.E.Doс: <b>{version_new}</b>.\n"
                f"Обновите, пожалуйста!"
            )
            await send_to_telegram(message, thread_id=THREAD_ID)
            print(version_new)
        else:
            with open(LOG_FILE, "a") as log_file:
                log_file.write(f"{datetime.datetime.now()} - Версия актуальна: {version_actual}\n")
    except Exception as e:
        print("Ошибка при проверке обновлений M.E.Doc:", e)
    finally:
        driver.quit()

# Обёртки для асинхронных функций
def schedule_send_summary():
    asyncio.create_task(send_summary())

def schedule_check_medoc_updates():
    asyncio.create_task(check_medoc_updates())

# Планировщик
async def scheduler():

    aioschedule.every().day.at("00:18").do(schedule_send_summary)
    aioschedule.every().day.at("10:00").do(schedule_check_medoc_updates)

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)

    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(60)


# Основной цикл
async def main():
    await asyncio.gather(
        process_requests(),
        #scheduler()
    )


if __name__ == "__main__":
    asyncio.run(main())