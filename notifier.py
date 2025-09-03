# --- notifier.py ---
from datetime import datetime
from pytz import timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram import Bot

from utils import extract_text_from_image, extract_prayer_times, PRAYER_NAME_MAP
from config import BOT_TOKEN, CHAT_ID, UZ_TZ

bot = Bot(token=BOT_TOKEN)
scheduler = BackgroundScheduler(timezone=UZ_TZ)

ORDER = ["ТОНГ", "ҚУЁШ", "ПЕШИН", "АСр", "АСР", "ШОМ", "ХУФТОН"]  # tolerate a stray lowercase variant

def _send(name_cyr: str):
    eng = PRAYER_NAME_MAP.get(name_cyr, name_cyr)
    if eng == 'Sunrise':
        # Skip sending messages for Sunrise
        print(f"ℹ️ Skipping notification for {eng}.")
        return
    msg = f"🕌 It's time for {eng} prayer!"
    bot.send_message(chat_id=CHAT_ID, text=msg)
    print(f"✅ Sent: {msg} @ {datetime.now(UZ_TZ).strftime('%H:%M:%S')}")

def _send_daily_summary(times: dict):
    lines = ["📅 Today's times (UZT):"]
    for key in ORDER:
        if key in times:
            lines.append(f"• {PRAYER_NAME_MAP.get(key, key)} — {times[key]}")
    # add any extras we parsed (rare)
    for k, v in times.items():
        if k not in ORDER:
            lines.append(f"• {PRAYER_NAME_MAP.get(k, k)} — {v}")
    text = "\n".join(lines)
    bot.send_message(chat_id=CHAT_ID, text=text)
    print("✅ Sent daily summary.")

def _clear_old_jobs():
    for job in scheduler.get_jobs():
        if job.name and (job.name.startswith("prayer-") or job.name.startswith("daily-summary-")):
            scheduler.remove_job(job.id)

def schedule_from_image(image_path: str, summary_mode: str = "immediate"):
    """
    Parse prayer times from `image_path` and schedule today's notifications.
    - Clears previous prayer/summary jobs.
    - Schedules only FUTURE notifications for the current day.
    - Sends a daily summary immediately (default) or schedules it for 00:30.
      summary_mode: "immediate" | "0030"
    """
    _clear_old_jobs()

    txt = extract_text_from_image(image_path)
    times = extract_prayer_times(txt)
    print("📅 Extracted times:", times)

    # Require a reasonable set
    if len(times) < 4:
        print("⚠️ Not enough times parsed; skipping scheduling.")
        return

    now = datetime.now(UZ_TZ)
    today = now.date()

    # Schedule each prayer (future only)
    for name_cyr, hhmm in times.items():
        try:
            hh, mm = map(int, hhmm.split(":"))
        except Exception:
            continue
        run_dt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if run_dt.date() != today:
            run_dt = run_dt.replace(year=now.year, month=now.month, day=today.day)
        if run_dt > now:
            scheduler.add_job(
                _send,
                "date",
                run_date=run_dt,
                args=[name_cyr],
                name=f"prayer-{name_cyr}",
                misfire_grace_time=60,   # if container paused briefly
                coalesce=True,
            )
            print(f"⏰ Scheduled {name_cyr} at {hh:02d}:{mm:02d}")

    # Daily summary
    if summary_mode == "immediate":
        _send_daily_summary(times)
    else:
        # schedule a 00:30 summary
        trigger = CronTrigger(hour=0, minute=30, timezone=UZ_TZ)
        # give the job an id that incorporates the date so we don't double-schedule
        job_id = f"daily-summary-{today.isoformat()}"
        # remove any existing summary job for today
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass
        scheduler.add_job(
            _send_daily_summary,
            trigger=trigger,
            args=[times],
            id=job_id,
            name=job_id,
            misfire_grace_time=300,
            coalesce=True,
        )
        print("🗓️ Daily summary scheduled for 00:30 UZT.")