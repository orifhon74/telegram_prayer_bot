# === daily_checker.py ===
import os
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto
from datetime import datetime, timedelta, timezone

API_ID = int(os.getenv("TELEGRAM_API_ID"))
API_HASH = os.getenv("TELEGRAM_API_HASH")
SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "prayer_session")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME", "imonuz")

# ---------- Storage ----------
DATA_DIR = os.path.abspath(os.getenv("DATA_DIR", "data/imonuz"))
os.makedirs(DATA_DIR, exist_ok=True)

# Keep a stable “today” pointer/file INSIDE the data dir by default
_default_stable = os.path.join(DATA_DIR, "prayer_times.jpg")
STABLE_PATH = os.path.abspath(os.getenv("DOWNLOAD_PATH", _default_stable))

USE_SYMLINK = os.getenv("USE_SYMLINK", "false").lower() == "true"   # keep false on Railway
RETAIN_DAYS = int(os.getenv("RETAIN_DAYS", "14"))

# Asia/Tashkent = UTC+5 (no DST)
UZ_TZ = timezone(timedelta(hours=5))

def _ensure_dir(p: str):
    os.makedirs(p, exist_ok=True)

def _today_uz_date():
    return datetime.now(timezone.utc).astimezone(UZ_TZ).date()

def _dated_path_for(date_obj) -> str:
    _ensure_dir(DATA_DIR)
    return os.path.join(DATA_DIR, f"{date_obj.isoformat()}.jpg")

def _stable_points_to(path: str) -> bool:
    """Return True if STABLE_PATH (file or symlink) already points to this path."""
    if not os.path.exists(STABLE_PATH):
        return False
    try:
        if os.path.islink(STABLE_PATH):
            return os.path.realpath(STABLE_PATH) == os.path.realpath(path)
        else:
            # If we copy instead of symlink, just compare size/mtime to avoid re-copy churn
            return False
    except Exception:
        return False

def _point_stable_to(src: str):
    src = os.path.abspath(src)
    dst = os.path.abspath(STABLE_PATH)
    if USE_SYMLINK:
        try:
            if os.path.islink(dst) or os.path.exists(dst):
                os.remove(dst)
        except FileNotFoundError:
            pass
        os.symlink(src, dst)
        print(f"🔗 Linked {dst} -> {src}")
    else:
        with open(src, "rb") as fsrc, open(dst, "wb") as fdst:
            fdst.write(fsrc.read())
        print(f"📎 Copied {src} -> {dst}")

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

def _list_data_dir() -> None:
    """Log volume contents so you can verify persistence in Railway Logs."""
    try:
        if not os.path.isdir(DATA_DIR):
            print(f"📂 DATA_DIR does not exist yet: {DATA_DIR}")
            return
        print(f"📂 Contents of {DATA_DIR}:")
        for name in sorted(os.listdir(DATA_DIR)):
            path = os.path.join(DATA_DIR, name)
            try:
                size = os.path.getsize(path)
                mtime = datetime.fromtimestamp(os.path.getmtime(path), UZ_TZ)
                print(f"   - {name} ({size} bytes, modified {mtime:%Y-%m-%d %H:%M:%S} UZ)")
            except Exception as e:
                print(f"   - {name} (error reading: {e})")
    except Exception as e:
        print("⚠️ Could not list DATA_DIR:", e)

def run_daily_check() -> bool:
    """
    Ensure today's image exists as data/imonuz/YYYY-MM-DD.jpg
    and update STABLE_PATH to point to it.
    Returns True if present (reused or freshly downloaded), else False.
    """
    print("🔍 Checking messages...")
    today = _today_uz_date()
    today_path = _dated_path_for(today)

    # Log current volume state
    _list_data_dir()

    # If already have today's file, ensure stable pointer is set and return True
    if os.path.exists(today_path):
        if not _stable_points_to(today_path):
            _point_stable_to(today_path)
        print("🕐 Today's image already present. Reusing.")
        _cleanup_old_files()
        return True

    # Window: 00:00–02:00 UZ
    start_uz = datetime(today.year, today.month, today.day, 0, 0, tzinfo=UZ_TZ)
    end_uz = start_uz + timedelta(hours=2)

    try:
        with TelegramClient(SESSION_NAME, API_ID, API_HASH) as client:
            # Try window first
            for msg in client.iter_messages(CHANNEL_USERNAME, limit=50):
                if isinstance(msg.media, MessageMediaPhoto):
                    msg_uz = msg.date.astimezone(UZ_TZ)
                    if start_uz <= msg_uz <= end_uz:
                        client.download_media(msg.media, file=today_path)
                        print(f"📸 Downloaded image in window: {msg_uz} -> {today_path}")
                        _point_stable_to(today_path)
                        _cleanup_old_files()
                        return True

            # Fallback: any photo posted today
            for msg in client.iter_messages(CHANNEL_USERNAME, limit=50):
                if isinstance(msg.media, MessageMediaPhoto):
                    msg_uz = msg.date.astimezone(UZ_TZ)
                    if msg_uz.date() == today:
                        client.download_media(msg.media, file=today_path)
                        print(f"📸 Downloaded today's latest image (fallback): {msg_uz} -> {today_path}")
                        _point_stable_to(today_path)
                        _cleanup_old_files()
                        return True

    except Exception as e:
        print("❌ Telethon error:", e)

    print("❌ No image found for today.")
    return False