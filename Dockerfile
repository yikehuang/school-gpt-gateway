FROM mcr.microsoft.com/playwright/python:v1.49.1-jammy

LABEL org.opencontainers.image.title="XJGPT School Gateway"
LABEL org.opencontainers.image.description="ChatGPT-like gateway for XJTLU XipuAI school web GPT"
LABEL org.opencontainers.image.source="https://github.com/yikehuang/school-gpt-gateway"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

COPY . .

RUN python -m pip install --upgrade pip \
    && python -m pip install -e . \
    && playwright install chromium

EXPOSE 8000

CMD ["xjgpt-gateway", "--host", "0.0.0.0", "--port", "8000"]
