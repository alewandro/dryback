import os
import json
import csv
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
from typing import Dict
from pathlib import Path

app = FastAPI()
DATA_DIR = Path(__file__).parent / "data"
CONFIG_PATH = Path(__file__).parent / "config.json"
LOG_FILE = Path(__file__).parent / "logs/consultas.log"
ERROR_LOG_FILE = Path(__file__).parent / "logs/error.log"

# Asegurarse de que los directorios existen
DATA_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Configurar logging

import logging
logging.basicConfig(
    filename=ERROR_LOG_FILE,
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
# Manejo de errores global
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    # logging.error(f"Unhandled error: {exc}", exc_info=True)
    logging.error(f"{request.method} {request.url.path} {dict(request.query_params)} - {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
    )

# CORS y middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Logging middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        with open(LOG_FILE, "a") as f:
            f.write(f"[{request.method}] {request.url.path} {dict(request.query_params)}\n")
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            with open(ERROR_LOG_FILE, "a") as ef:
                ef.write(f"[{request.method}] {request.url.path} {dict(request.query_params)} ERROR: {str(e)}\n")
            raise

app.add_middleware(LoggingMiddleware)

# Cargar config
with open(CONFIG_PATH) as f:
    config = json.load(f)

# Diccionario de iteradores por par
csv_iterators: Dict[str, csv.reader] = {}

def get_csv_iterator(symbol: str):
    if symbol not in config:
        return None
    if symbol not in csv_iterators:
        csv_path = DATA_DIR / config[symbol]
        if not csv_path.exists():
            return None
        f = open(csv_path, newline='')
        reader = csv.reader(f)
        csv_iterators[symbol] = (reader, f)
    return csv_iterators[symbol][0]

def close_all_iterators():
    for reader, f in csv_iterators.values():
        f.close()

@app.get("/api/v3/klines")
async def get_klines(symbol: str):
    iterator = get_csv_iterator(symbol)
    if not iterator:
        return JSONResponse({"error": f"Symbol {symbol} not found"}, status_code=404)
    try:
        row = next(iterator)
        # Devuelve la fila como lista de valores 
        return [row]
    except StopIteration:
        return JSONResponse({"error": "No more data"}, status_code=404)

@app.get("/status")
async def status():
    import time
    return {"uptime ": time.time() - os.getpid()}

@app.get("/ping")
async def ping():
    return {"pong /n"}

# Proxy para otras rutas
@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"])
async def proxy(request: Request, full_path: str):
    url = f"https://api.binance.com/{full_path}"
    method = request.method
    headers = dict(request.headers)
    data = await request.body()
    async with httpx.AsyncClient() as client:
        resp = await client.request(method, url, headers=headers, content=data, params=request.query_params)
        return Response(content=resp.content, status_code=resp.status_code, headers=resp.headers)

import atexit
atexit.register(close_all_iterators)

# Para correr: uvicorn dryback.main:app --host 0.0.0.0 --port 9999