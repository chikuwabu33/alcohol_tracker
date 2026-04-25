FROM python:3.12-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser && chown -R appuser /app

COPY requirements_frontend.txt .
RUN pip install --no-cache-dir -r requirements_frontend.txt

COPY --chown=appuser:appuser ./app /app
USER appuser
ENV PYTHONPATH=/app
EXPOSE 8501
CMD ["streamlit", "run", "src/frontend.py", "--server.port", "8501", "--server.address", "0.0.0.0"]