# ---- Dockerfile ----
FROM python:3.11-slim

# System deps (tesseract + languages + tzdata for cron timezones)
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-rus \
    tesseract-ocr-uzb \
    tzdata \
 && rm -rf /var/lib/apt/lists/*

# Let pytesseract find traineddata
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

# Workdir
WORKDIR /app

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

# Gunicorn entry (HTTP health port)
ENV PORT=8080
CMD ["gunicorn", "-w", "1", "-b", "0.0.0.0:8080", "app:create_app()"]