FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm \
    && rm -rf /var/lib/apt/lists/*

COPY package.json ./
COPY AI_interact.py api_server.py back_end.py front_end.py ./
COPY lifemap-ai-main ./lifemap-ai-main

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LIFEMAP_API_HOST=0.0.0.0 \
    LIFEMAP_OLLAMA_URL=http://host.docker.internal:11434/api/chat

RUN pip install --no-cache-dir pydantic

EXPOSE 5173 8000

CMD ["bash", "-lc", "npm run api & HOST=0.0.0.0 npm run dev"]
