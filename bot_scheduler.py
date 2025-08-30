# === bot_scheduler.py ===
import os
from telegram import Bot
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone as tz_get
from datetime import datetime
from utils import extract_text_from_image, extract_prayer_times, prayer_name_map

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
DOWNLOAD_PATH = os.getenv("DOWNLOAD_PATH", "prayer_times.jpg")
TZ_NAME = os.getenv("TZ_NAME", "Asia/Tashkent")
UZ_TZ = tz_get(TZ_NAME)

bot = Bot(token=BOT_TOKEN)

def schedule_notifications(scheduler: BackgroundScheduler, image_path: str = None):
    """
    Parse today's image and schedule prayer notifications.
    Replaces any old jobs with today's new times.
    """
    image_path = image_path or DOWNLOAD_PATH

    text = extract_text_from_image(image_path)
    print("🧾 OCR TEXT (first 400 chars):\n", text[:400])

    prayer_times = extract_prayer_times(text)
    print("📅 Extracted Prayer Times:", prayer_times)

    if len(prayer_times) < 5:
        print("⚠️ Not enough prayer times found. Skipping scheduling.")
        return

    # Remove previous jobs (if any)
    for job in scheduler.get_jobs():
        if job.id.startswith("prayer_"):
            scheduler.remove_job(job.id)

    for canon_name, time_str in prayer_times.items():
        try:
            hour, minute = map(int, time_str.split(":"))
        except Exception:
            print(f"⚠️ Bad time string for {canon_name}: {time_str}")
            continue

        eng_name = prayer_name_map.get(canon_name, canon_name)

        def send_prayer(name=eng_name):
            message = f"🕌 It's time for {name} prayer!"
            bot.send_message(chat_id=CHAT_ID, text=message)
            print(f"✅ Sent: {message} at {datetime.now(UZ_TZ).strftime('%H:%M:%S')}")

        job_id = f"prayer_{canon_name}"
        scheduler.add_job(
            send_prayer,
            trigger='cron',
            hour=hour,
            minute=minute,
            id=job_id,
            timezone=UZ_TZ
        )
        print(f"⏰ Scheduled {eng_name} at {hour:02d}:{minute:02d} {TZ_NAME}")