FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-client libreoffice-impress poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY app ./app

EXPOSE 8000
CMD ["sh", "-c", "python -m app.database.init_db && exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
