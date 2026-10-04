FROM python:3.14.8-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --requirement requirements.txt

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app \
    && chown app:app /app

COPY --chown=app:app app ./app
COPY --chown=app:app config ./config

USER app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
