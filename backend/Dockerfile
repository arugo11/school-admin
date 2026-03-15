FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/backend \
    APP_DATA_DIR=/app/data \
    FRONTEND_DIST_DIR=/app/frontend_dist

WORKDIR /app

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

COPY backend /app/backend
COPY data /app/data
COPY frontend/dist /app/frontend_dist

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
