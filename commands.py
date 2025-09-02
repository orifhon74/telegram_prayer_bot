# --- commands.py ---
import os
from telegram.ext import CommandHandler
from utils import extract_text_from_image, extract_prayer_times, PRAYER_NAME_MAP


def today_cmd(update, context):
    stable_path = os.getenv("STABLE_PATH", "/data/imonuz/today.jpg")
    if not os.path.exists(stable_path):
        update.message.reply_text("⚠️ No prayer times available yet today.")
        return

    text = extract_text_from_image(stable_path)
    times = extract_prayer_times(text)
    order = ["ТОНГ", "ҚУЁШ", "ПЕШИН", "АСР", "ШОМ", "ХУФТОН"]

    lines = ["📅 Today's times (UZT):"]
    for k in order:
        if k in times:
            lines.append(f"• {PRAYER_NAME_MAP.get(k, k)} — {times[k]}")

    update.message.reply_text("\n".join(lines))


def register_handlers(dispatcher):
    dispatcher.add_handler(CommandHandler("today", today_cmd))