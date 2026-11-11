FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
# Tesseract OCR for scanned past-question PDFs (research pipeline).
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN DJANGO_SECRET_KEY=build python manage.py collectstatic --noinput
RUN useradd -m kwado && chown -R kwado /app
USER kwado
EXPOSE 8000
# gthread workers keep SSE tutor streams from blocking other requests.
CMD ["gunicorn", "config.wsgi", "-b", "0.0.0.0:8000", "-k", "gthread", "--workers", "4", "--threads", "8", "--timeout", "180", "--max-requests", "2000", "--max-requests-jitter", "200"]
