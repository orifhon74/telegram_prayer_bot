# === utils.py ===
import os
import pytesseract
from PIL import Image
import re
import difflib

# Set Tesseract path from env or fallback to 'tesseract' in PATH
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", "tesseract")

def extract_text_from_image(image_path: str) -> str:
    img = Image.open(image_path)
    # uzb (Cyrillic) often packaged as 'uzb' and russian as 'rus'
    # If your Railway image only has 'eng', remove '+rus'.
    return pytesseract.image_to_string(img, lang=os.getenv("OCR_LANGS", "uzb+rus"))

def extract_prayer_times(text: str):
    canonical_keywords = {
        "ТОНГ": ["ТОНГ"],
        "ҚУЁШ": ["ҚУЁШ"],
        "ПЕШИН": ["ПЕШИН"],
        "АСР": ["АСР"],
        "ШОМ": ["ШОМ", "ПЕ", "Ш0М", "ШОММ", "Ш0Н"],
        "ХУФТОН": ["ХУФТОН"]
    }

    prayer_times = {}
    for line in text.splitlines():
        line_upper = line.strip().upper()
        m = re.search(r'(\d{1,2}:\d{2})', line_upper)
        if not m:
            continue
        time_str = m.group(1)
        # text before the time — used to guess which prayer this is
        before = line_upper[:m.start()]
        words = before.split()
        for word in words:
            for canonical, aliases in canonical_keywords.items():
                match = difflib.get_close_matches(word, aliases, n=1, cutoff=0.6)
                if match and canonical not in prayer_times:
                    prayer_times[canonical] = time_str
                    break
            else:
                continue
            break

    return prayer_times

prayer_name_map = {
    "ТОНГ": "Fajr",
    "ҚУЁШ": "Sunrise",
    "ПЕШИН": "Dhuhr",
    "АСР": "Asr",
    "ШОМ": "Maghrib",
    "ХУФТОН": "Isha"
}