FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    YOLO_CONFIG_DIR=/models/config
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
      libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY app.py /app/app.py
EXPOSE 443 8080
CMD ["python", "/app/app.py"]
