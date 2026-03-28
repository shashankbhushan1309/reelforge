FROM python:3.12-slim

WORKDIR /app

# Upgrade pip
RUN pip install --upgrade pip

# Use existing worker dependencies as baseline
COPY workers/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared models and code
COPY shared/ /app/shared/
COPY services/notify/ /app/services/notify/

CMD ["python", "-m", "services.notify.main"]
