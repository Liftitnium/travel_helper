import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DEFAULT_ORIGIN = os.getenv("DEFAULT_ORIGIN", "MAD")
SCAN_HOUR = int(os.getenv("SCAN_HOUR", "8"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "10"))
DATE_RANGE_WEEKS = int(os.getenv("DATE_RANGE_WEEKS", "8"))
HEADLESS = os.getenv("HEADLESS", "false").lower() in ("true", "1", "yes")

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "bot.db")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

WINDOW_SIZE = "1920,1080"
MIN_DELAY = 2.0
MAX_DELAY = 5.0
TRIP_MIN_NIGHTS = 1
TRIP_MAX_NIGHTS = 3
