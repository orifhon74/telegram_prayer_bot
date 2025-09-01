# --- utils.py ---
import re
import difflib
from PIL import Image
import pytesseract

# If you ever need to override, set TESSERACT_CMD in env
TESS_BIN = None  # let pytesseract auto-detect (Docker installs it system-wide)
if TESS_BIN:
    pytesseract.pytesseract.tesseract_cmd = TESS_BIN

def extract_text_from_image(image_path: str) -> str:
    img = Image.open(image_path)
    # Uzbek + Russian often appear. Keep as you had.
    return pytesseract.image_to_string(img, lang="uzb+rus")

def extract_prayer_times(text: str) -> dict:
    """
    Return a dict like {"ТОНГ": "05:01", "ҚУЁШ": "06:20", ...}
    Uses fuzzy keyword matching (Cyrillic forms).
    """
    canonical_keywords = {
        "ТОНГ": ["ТОНГ"],
        "ҚУЁШ": ["ҚУЁШ"],
        "ПЕШИН": ["ПЕШИН"],
        "АСР": ["АСР"],
        "ШОМ": ["ШОМ", "Ш0М", "ШОММ", "Ш0Н"],
        "ХУФТОН": ["ХУФТОН"],
    }
    prayer_times = {}

    for line in text.splitlines():
        u = line.strip().upper()
        m = re.search(r'(\d{2}:\d{2})', u)
        if not m:
            continue
        time_str = m.group(1)
        before = u[:m.start()]
        words = before.split()
        for w in words:
            for canon, aliases in canonical_keywords.items():
                match = difflib.get_close_matches(w, aliases, n=1, cutoff=0.6)
                if match and canon not in prayer_times:
                    prayer_times[canon] = time_str
                    break
            else:
                continue
            break

    return prayer_times

PRAYER_NAME_MAP = {
    "ТОНГ": "Fajr",
    "ҚУЁШ": "Sunrise",
    "ПЕШИН": "Dhuhr",
    "АСР": "Asr",
    "ШОМ": "Maghrib",
    "ХУФТОН": "Isha",
}