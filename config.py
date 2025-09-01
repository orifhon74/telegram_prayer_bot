# --- config.py ---
import os
from datetime import timedelta, timezone
from pytz import timezone as pytz_tz

# Telegram (Telethon)
API_ID = int(os.getenv("TELEGRAM_API_ID", "0"))
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "imonuz")

# Bot (python-telegram-bot v13)
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")  # e.g. your user id

# Storage on persistent volume
DATA_DIR = os.getenv("DATA_DIR", "/data/imonuz")  # MUST be absolute on Railway
os.makedirs(DATA_DIR, exist_ok=True)

# Telethon session goes on the volume so it survives restarts
SESSION_PATH = os.getenv("TELEGRAM_SESSION_PATH", os.path.join(DATA_DIR, "prayer_session"))

# Stable pointer to “today’s” image inside DATA_DIR
STABLE_PATH = os.getenv("STABLE_PATH", os.path.join(DATA_DIR, "today.jpg"))
USE_SYMLINK = os.getenv("USE_SYMLINK", "false").lower() == "true"
RETAIN_DAYS = int(os.getenv("RETAIN_DAYS", "14"))

# Timezone
# Asia/Tashkent = UTC+5 (no DST)
UZ_TZ = pytz_tz("Asia/Tashkent")

# Daily fetch schedule (00:12 to be safe after 00:10 post time)
FETCH_CRON_HOUR = int(os.getenv("FETCH_CRON_HOUR", "0"))
FETCH_CRON_MIN = int(os.getenv("FETCH_CRON_MIN", "12"))