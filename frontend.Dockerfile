FROM python:3.11-slim
WORKDIR /app
COPY requirements_frontend.txt .
RUN pip install --no-cache-dir -r requirements_frontend.txt
COPY ./app /app
EXPOSE 8501
CMD ["streamlit", "run", "src/frontend.py", "--server.port", "8501", "--server.address", "0.0.0.0"]