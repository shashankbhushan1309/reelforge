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

# Copy shared packages and worker code
COPY shared/ /app/shared/
COPY workers/ /app/workers/

# Copy utility scripts (includes the LUT generator)
COPY scripts/ /app/scripts/

# Generate color-grading LUT files at build time so they exist on disk
# before any assembly worker starts. Output: /app/luts/{moody,warm_cinematic,
# bright_pop,dark_dramatic}.cube  (identity "natural" needs no file).
ENV LUT_DIR=/app/luts
RUN python3 /app/scripts/generate_luts.py

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default: run all workers (overridden per service in docker-compose)
CMD ["celery", "-A", "workers.celery_app", "worker", "--loglevel=info"]
