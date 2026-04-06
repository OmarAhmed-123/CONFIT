FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend /app

ENV PYTHONUNBUFFERED=1
ENV TRYON_REMOTE_MOCK_HOST=0.0.0.0
ENV TRYON_REMOTE_MOCK_PORT=8011

EXPOSE 8011

CMD ["python", "mock_remote_gpu_server.py"]

