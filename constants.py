import os
from datetime import datetime

# Environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
PLAY_ALLOWED_DAYS = os.getenv("PLAY_ALLOWED_DAYS", "").split(',')
MIN_PLAYERS_FOR_MEETUP = int(os.getenv("MIN_PLAYERS_FOR_MEETUP"))
MAX_VACANCY = int(os.getenv("MAX_VACANCY"))
AWS_REGION_CP = os.getenv("AWS_REGION_CP")
TODAY = datetime.today().weekday()
AWS_ACCESS_KEY_ID_CP = os.getenv("AWS_ACCESS_KEY_ID_CP")
AWS_SECRET_ACCESS_KEY_CP = os.getenv("AWS_SECRET_ACCESS_KEY_CP")
CONVERT_EXECUTABLE_PATH = os.getenv("CONVERT_PATH")
TEMP_PATH = os.getenv("TEMP_PATH")
GIF_DELAY = os.getenv("GIF_DELAY")
PNG_WIDTH = os.getenv("PNG_WIDTH")
PNG_HEIGHT = os.getenv("PNG_HEIGHT")

# Constants
BOT_BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PUZZLE_INITIAL_SVG_PATH = os.path.join(TEMP_PATH, 'puzzle_initial.svg')
PUZZLE_INITIAL_PNG_PATH = os.path.join(TEMP_PATH, 'puzzle_initial.png')
PUZZLE_SOLUTION_SVGS_DIR = os.path.join(TEMP_PATH, 'solution', 'svgs')
PUZZLE_SOLUTION_PNGS_DIR = os.path.join(TEMP_PATH, 'solution', 'pngs')
PUZZLE_SOLUTION_GIF_PATH = os.path.join(TEMP_PATH, 'solution', 'solution.gif')


def PUZZLE_SOLUTION_SVGS_PATH(i):
    return os.path.join(PUZZLE_SOLUTION_SVGS_DIR, f'solution_{i}.svg')


def PUZZLE_SOLUTION_PNGS_PATH(i):
    return os.path.join(PUZZLE_SOLUTION_PNGS_DIR, f'solution_{i}.png')
