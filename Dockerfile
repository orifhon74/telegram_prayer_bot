# --- Dockerfile ---
FROM python:3.11-slim

# System deps for Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr libtesseract-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# By default run with gunicorn (Flask app)
# Railway will inject PORT
CMD exec gunicorn -w 1 -b 0.0.0.0:${PORT:-5000} app:create_app