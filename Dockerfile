# Use slim Python base
FROM python:3.10-slim

# Prevent prompts and enable real-time logging
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Set environment variables for Chrome
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Install system dependencies (added more for headless Chrome stability)
RUN apt-get update && apt-get install -y \
    wget curl unzip gnupg ca-certificates \
    chromium chromium-driver \
    fonts-liberation \
    libnss3 libgbm1 libasound2 libatk1.0-0 libatk-bridge2.0-0 \
    libcairo2 libcups2 libdbus-1-3 libexpat1 libfontconfig1 \
    libgcc1 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 libnspr4 \
    libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 \
    libxcb1 libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 \
    libxi6 libxrandr2 libxrender1 libxtst6 \
    && rm -rf /var/lib/apt/lists/*  # Clean up in the same layer for smaller image

# Create app directory
WORKDIR /app

# Copy app files
COPY . .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (optional, Render uses $PORT anyway)
EXPOSE 10000

# Start with Gunicorn, use dynamic $PORT, increase timeout
CMD ["gunicorn", "app:app", "--workers=1", "--timeout=600", "--bind=0.0.0.0:$PORT", "--log-level=debug"]
