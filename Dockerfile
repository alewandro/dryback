FROM python:3.11-slim

# Instalar curl
RUN apt-get update && \
    apt-get install -y curl && \
    rm -rf /var/lib/apt/lists/*

# Crear y establecer el directorio de trabajo
WORKDIR /app

# Copiar requirements.txt
COPY requirements.txt .

# Instalar dependencias
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Crear directorio para los logs
RUN mkdir -p logs

# Exponer el puerto
EXPOSE 9999

# Comando para ejecutar la aplicación
CMD ["python", "main.py"]