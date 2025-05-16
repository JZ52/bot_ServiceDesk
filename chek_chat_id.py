import requests
import json

TELEGRAM_BOT_TOKEN = ""

def get_chat_id():
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    response = requests.get(url)
    updates = response.json()
    print(json.dumps(updates, indent=4))  # Красивый вывод данных

get_chat_id()