# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем системные зависимости для Playwright
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

# Создаем пользователя
RUN useradd -m -u 1000 appuser

# Создаем рабочую директорию
WORKDIR /app

# Копируем requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright and browsers as appuser
RUN pip install playwright
USER appuser
RUN playwright install chromium
USER root

# Копируем исходный код
COPY src/ ./src/

# Создаем директорию для данных и настраиваем права
RUN mkdir -p /app/data
RUN chown -R appuser:appuser /app

# Устанавливаем переменные окружения
ENV DATA_DIR=/app/data
ENV COOKIES_PATH=/app/data/cookies.json
ENV PYTHONPATH=/app/src

# Переключаемся на пользователя appuser
USER appuser

# Команда по умолчанию
CMD ["python", "src/monitor.py"]
