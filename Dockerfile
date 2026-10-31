FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Include every root Python module: the API imports chat_features, learning,
# calculator_bridge, not just the original four files.
COPY *.py ./
COPY lifemap-ai-main ./lifemap-ai-main

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=5173

RUN useradd --create-home --uid 10001 lifemap

USER lifemap
EXPOSE 5173

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "from urllib.request import urlopen; import os; urlopen('http://127.0.0.1:'+os.environ.get('PORT','5173')+'/api/health',timeout=3)"

CMD ["python", "app_server.py"]
