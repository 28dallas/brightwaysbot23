FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY .env .env

EXPOSE 8002

CMD ["python", "-m", "uvicorn", "backend.main_new:app", "--host", "0.0.0.0", "--port", "8002"]