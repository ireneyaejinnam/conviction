FROM python:3.12-slim

# curl is only here for the healthchecks in docker-compose.yml.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 app

WORKDIR /app

# Install deps before copying the code so code changes don't bust this layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=app:app . .

ENV CONVICTION_DATA_DIR=/data \
    PYTHONUNBUFFERED=1

USER app

# 8501: Streamlit (app service), 8000: FastAPI (api service). Healthchecks
# live in docker-compose.yml, one per service.
EXPOSE 8501 8000

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true", "--browser.gatherUsageStats=false"]
