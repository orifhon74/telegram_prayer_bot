# --- notifier.py ---
from datetime import datetime
from pytz import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from telegram import Bot

from utils import extract_text_from_image, extract_prayer_times, PRAYER_NAME_MAP
from config import BOT_TOKEN, CHAT_ID, UZ_TZ

bot = Bot(token=BOT_TOKEN)
scheduler = BackgroundScheduler(timezone=UZ_TZ)

def _send(name_cyr: str):
    eng = PRAYER_NAME_MAP.get(name_cyr, name_cyr)
    msg = f"🕌 It's time for {eng} prayer!"
    bot.send_message(chat_id=CHAT_ID, text=msg)
    print(f"✅ Sent: {msg} @ {datetime.now(UZ_TZ).strftime('%H:%M:%S')}")

def schedule_from_image(image_path: str):
    """
    Parses times and schedules ONLY future jobs for today.
    Clears previous jobs first.
    """
    # Clear existing daily jobs to avoid duplicates
    for job in scheduler.get_jobs():
        if job.name and job.name.startswith("prayer-"):
            scheduler.remove_job(job.id)

    txt = extract_text_from_image(image_path)
    times = extract_prayer_times(txt)
    print("📅 Extracted times:", times)

    if len(times) < 4:
        print("⚠️ Not enough times parsed; skipping scheduling.")
        return

    now = datetime.now(UZ_TZ)
    today = now.date()

    for name_cyr, hhmm in times.items():
        try:
            hh, mm = map(int, hhmm.split(":"))
        except Exception:
            continue
        run_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if run_dt.date() != today:
            run_dt = run_dt.replace(year=now.year, month=now.month, day=today.day)
        # schedule only if in the future
        if run_dt > now:
            scheduler.add_job(
                _send,
                "date",
                run_date=run_dt,
                args=[name_cyr],
                name=f"prayer-{name_cyr}"
            )
            print(f"⏰ Scheduled {name_cyr} at {hh:02d}:{mm:02d}")