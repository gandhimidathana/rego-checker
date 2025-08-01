FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    chromium chromium-driver \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN chromium --version && chromedriver --version
ENV CHROME_BIN=/usr/bin/chromium
ENV PATH=$PATH:/usr/bin

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 10000
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:10000", "--timeout", "600"]
