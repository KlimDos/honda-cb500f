# Двухфазная сборка CB500F Monitor

# === ФАЗА 1: Установка зависимостей ===
FROM python:3.11-slim AS deps

# Системные зависимости для Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libxss1 \
    libasound2 \
    libcups2 \
    libxfixes3 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Установка Playwright браузеров
RUN playwright install chromium

# === ФАЗА 2: Приложение ===
FROM python:3.11-slim

# Копируем системные зависимости из первой фазы
COPY --from=deps /usr/lib/x86_64-linux-gnu/ /usr/lib/x86_64-linux-gnu/
COPY --from=deps /usr/share/ca-certificates/ /usr/share/ca-certificates/
COPY --from=deps /etc/ssl/ /etc/ssl/

# Копируем Python пакеты
COPY --from=deps /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=deps /usr/local/bin/ /usr/local/bin/

# Копируем Playwright браузеры
COPY --from=deps /root/.cache/ms-playwright/ /root/.cache/ms-playwright/

# Рабочая директория
WORKDIR /app

# Копируем код приложения
COPY src/ ./src/
COPY src/view_database.py ./view_database.py

# Создаем директорию для данных
RUN mkdir -p /app/data

# Переменные окружения
ENV PYTHONPATH=/app/src
ENV DATA_DIR=/app/data
ENV COOKIES_PATH=/app/data/cookies.json

# Запуск
CMD ["python", "src/monitor.py"]
