FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY docs /app/docs

RUN pip install --upgrade pip && pip install -e .

RUN useradd --create-home --shell /bin/bash appuser && chown -R appuser:appuser /app
USER appuser

CMD ["key-point-extractor-api"]
