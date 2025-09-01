# --- utils.py ---
import os
import re
import difflib
from PIL import Image
import pytesseract

# If you ever need to override, set TESSERACT_CMD in env
TESS_BIN = None  # let pytesseract auto-detect (Docker installs it system-wide)
if TESS_BIN:
    pytesseract.pytesseract.tesseract_cmd = TESS_BIN

# On Railway the executable will be on PATH; locally you might override it.
# If you set TESSERACT_CMD in Railway Variables, this respects it.
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", "tesseract")

def extract_text_from_image(image_path: str) -> str:
    """
    OCR with preferred langs (uzb+rus), falling back to rus, then eng
    if the traineddata isn't present. This prevents hard crashes.
    """
    img = Image.open(image_path)
    preferred = ["uzb+rus", "rus", "eng"]
    last_err = None
    for lang in preferred:
        try:
            return pytesseract.image_to_string(img, lang=lang)
        except Exception as e:
            last_err = e
    # As a last resort, try default (no lang)
    try:
        return pytesseract.image_to_string(img)
    except Exception:
        # Surface the original, more useful error
        raise RuntimeError(f"OCR failed; last error: {last_err}") from last_err

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