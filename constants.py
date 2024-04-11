import os
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PLAY_ALLOWED_DAYS = os.getenv("PLAY_ALLOWED_DAYS", "").split(',')
MIN_PLAYERS_FOR_MEETUP = int(os.getenv("MIN_PLAYERS_FOR_MEETUP"))
MAX_VACANCY = int(os.getenv("MAX_VACANCY"))
AWS_REGION_CP = os.getenv("AWS_REGION_CP")
BOT_BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
TODAY = datetime.today().weekday()
AWS_ACCESS_KEY_ID_CP = os.getenv("AWS_ACCESS_KEY_ID_CP")
AWS_SECRET_ACCESS_KEY_CP = os.getenv("AWS_SECRET_ACCESS_KEY_CP")
CONVERT_PATH = os.getenv("CONVERT_PATH")
TEMP_PATH = os.getenv("TEMP_PATH")
PSPDFKIT_API_KEY = os.getenv("PSPDFKIT_API_KEY")
