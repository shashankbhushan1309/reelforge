# Workers Dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (ffmpeg, opencv deps, tesseract)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    libgl1-mesa-glx \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY workers/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared packages
COPY shared/ /app/shared/

# Copy worker code
COPY workers/ /app/workers/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default: run all workers (overridden per service in docker-compose)
CMD ["celery", "-A", "workers.celery_app", "worker", "--loglevel=info"]
