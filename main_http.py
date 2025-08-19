import os
import json
import logging
from datetime import datetime
from typing import Any, Dict
import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import time
from klines_handler import KlinesHandler

# Configuración de logging
logging.basicConfig(level=logging.INFO)
request_logger = logging.getLogger('request_logger')
error_logger = logging.getLogger('error_logger')

# Configurar handlers para los archivos de log
request_handler = logging.FileHandler('logs/requests.log')
error_handler = logging.FileHandler('logs/errors.log')
error_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
error_handler.setFormatter(error_formatter)

request_logger.addHandler(request_handler)
error_logger.addHandler(error_handler)

# Cargar configuración
with open('config.json', 'r') as f:
    config = json.load(f)

app = FastAPI()
start_time = time.time()
klines_handler = KlinesHandler()

# Exception Handler Global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_logger.error(f"Error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"}
    )

# Endpoint de estado
@app.get("/status")
async def get_status():
    uptime = time.time() - start_time
    return {"uptime": uptime, "status": "running"}

# Endpoint de ping
@app.get("/ping")
async def ping():
    return "pong"

# Endpoint para klines
@app.get("/api/v3/klines")
async def get_klines(symbol: str, interval: str):
    try:
        # Registrar la petición
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        request_logger.info(f"{timestamp} - GET /api/v3/klines?symbol={symbol}&interval={interval}")

        # Verificar si el símbolo y el intervalo existen en la configuración
        if (symbol not in config["spot"] or
            interval not in config["spot"][symbol]):
            raise HTTPException(status_code=400,
                             detail="Symbol or interval not found in configuration")
        
        # Obtener la ruta del archivo
        file_path = klines_handler.get_file_path("spot", symbol, interval, config)
        if not file_path:
            raise HTTPException(status_code=404,
                             detail="Data file not found")

        # Obtener la siguiente kline
        kline_data = klines_handler.get_next_kline(file_path)
        if not kline_data:
            raise HTTPException(status_code=404,
                             detail="No more kline data available")

        return kline_data
    
    except HTTPException:
        raise
    except Exception as e:
        error_logger.error(f"Error in klines endpoint: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Proxy general para Binance
@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_to_binance(request: Request, full_path: str):
    # Registrar la petición
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    request_logger.info(f"{timestamp} - {request.method} /{full_path}")
    
    # Construir la URL de Binance
    binance_url = f"https://api.binance.com/{full_path}"
    
    try:
        # Obtener los query parameters
        params = dict(request.query_params)
        
        # Realizar la petición a Binance sin enviar los headers originales
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=binance_url,
                params=params
            )
            
            try:
                content = response.json()
            except ValueError:
                content = response.text

            return JSONResponse(
                content={"data": content},
                status_code=response.status_code
            )
            
    except Exception as e:
        error_logger.error(f"Error in proxy: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    import uvicorn
    
    # Asegurar que existe el directorio data
    if not os.path.exists('data'):
        os.makedirs('data')
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8888  # Puerto diferente para distinguir del servidor HTTPS
    )