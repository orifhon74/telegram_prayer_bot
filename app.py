# --- app.py ---
import os
from flask import Flask, jsonify
from apscheduler.triggers.cron import CronTrigger

from config import UZ_TZ, FETCH_CRON_HOUR, FETCH_CRON_MIN, DATA_DIR, STABLE_PATH
from notifier import scheduler, schedule_from_image
from daily_checker import fetch_today_image

from telegram.ext import Updater
from config import BOT_TOKEN
from commands import register_handlers

app = Flask(__name__)

@app.route("/healthz")
def healthz():
    return "ok", 200

@app.route("/status")
def status():
    return jsonify({
        "data_dir": DATA_DIR,
        "stable_path_exists": os.path.exists(STABLE_PATH),
        "jobs": [repr(j) for j in scheduler.get_jobs()],
    })

def bootstrap_once():
    """
    On startup: ensure today's image and build today's schedule.
    """
    print(f"🚀 Starting prayer bot service… DATA_DIR={DATA_DIR}")
    path = fetch_today_image()
    if path:
        schedule_from_image(path)
    else:
        print("🟡 No image at startup; will retry at the daily cron.")

def schedule_daily_fetch():
    """
    Every day @ 00:12 Asia/Tashkent: re-fetch image and rebuild schedule.
    """
    def job():
        print("🔁 Daily fetch job firing…")
        path = fetch_today_image()
        if path:
            schedule_from_image(path)

    trigger = CronTrigger(hour=FETCH_CRON_HOUR, minute=FETCH_CRON_MIN, timezone=UZ_TZ)
    scheduler.add_job(job, trigger=trigger, name="daily-fetch")
    print(f"🗓️ Cron set for {FETCH_CRON_HOUR:02d}:{FETCH_CRON_MIN:02d} Asia/Tashkent")

def create_app():
    if not scheduler.running:
        scheduler.start(paused=False)
        schedule_daily_fetch()
        bootstrap_once()
    return app

def start_bot():
    updater = Updater(token=BOT_TOKEN, use_context=True)
    register_handlers(updater.dispatcher)
    updater.start_polling()
    print("🤖 Telegram bot polling started.")

# For local runs: python app.py
if __name__ == "__main__":
    create_app()
    start_bot()
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)