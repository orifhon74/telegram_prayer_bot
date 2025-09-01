# --- daily_checker.py ---
import os
from datetime import datetime, timedelta
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto

from config import (
    API_ID, API_HASH, CHANNEL_USERNAME,
    DATA_DIR, STABLE_PATH, USE_SYMLINK, RETAIN_DAYS, UZ_TZ, SESSION_PATH
)

def _today_uz():
    return datetime.now(UZ_TZ).date()

def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)

def _dated_image_path(d) -> str:
    _ensure_dir(DATA_DIR)
    return os.path.join(DATA_DIR, f"{d.isoformat()}.jpg")

def _stable_points_to(dst: str) -> bool:
    if not os.path.exists(STABLE_PATH):
        return False
    try:
        if os.path.islink(STABLE_PATH):
            return os.path.realpath(STABLE_PATH) == os.path.realpath(dst)
    except Exception:
        pass
    return False

def _point_stable_to(src: str):
    # symlink or copy
    if USE_SYMLINK:
        try:
            if os.path.exists(STABLE_PATH) or os.path.islink(STABLE_PATH):
                os.remove(STABLE_PATH)
        except FileNotFoundError:
            pass
        os.symlink(src, STABLE_PATH)
        print(f"🔗 Linked {STABLE_PATH} -> {src}")
    else:
        with open(src, "rb") as fsrc, open(STABLE_PATH, "wb") as fdst:
            fdst.write(fsrc.read())
        print(f"📎 Copied {src} -> {STABLE_PATH}")

def _cleanup_old():
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

def fetch_today_image() -> str | None:
    """
    Try to ensure today's image exists (00:00–02:00 window preferred).
    Returns path to today's image or None.
    """
    today = _today_uz()
    today_path = _dated_image_path(today)

    # Already present? update stable and return
    if os.path.exists(today_path):
        if not _stable_points_to(today_path):
            _point_stable_to(today_path)
        print("🕐 Today's image already present.")
        _cleanup_old()
        return today_path

    # Preferred window
    start = datetime(today.year, today.month, today.day, 0, 0, tzinfo=UZ_TZ)
    end = start + timedelta(hours=2)

    try:
        with TelegramClient(SESSION_PATH, API_ID, API_HASH) as client:
            # Search for a photo in the 00:00–02:00 window
            for msg in client.iter_messages(CHANNEL_USERNAME, limit=60):
                if isinstance(msg.media, MessageMediaPhoto):
                    msg_uz = msg.date.astimezone(UZ_TZ)
                    if start <= msg_uz <= end:
                        client.download_media(msg.media, file=today_path)
                        print(f"📸 Downloaded in window: {msg_uz} -> {today_path}")
                        _point_stable_to(today_path)
                        _cleanup_old()
                        return today_path

            # Fallback: any photo posted today
            for msg in client.iter_messages(CHANNEL_USERNAME, limit=60):
                if isinstance(msg.media, MessageMediaPhoto):
                    msg_uz = msg.date.astimezone(UZ_TZ)
                    if msg_uz.date() == today:
                        client.download_media(msg.media, file=today_path)
                        print(f"📸 Downloaded fallback today: {msg_uz} -> {today_path}")
                        _point_stable_to(today_path)
                        _cleanup_old()
                        return today_path

    except Exception as e:
        print("❌ Telethon error:", e)

    print("❌ No image found for today.")
    return None