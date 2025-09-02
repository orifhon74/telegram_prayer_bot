# --- utils.py ---
import os
import re
import difflib
from datetime import time as dtime
from PIL import Image
import pytesseract

# Let pytesseract auto-find tesseract (Docker) or allow override via env.
pytesseract.pytesseract.tesseract_cmd = os.getenv("TESSERACT_CMD", "tesseract")

# Canonical order for a day
ORDER = ["ТОНГ", "ҚУЁШ", "ПЕШИН", "АСР", "ШОМ", "ХУФТОН"]

# Display names
PRAYER_NAME_MAP = {
    "ТОНГ": "Fajr",
    "ҚУЁШ": "Sunrise",
    "ПЕШИН": "Dhuhr",
    "АСР": "Asr",
    "ШОМ": "Maghrib",
    "ХУФТОН": "Isha",
}

# Aliases/typos we’ve seen (Cyrillic & Latin Uzbek/English)
ALIASES = {
    "ТОНГ":  ["ТОНГ", "TONG", "T0NG", "TONG'"],
    "ҚУЁШ":  ["ҚУЁШ", "QUYOSH", "QUYOSh", "QUYOШ", "QУЁШ", "QUY0SH"],
    "ПЕШИН": ["ПЕШИН", "PESHIN", "PEШИН", "РЕШИН"],
    "АСР":   ["АСР", "ASR", "ACР"],
    "ШОМ":   ["ШОМ", "Ш0М", "ШОММ", "Ш0Н", "ШОН", "SHOM", "SHAM", "SH0M", "MAGHRIB"],
    "ХУФТОН":["ХУФТОН", "XUFTON", "HUFТОN", "HUFTON", "XUФТОН"],
}

TIME_RE = re.compile(r'\b([01]?\d|2[0-3]):[0-5]\d\b')

def _norm(s: str) -> str:
    """
    Normalize common OCR confusions to improve alias matching.
    """
    s = s.upper()
    # Replace zero with O where it appears in words; keep digits in times
    s = re.sub(r'(?<=\D)0(?=\D)', 'О', s)  # zero between non-digits -> Cyrillic O
    s = s.replace('0', '0')  # keep zeros in times
    # Normalize latin/cyrillic lookalikes a bit
    s = s.replace('A', 'A').replace('C', 'C')  # placeholders; extend if needed
    return s

def extract_text_from_image(image_path: str) -> str:
    img = Image.open(image_path)
    for lang in ["uzb+rus", "rus", "eng"]:
        try:
            return pytesseract.image_to_string(img, lang=lang)
        except Exception:
            continue
    return pytesseract.image_to_string(img)  # last resort

def _hhmm_to_time(hhmm: str) -> dtime | None:
    try:
        h, m = map(int, hhmm.split(":"))
        return dtime(hour=h, minute=m)
    except Exception:
        return None

def _time_in_range(t: dtime, start: dtime, end: dtime) -> bool:
    return (t > start) and (t < end)

def extract_prayer_times(text: str) -> dict:
    """
    Return dict like {"ТОНГ": "05:01", "ҚУЁШ": "06:20", ...}
    Robust to label position and OCR noise; infers missing labels from chronology.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    norm_lines = [_norm(ln) for ln in lines]

    # Pass 1: direct alias + time on same line (label anywhere)
    result: dict[str, str] = {}
    used_times: set[str] = set()
    all_times: set[str] = set()

    # Collect all times present to enable inference later
    for ln in norm_lines:
        for m in TIME_RE.finditer(ln):
            all_times.add(m.group(0))

    # Direct mapping
    for canon, aliases in ALIASES.items():
        if canon in result:
            continue
        for ln in norm_lines:
            if any(a in ln for a in aliases):
                m = TIME_RE.search(ln)
                if m:
                    t = m.group(0)
                    result[canon] = t
                    used_times.add(t)
                    break

    # Pass 2: fuzzy token matching if a label still missing
    if len(result) < len(ORDER):
        for canon, aliases in ALIASES.items():
            if canon in result:
                continue
            best_line = None
            best_score = 0.0
            for ln in norm_lines:
                tokens = re.findall(r'[\wЁЎҚҒҲА-Я]+', ln)
                if not tokens:
                    continue
                # fuzzy against all tokens in line
                for tok in tokens:
                    score = max(difflib.SequenceMatcher(None, tok, a).ratio() for a in aliases)
                    if score > best_score:
                        if TIME_RE.search(ln):
                            best_score = score
                            best_line = ln
            if best_line and best_score >= 0.72:
                m = TIME_RE.search(best_line)
                if m:
                    t = m.group(0)
                    if t not in used_times:
                        result[canon] = t
                        used_times.add(t)

    # Pass 3: infer missing labels from day chronology using all_times
    # Sort all times
    timeline = sorted((_hhmm_to_time(t), t) for t in all_times if _hhmm_to_time(t) is not None)
    index = {k: _hhmm_to_time(v) for k, v in result.items() if _hhmm_to_time(v) is not None}

    def pick_between(after: dtime, before: dtime) -> str | None:
        for tt, raw in timeline:
            if raw in used_times:
                continue
            if _time_in_range(tt, after, before):
                return raw
        return None

    # Infer SHOM/Maghrib if missing and ASR & ХУФТОН exist
    if "ШОМ" not in result and "АСР" in index and "ХУФТОН" in index:
        cand = pick_between(index["АСР"], index["ХУФТОН"])
        if cand:
            result["ШОМ"] = cand
            used_times.add(cand)

    # (Optional) You could add similar inference for ПЕШИН using ҚУЁШ/АСР bounds, etc.

    return result