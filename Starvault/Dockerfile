FROM node:18-slim

RUN apt-get update && apt-get install -y \
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
ENV BOT_TOKEN_FILE=/run/starvault/bot_token
ENV BOT_HOST=127.0.0.1:3000
ENV APP_HOST=127.0.0.1:5000

WORKDIR /app/web
COPY web/package.json ./
RUN npm install

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
