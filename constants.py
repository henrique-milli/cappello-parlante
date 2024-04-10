import os
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PLAY_ALLOWED_DAYS = os.getenv("PLAY_ALLOWED_DAYS").split(',')
MIN_PLAYERS_FOR_MEETUP = int(os.getenv("MIN_PLAYERS_FOR_MEETUP"))
LATEST_POLLS_SIZE = int(os.getenv("LATEST_POLLS_SIZE"))
AWS_REGION_CP = os.getenv("AWS_REGION_CP")
BOT_BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
TODAY = datetime.today().weekday()
AWS_ACCESS_KEY_ID_CP = os.getenv("AWS_ACCESS_KEY_ID_CP")
AWS_SECRET_ACCESS_KEY_CP = os.getenv("AWS_SECRET_ACCESS_KEY_CP")
CONVERT_PATH = os.getenv("CONVERT_PATH")