# Proxyx — gateway di Docker.
# Perbaikan dari repo asli: CMD memakai perintah yang BENAR-BENAR ADA
# (asli memakai flag --gateway/--port/--background yang tidak ada di CLI).
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt pyproject.toml README.md ./
COPY proxyx/ ./proxyx/
COPY config/ ./config/
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir .
ENV PYTHONUNBUFFERED=1 GATEWAY_PORT=8888
EXPOSE 8888
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://127.0.0.1:8888/api/status || exit 1
CMD ["python", "-m", "proxyx", "gateway", "--port", "8888"]
