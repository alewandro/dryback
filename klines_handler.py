import os
import csv
from typing import List, Dict, Optional
import logging

class KlinesHandler:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self.file_positions: Dict[str, int] = {}  # Mantiene la posición actual de cada archivo
        self.logger = logging.getLogger('error_logger')

    def get_file_path(self, market: str, symbol: str, interval: str, config: Dict) -> Optional[str]:
        try:
            file_name = config[market][symbol][interval]
            return os.path.join(self.data_dir, file_name)
        except KeyError:
            self.logger.error(f"Configuration not found for {market}/{symbol}/{interval}")
            return None

    def get_next_kline(self, file_path: str) -> Optional[List]:
        """
        Lee la siguiente línea del archivo CSV y la devuelve como una lista de valores OHLCV.
        Mantiene el seguimiento de la posición actual en el archivo.
        """
        try:
            if file_path not in self.file_positions:
                self.file_positions[file_path] = 0

            if not os.path.exists(file_path):
                self.logger.error(f"File not found: {file_path}")
                return None

            with open(file_path, 'r') as f:
                csv_reader = csv.reader(f)
                
                # Avanzar hasta la última posición leída
                for _ in range(self.file_positions[file_path]):
                    next(csv_reader, None)

                # Leer la siguiente línea
                row = next(csv_reader, None)
                if row:
                    self.file_positions[file_path] += 1
                    # Convertir valores numéricos
                    return [
                        int(row[0]),     # Open time
                        float(row[1]),   # Open
                        float(row[2]),   # High
                        float(row[3]),   # Low
                        float(row[4]),   # Close
                        float(row[5]),   # Volume
                        int(row[6]),     # Close time
                        float(row[7]),   # Quote asset volume
                        int(row[8]),     # Number of trades
                        float(row[9]),   # Taker buy base asset volume
                        float(row[10]),  # Taker buy quote asset volume
                        float(row[11])   # Ignore
                    ]
                return None

        except Exception as e:
            self.logger.error(f"Error reading kline data: {str(e)}", exc_info=True)
            return None

    def reset_file_position(self, file_path: str):
        """Reinicia la posición de lectura de un archivo específico"""
        self.file_positions[file_path] = 0