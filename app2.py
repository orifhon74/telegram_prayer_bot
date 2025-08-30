from telegram import Bot
from apscheduler.schedulers.blocking import BlockingScheduler
from pytz import timezone
from datetime import datetime
import pytesseract
from PIL import Image
import re
import difflib

# === BOT CONFIG ===
bot_token = '7696530982:AAEOMNE-jM5xl-Mk3UgQyG_GjzBKfucCUR8'
chat_id = '714491447'  # You can use your ID or group ID
bot = Bot(token=bot_token)

# === TIMEZONE ===
UZ_TZ = timezone('Asia/Tashkent')

# === OCR SETUP ===
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

prayer_name_map = {
    "ТОНГ": "Fajr",
    "ҚУЁШ": "Sunrise",
    "ПЕШИН": "Dhuhr",
    "АСР": "Asr",
    "ШОМ": "Maghrib",
    "ХУФТОН": "Isha"
}

# === OCR ===
def extract_text_from_image(image_path):
    img = Image.open(image_path)
    return pytesseract.image_to_string(img, lang='uzb+rus')

# === PARSE PRAYER TIMES ===
def extract_prayer_times(text):
    canonical_keywords = {
        "ТОНГ": ["ТОНГ"],
        "ҚУЁШ": ["ҚУЁШ"],
        "ПЕШИН": ["ПЕШИН"],
        "АСР": ["АСР"],
        "ШОМ": ["ШОМ", "ПЕ", "Ш0М", "ШОММ", "Ш0Н"],
        "ХУФТОН": ["ХУФТОН"]
    }

    prayer_times = {}

    for line in text.splitlines():
        line_upper = line.strip().upper()
        time_match = re.search(r'(\d{2}:\d{2})', line_upper)
        if not time_match:
            continue

        time_str = time_match.group(1)
        line_before_time = line_upper[:time_match.start()]

        words = line_before_time.split()
        for word in words:
            for canonical, aliases in canonical_keywords.items():
                match = difflib.get_close_matches(word, aliases, n=1, cutoff=0.6)
                if match and canonical not in prayer_times:
                    prayer_times[canonical] = time_str
                    break
            else:
                continue
            break

    return prayer_times

# === SCHEDULE PRAYER ALERTS ===
def schedule_notifications(prayer_times):
    scheduler = BlockingScheduler(timezone=UZ_TZ)

    for name, time_str in prayer_times.items():
        hour, minute = map(int, time_str.split(":"))

        def send_prayer(name=name):
            eng_name = prayer_name_map.get(name, name)
            message = f"🕌 It's time for {eng_name} prayer!"
            bot.send_message(chat_id=chat_id, text=message)
            print(f"✅ Sent: {message} at {datetime.now(UZ_TZ).strftime('%H:%M:%S')}")

        scheduler.add_job(send_prayer, 'cron', hour=hour, minute=minute)
        print(f"⏰ Scheduled {name} at {hour:02d}:{minute:02d}")

    # 🔔 Send test message immediately
    bot.send_message(chat_id=chat_id, text="📣 Test message from prayer bot!")
    scheduler.start()

# === MAIN RUN ===
if __name__ == "__main__":
    text = extract_text_from_image("prayer_times.jpg")
    print("🧾 OCR TEXT:\n", text)

    prayer_times = extract_prayer_times(text)
    print("📅 Extracted Prayer Times:", prayer_times)

    if len(prayer_times) >= 5:
        schedule_notifications(prayer_times)
    else:
        print("⚠️ Not enough prayer times found. Aborting.")