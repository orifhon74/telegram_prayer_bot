# === daily_checker.py ===
import os
from datetime import datetime, timedelta
from typing import Optional

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto

from config import (
    API_ID, API_HASH, CHANNEL_USERNAME,
    DATA_DIR, SESSION_PATH, TELEGRAM_STRING_SESSION,
    UZ_TZ, STABLE_PATH, USE_SYMLINK, RETAIN_DAYS,
)

# ---------------- Helpers ----------------
def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def _today_uz_date():
    return datetime.now(UZ_TZ).date()

def _dated_path_for(date_obj) -> str:
    _ensure_dir(DATA_DIR)
    return os.path.join(DATA_DIR, f"{date_obj.isoformat()}.jpg")

def _stable_points_to(path: str) -> bool:
    """Return True if STABLE_PATH already points to this path."""
    if not os.path.exists(STABLE_PATH):
        return False
    try:
        if os.path.islink(STABLE_PATH):
            return os.path.realpath(STABLE_PATH) == os.path.realpath(path)
        else:
            # if we copy instead of symlink, treat as not pointing (so we can refresh)
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
        # copy bytes (works everywhere)
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

# ---------------- Telethon Client ----------------
def _make_client() -> TelegramClient:
    """
    Use StringSession if provided (best for Railway), else file-based session under DATA_DIR.
    """
    if TELEGRAM_STRING_SESSION:
        return TelegramClient(StringSession(TELEGRAM_STRING_SESSION), API_ID, API_HASH)
    else:
        # SESSION_PATH is inside the persistent volume
        return TelegramClient(SESSION_PATH, API_ID, API_HASH)

# ---------------- Public API ----------------
def fetch_today_image() -> Optional[str]:
    """
    Ensure today's image exists at DATA_DIR/YYYY-MM-DD.jpg and point STABLE_PATH to it.
    Returns the absolute path if available (existing or freshly downloaded), else None.
    """
    print("🔍 Checking Telegram channel for today's image…")

    today = _today_uz_date()
    today_path = _dated_path_for(today)

    # If we already have today's file, make sure STABLE_PATH is set and return
    if os.path.exists(today_path):
        if not _stable_points_to(today_path):
            _point_stable_to(today_path)
        print(f"🕐 Today's image already present → {today_path}")
        _cleanup_old_files()
        return today_path

    # Search window: 00:00–02:00 UZ (imon usually posts ~00:10)
    start_uz = datetime(today.year, today.month, today.day, 0, 0, tzinfo=UZ_TZ)
    end_uz = start_uz + timedelta(hours=2)

    try:
        with _make_client() as client:
            # Pass 1: strict time window
            for msg in client.iter_messages(CHANNEL_USERNAME, limit=60):
                if isinstance(msg.media, MessageMediaPhoto):
                    msg_uz = msg.date.astimezone(UZ_TZ)
                    if start_uz <= msg_uz <= end_uz:
                        client.download_media(msg.media, file=today_path)
                        print(f"📸 Downloaded image in window: {msg_uz} -> {today_path}")
                        _point_stable_to(today_path)
                        _cleanup_old_files()
                        return today_path

            # Pass 2 (fallback): any photo posted today
            for msg in client.iter_messages(CHANNEL_USERNAME, limit=100):
                if isinstance(msg.media, MessageMediaPhoto):
                    msg_uz = msg.date.astimezone(UZ_TZ)
                    if msg_uz.date() == today:
                        client.download_media(msg.media, file=today_path)
                        print(f"📸 Downloaded today's latest image (fallback): {msg_uz} -> {today_path}")
                        _point_stable_to(today_path)
                        _cleanup_old_files()
                        return today_path

    except Exception as e:
        print("❌ Telethon error:", e)

    print("❌ No image found for today.")
    return None

# Optional legacy wrapper (if any older code calls this)
def run_daily_check() -> bool:
    """Back-compat: returns True iff fetch_today_image() found/created today's image."""
    return fetch_today_image() is not None