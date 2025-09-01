# === daily_checker.py ===
import os
from datetime import datetime, timedelta
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto

from config import (
    API_ID, API_HASH, CHANNEL_USERNAME,
    DATA_DIR, SESSION_PATH, TELEGRAM_STRING_SESSION,
    UZ_TZ, STABLE_PATH, USE_SYMLINK, RETAIN_DAYS,
)

# ----------------- helpers -----------------
def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def _today_uz_date():
    return datetime.now(UZ_TZ).date()

def _dated_path_for(date_obj) -> str:
    _ensure_dir(DATA_DIR)
    return os.path.join(DATA_DIR, f"{date_obj.isoformat()}.jpg")

def _stable_points_to(path: str) -> bool:
    if not os.path.exists(STABLE_PATH):
        return False
    try:
        if os.path.islink(STABLE_PATH):
            return os.path.realpath(STABLE_PATH) == os.path.realpath(path)
        # If STABLE_PATH is a normal file we’ll always refresh/copy; return False.
        return False
    except Exception:
        return False

def _point_stable_to(src: str):
    """Update STABLE_PATH to point to src (copy or symlink)."""
    if USE_SYMLINK:
        try:
            if os.path.islink(STABLE_PATH) or os.path.exists(STABLE_PATH):
                os.remove(STABLE_PATH)
        except FileNotFoundError:
            pass
        os.symlink(src, STABLE_PATH)
        print(f"🔗 Linked {STABLE_PATH} -> {src}")
    else:
        # Copy bytes to a stable name
        with open(src, "rb") as fsrc, open(STABLE_PATH, "wb") as fdst:
            fdst.write(fsrc.read())
        print(f"📎 Copied {src} -> {STABLE_PATH}")

def _cleanup_old_files():
    if RETAIN_DAYS <= 0:
        return
    cutoff = datetime.now(UZ_TZ) - timedelta(days=RETAIN_DAYS)
    if not os.path.isdir(DATA_DIR):
        return
    for name in os.listdir(DATA_DIR):
        if not name.lower().endswith(".jpg"):
            continue
        path = os.path.join(DATA_DIR, name)
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(path), UZ_TZ)
            if mtime < cutoff:
                os.remove(path)
                print(f"🧹 Removed old file: {name}")
        except Exception:
            pass

def _make_client() -> TelegramClient:
    """Prefer StringSession (Railway variable) if present, else file session under DATA_DIR."""
    if TELEGRAM_STRING_SESSION:
        return TelegramClient(StringSession(TELEGRAM_STRING_SESSION), API_ID, API_HASH)
    return TelegramClient(SESSION_PATH, API_ID, API_HASH)

def _safe_download(client: TelegramClient, msg, out_path: str) -> bool:
    """
    Robust download:
      1) pass the *message* (not msg.media)
      2) verify existence
      3) retry once
    """
    try:
        _ensure_dir(os.path.dirname(out_path))
        # 1st attempt
        client.download_media(msg, file=out_path)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
            return True
        # Retry once
        client.download_media(msg, file=out_path)
        return os.path.exists(out_path) and os.path.getsize(out_path) > 0
    except Exception as e:
        print("⚠️ download_media error:", e)
        return False

# ----------------- public: fetch_today_image -----------------
def fetch_today_image() -> str | None:
    """
    Ensure today's image exists as /data/imonuz/YYYY-MM-DD.jpg and refresh STABLE_PATH.
    Returns absolute path if present/created, else None.
    """
    print("🔎 Checking Telegram channel for today's image…")
    today = _today_uz_date()
    today_path = _dated_path_for(today)

    # Already have today's file — just refresh the stable pointer.
    if os.path.exists(today_path):
        if not _stable_points_to(today_path):
            _point_stable_to(today_path)
        print("🕐 Today's image already present. Reusing.")
        _cleanup_old_files()
        return today_path

    # Time window: 00:00–02:00 (UZT)
    start_uz = datetime(today.year, today.month, today.day, 0, 0, tzinfo=UZ_TZ)
    end_uz = start_uz + timedelta(hours=2)

    try:
        with _make_client() as client:
            # 1) strict window first
            for msg in client.iter_messages(CHANNEL_USERNAME, limit=50):
                if isinstance(msg.media, MessageMediaPhoto):
                    msg_uz = msg.date.astimezone(UZ_TZ)
                    if start_uz <= msg_uz <= end_uz:
                        if _safe_download(client, msg, today_path):
                            print(f"📸 Downloaded image in window: {msg_uz} → {today_path}")
                            _point_stable_to(today_path)
                            _cleanup_old_files()
                            return today_path
                        else:
                            print("❌ Download returned no file (window).")

            # 2) fallback: any photo from today (sometimes they post a bit off 00:10)
            for msg in client.iter_messages(CHANNEL_USERNAME, limit=50):
                if isinstance(msg.media, MessageMediaPhoto):
                    msg_uz = msg.date.astimezone(UZ_TZ)
                    if msg_uz.date() == today:
                        if _safe_download(client, msg, today_path):
                            print(f"📸 Downloaded today's latest image (fallback): {msg_uz} → {today_path}")
                            _point_stable_to(today_path)
                            _cleanup_old_files()
                            return today_path
                        else:
                            print("❌ Download returned no file (fallback).")

    except Exception as e:
        print("❌ Telethon error:", e)

    print("❌ No image found for today.")
    return None