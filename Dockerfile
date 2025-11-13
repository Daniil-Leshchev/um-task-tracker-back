FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend /app

ENV DJANGO_SETTINGS_MODULE=umtracker.settings

CMD ["uvicorn", "umtracker.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]