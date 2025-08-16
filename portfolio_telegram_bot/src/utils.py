"""Вспомогательные функции"""
import logging
import os
from datetime import datetime

def setup_logging(log_dir: str = "./logs") -> None:
    """Настройка логирования"""
    os.makedirs(log_dir, exist_ok=True)
    
    log_filename = os.path.join(log_dir, f"bot_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )

def ensure_directory_exists(directory: str) -> None:
    """Создание директории если она не существует"""
    os.makedirs(directory, exist_ok=True)
