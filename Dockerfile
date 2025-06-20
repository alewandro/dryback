FROM python:3.11-slim

WORKDIR /app

COPY . /app

# Instalar curl y iputils-ping
RUN apt-get update && apt-get install -y curl iputils-ping \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

EXPOSE 9999

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9999"]