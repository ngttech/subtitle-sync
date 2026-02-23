FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    gcc \
    g++ \
    python3-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN wget -q https://github.com/kaegi/alass/releases/download/v2.0.0/alass-linux64 \
    -O /usr/local/bin/alass-cli && chmod +x /usr/local/bin/alass-cli

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y --auto-remove gcc g++ python3-dev

COPY . .
RUN mkdir -p /app/data /app/config

ENV SUBTITLE_SYNC_CONFIG_DIR=/app/config
ENV SUBTITLE_SYNC_DATA_DIR=/app/data
ENV SUBTITLE_SYNC_DEV=0

EXPOSE 8765
CMD ["python", "run.py"]
