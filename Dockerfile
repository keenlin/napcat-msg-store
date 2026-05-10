FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY src/ ./src/

RUN pip install --no-cache-dir . && rm -rf src/

ENV PYTHONUNBUFFERED=1

EXPOSE 8788

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8788/health')" || exit 1

ENTRYPOINT ["python", "-m", "napcat_msg_store.main"]
