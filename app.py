# === app.py ===
import os
import time
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone as tz_get
from daily_checker import run_daily_check
from bot_scheduler import schedule_notifications

TZ_NAME = os.getenv("TZ_NAME", "Asia/Tashkent")
UZ_TZ = tz_get(TZ_NAME)

def refresh_and_schedule(scheduler: BackgroundScheduler):
    """
    Download/reuse today's image, then (re)schedule today's notifications.
    """
    ok = run_daily_check()
    if ok:
        # brief pause to ensure file flushed
        time.sleep(1)
        schedule_notifications(scheduler)
    else:
        print("🛑 Skipping schedule — no image for today.")

def main():
    print("🚀 Starting prayer bot worker...")
    scheduler = BackgroundScheduler(timezone=UZ_TZ)

    # 1) Run immediately at boot
    refresh_and_schedule(scheduler)

    # 2) Re-run every day shortly after the channel posts (around 00:10 UZ)
    scheduler.add_job(
        lambda: refresh_and_schedule(scheduler),
        trigger='cron',
        hour=0,
        minute=12,
        id="daily_refresh",
        timezone=UZ_TZ
    )

    scheduler.start()
    print("📆 Scheduler started. Worker is running.")

    try:
        # Keep the worker alive
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        scheduler.shutdown()

if __name__ == "__main__":
    main()