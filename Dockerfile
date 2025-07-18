# Use slim Python base
FROM python:3.10-slim

# Prevent prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget curl unzip gnupg ca-certificates \
    chromium chromium-driver \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables for Chrome
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

# Create app directory
WORKDIR /app

# Copy app files
COPY . .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 10000

# Start with Gunicorn, increase timeout to 600s to avoid timeout errors
CMD ["gunicorn", "app:app", "--workers=1", "--timeout=600", "--bind=0.0.0.0:10000"]
