FROM node:18-slim

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    redis-server \
    redis-tools \
    chromium \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libx11-6 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libxshmfence1 \
    xdg-utils \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium
ENV BOT_HOST=127.0.0.1:3000
ENV APP_HOST=127.0.0.1:5000
ENV REDIS_HOST=127.0.0.1
ENV REDIS_PORT=6379

WORKDIR /app/web
COPY web/requirements.txt ./
RUN python3 -m venv /opt/starlog-venv \
    && /opt/starlog-venv/bin/pip install --no-cache-dir -r requirements.txt

ENV PATH=/opt/starlog-venv/bin:$PATH

WORKDIR /app/bot
COPY bot/package*.json ./
RUN npm install

WORKDIR /app
COPY web ./web
COPY bot ./bot
COPY setup.sh ./setup.sh
RUN chmod +x /app/setup.sh

EXPOSE 5000

CMD ["/app/setup.sh"]
