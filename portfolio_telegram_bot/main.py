#!/usr/bin/env python3
"""
Точка входа для Portfolio Telegram Bot
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.config import Config
from src.scheduler import Scheduler
from src.utils import setup_logging

def main():
    """Основная функция"""
    # Загрузка конфигурации
    config = Config()
    
    # Настройка логирования
    setup_logging(config.LOGS_DIRECTORY)
    
    # Проверка обязательных настроек
    if not config.TINKOFF_TOKEN or not config.TELEGRAM_TOKEN:
        print("❌ Ошибка: Не настроены токены. Запустите setup_bot.py")
        return
    
    # Запуск планировщика
    scheduler = Scheduler(config)
    
    print("🤖 Portfolio Telegram Bot запущен")
    print(f"⏰ Отчеты будут отправляться в {config.REPORT_TIME}")
    print("Для остановки нажмите Ctrl+C")
    
    try:
        scheduler.start_daily_scheduler()
    except KeyboardInterrupt:
        print("
🛑 Бот остановлен")

if __name__ == "__main__":
    main()
