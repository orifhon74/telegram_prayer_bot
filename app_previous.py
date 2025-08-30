import schedule
import time
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto
import pytesseract
from PIL import Image
import os
import difflib
from datetime import datetime, timedelta, timezone

# ========== CONFIG ==========
api_id = 25627453
api_hash = '42d20a459418d7b8642c25dc4adaae94'
session_name = 'prayer_session'
channel_username = 'imonuz'
download_path = 'latest.jpg'
notify_chat_id = 'me'

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = '/opt/homebrew/bin/tesseract'

# ========== OCR UTIL ==========
def extract_prayer_name(text):
    keywords = ["БОМДОД", "ПЕШИН", "АСР", "ШАМ", "ХУФТОН"]
    found = []

    for line in text.splitlines():
        word = line.strip().upper()
        match = difflib.get_close_matches(word, keywords, n=1, cutoff=0.6)
        if match:
            found.append(match[0])

    return found[0] if found else None

# ========== DAILY CHECK FUNCTION ==========
def run_daily_check():
    print("🔍 Checking messages...")

    # Define time window: 12:00 to 01:00 in Tashkent time
    tz = timezone(timedelta(hours=5))  # Uzbekistan is UTC+5
    now_utc = datetime.now(timezone.utc)
    today_uz = now_utc.astimezone(tz).date()
    start_time_uz = datetime(today_uz.year, today_uz.month, today_uz.day, 0, 0, tzinfo=tz)
    end_time_uz = start_time_uz + timedelta(hours=1)

    with TelegramClient(session_name, api_id, api_hash) as client:
        messages = client.iter_messages(channel_username, limit=20)

        found_image = False
        for msg in messages:
            if isinstance(msg.media, MessageMediaPhoto) and start_time_uz <= msg.date <= end_time_uz:
                client.download_media(msg.media, file=download_path)
                found_image = True
                print("📸 Downloaded image from:", msg.date)
                break

        if not found_image:
            print("❌ No image found between 12am–1am (UZ time).")
            return

        # OCR
        img = Image.open(download_path)
        text = pytesseract.image_to_string(img, lang='uzb+rus')
        print("🧾 Extracted Text:\n", text)

        # Extract prayer
        prayer = extract_prayer_name(text)
        if prayer:
            message = f"🕌 Вақт бўлди: {prayer} намози!"
            client.send_message(notify_chat_id, message)
            print("✅ Notification sent:", message)
        else:
            print("❌ No recognizable prayer name in text.")

# ========== SCHEDULER ==========
schedule.every().day.at("01:00").do(run_daily_check)

print("📆 Prayer checker scheduled daily at 1 AM (local machine time).")
while True:
    schedule.run_pending()
    time.sleep(30)