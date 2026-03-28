FROM python:3.12-slim

WORKDIR /app

COPY services/trend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ /app/shared/
COPY services/trend/ /app/services/trend/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "services.trend.main"]
