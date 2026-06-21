FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

WORKDIR /app

COPY . .

RUN python -m pip install --upgrade pip \
    && python -m pip install -e . \
    && playwright install chromium

EXPOSE 8000

CMD ["xjgpt-gateway", "--host", "0.0.0.0", "--port", "8000"]
