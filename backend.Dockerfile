FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser && chown -R appuser /app

COPY requirements_backend.txt .
RUN pip install --no-cache-dir -r requirements_backend.txt

COPY --chown=appuser:appuser ./app /app
USER appuser
ENV PYTHONPATH=/app
EXPOSE 8000
CMD ["uvicorn", "src.backend:app", "--host", "0.0.0.0", "--port", "8000"]