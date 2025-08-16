#!/usr/bin/env python3
"""
Скрипт для создания структуры проекта Portfolio Telegram Bot
"""

import os
import json

def create_project_structure():
    """Создание структуры проекта"""
    
    # Базовая папка проекта
    project_root = "portfolio_telegram_bot"
    
    # Структура папок
    folders = [
        project_root,
        f"{project_root}/src",
        f"{project_root}/data",
        f"{project_root}/data/charts",
        f"{project_root}/config",
        f"{project_root}/logs"
    ]
    
    # Создание папок
    for folder in folders:
        os.makedirs(folder, exist_ok=True)
        print(f"📁 Создана папка: {folder}")
    
    # Файлы с содержимым
    files_content = {
        # Python модули src/
        f"{project_root}/src/__init__.py": "",
        
        f"{project_root}/src/config.py": '''"""Конфигурация и настройки"""
import json
import os
from typing import Dict

class Config:
    def __init__(self, config_path: str = "config/settings.json"):
        self.config_path = config_path
        self.load_config()
    
    def load_config(self):
        """Загрузка конфигурации из JSON файла"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self.TINKOFF_TOKEN = config_data.get('tinkoff_token', '')
            self.TELEGRAM_TOKEN = config_data.get('telegram_token', '')
            self.CHAT_ID = config_data.get('chat_id', 0)
            self.PORTFOLIO_ACCOUNTS = config_data.get('portfolio_accounts', {})
            self.BOT_TRADER_ACCOUNT_ID = config_data.get('bot_trader_account_id', '')
            self.TIMEZONE = config_data.get('timezone', 'Europe/Moscow')
            self.REPORT_TIME = config_data.get('report_time', '11:00')
            self.DATA_DIRECTORY = config_data.get('data_directory', './data')
            self.LOGS_DIRECTORY = config_data.get('logs_directory', './logs')
            
        except FileNotFoundError:
            print(f"⚠️ Файл конфигурации {self.config_path} не найден")
            self._create_default_config()
    
    def _create_default_config(self):
        """Создание конфигурации по умолчанию"""
        self.TINKOFF_TOKEN = ''
        self.TELEGRAM_TOKEN = ''
        self.CHAT_ID = 0
        self.PORTFOLIO_ACCOUNTS = {}
        self.BOT_TRADER_ACCOUNT_ID = ''
        self.TIMEZONE = 'Europe/Moscow'
        self.REPORT_TIME = '11:00'
        self.DATA_DIRECTORY = './data'
        self.LOGS_DIRECTORY = './logs'
''',
        
        f"{project_root}/src/tinkoff_client.py": '''"""Работа с API Тинькофф"""
import logging
from decimal import Decimal
from typing import Dict, Optional
from tinkoff.invest import Client, RequestError
from tinkoff.invest.schemas import MoneyValue, Quotation

logger = logging.getLogger(__name__)

class TinkoffClient:
    def __init__(self, token: str):
        self.token = token
    
    def quotation_to_decimal(self, quotation: Quotation) -> Decimal:
        """Конвертация Quotation в Decimal"""
        return Decimal(str(quotation.units)) + Decimal(str(quotation.nano)) / Decimal("1000000000")
    
    def money_value_to_decimal(self, money: MoneyValue) -> Decimal:
        """Конвертация MoneyValue в Decimal"""
        return Decimal(str(money.units)) + Decimal(str(money.nano)) / Decimal("1000000000")
    
    def get_portfolio_data(self, account_id: str) -> Dict:
        """Получение данных портфеля"""
        # Реализация из portfolio_checker.py
        pass
    
    def get_moex_index_price(self) -> Optional[float]:
        """Получение текущего значения индекса MOEX"""
        # Реализация из portfolio_race_tracker.py
        pass
    
    def get_currency_rates(self) -> Dict[str, float]:
        """Получение курсов валют"""
        pass
''',
        
        f"{project_root}/src/portfolio_analyzer.py": '''"""Анализ отдельного портфеля"""
from typing import Dict, List
from .tinkoff_client import TinkoffClient

class PortfolioAnalyzer:
    def __init__(self, tinkoff_client: TinkoffClient):
        self.client = tinkoff_client
    
    def generate_portfolio_report(self, account_id: str) -> Dict:
        """Генерация отчета по портфелю"""
        pass
    
    def calculate_total_pnl_from_inception(self, account_id: str) -> float:
        """Расчет общей прибыли с момента открытия"""
        pass
    
    def get_positions_near_stop_loss(self, account_id: str) -> List[Dict]:
        """Получение позиций близко к стоп-лоссу"""
        pass
''',
        
        f"{project_root}/src/race_tracker.py": '''"""Отслеживание гонки портфелей"""
import csv
import os
from datetime import date
from typing import Dict, List
from .tinkoff_client import TinkoffClient

class RaceTracker:
    def __init__(self, tinkoff_client: TinkoffClient, data_dir: str = "./data"):
        self.client = tinkoff_client
        self.data_dir = data_dir
        self.history_file = os.path.join(data_dir, "portfolio_race_history.csv")
    
    def update_daily_data(self, portfolio_accounts: Dict[str, str]) -> None:
        """Обновление ежедневных данных"""
        pass
    
    def generate_race_report(self) -> Dict:
        """Генерация отчета о гонке"""
        pass
    
    def create_performance_chart(self) -> str:
        """Создание графика производительности, возвращает путь к PNG"""
        pass
    
    def load_historical_data(self) -> List[Dict]:
        """Загрузка исторических данных"""
        pass
''',
        
        f"{project_root}/src/telegram_bot.py": '''"""Telegram бот"""
import logging
from typing import List
import telegram
from telegram.constants import ParseMode

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str, chat_id: int):
        self.bot = telegram.Bot(token=token)
        self.chat_id = chat_id
    
    def send_message(self, text: str, parse_mode=ParseMode.MARKDOWN) -> None:
        """Отправка сообщения"""
        try:
            self.bot.send_message(
                chat_id=self.chat_id,
                text=text,
                parse_mode=parse_mode
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
    
    def send_photo(self, photo_path: str, caption: str = "") -> None:
        """Отправка фото"""
        try:
            with open(photo_path, 'rb') as photo:
                self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=photo,
                    caption=caption,
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
    
    def send_long_message(self, text: str) -> None:
        """Отправка длинного сообщения с разбивкой"""
        # Разбивка на части по 4096 символов
        max_length = 4096
        for i in range(0, len(text), max_length):
            part = text[i:i + max_length]
            self.send_message(part)
''',
        
        f"{project_root}/src/report_formatter.py": '''"""Форматирование отчетов для Telegram"""
from typing import Dict, List

class ReportFormatter:
    @staticmethod
    def format_portfolio_report(data: Dict) -> str:
        """Форматирование отчета по портфелю для Telegram"""
        pass
    
    @staticmethod
    def format_race_report(data: Dict) -> str:
        """Форматирование отчета о гонке для Telegram"""
        pass
    
    @staticmethod
    def optimize_for_telegram(text: str) -> List[str]:
        """Разбивка длинного текста на части для Telegram"""
        max_length = 4096
        parts = []
        current_part = ""
        
        for line in text.split('\n'):
            if len(current_part) + len(line) + 1 > max_length:
                if current_part:
                    parts.append(current_part.strip())
                current_part = line
            else:
                if current_part:
                    current_part += '\n' + line
                else:
                    current_part = line
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
''',
        
        f"{project_root}/src/scheduler.py": '''"""Планировщик задач"""
import schedule
import time
import logging
from datetime import datetime
import pytz
from .config import Config
from .tinkoff_client import TinkoffClient
from .portfolio_analyzer import PortfolioAnalyzer
from .race_tracker import RaceTracker
from .telegram_bot import TelegramBot
from .report_formatter import ReportFormatter

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, config: Config):
        self.config = config
        self.tinkoff_client = TinkoffClient(config.TINKOFF_TOKEN)
        self.portfolio_analyzer = PortfolioAnalyzer(self.tinkoff_client)
        self.race_tracker = RaceTracker(self.tinkoff_client, config.DATA_DIRECTORY)
        self.telegram_bot = TelegramBot(config.TELEGRAM_TOKEN, config.CHAT_ID)
        self.report_formatter = ReportFormatter()
    
    def run_daily_reports(self) -> None:
        """Запуск ежедневных отчетов"""
        try:
            logger.info("Запуск ежедневных отчетов...")
            
            # Отчет по портфелю "Бот-трейдер"
            portfolio_data = self.portfolio_analyzer.generate_portfolio_report(
                self.config.BOT_TRADER_ACCOUNT_ID
            )
            portfolio_report = self.report_formatter.format_portfolio_report(portfolio_data)
            self.telegram_bot.send_message(portfolio_report)
            
            # Обновление данных гонки
            self.race_tracker.update_daily_data(self.config.PORTFOLIO_ACCOUNTS)
            
            # Отчет о гонке
            race_data = self.race_tracker.generate_race_report()
            race_report = self.report_formatter.format_race_report(race_data)
            self.telegram_bot.send_message(race_report)
            
            # График гонки
            chart_path = self.race_tracker.create_performance_chart()
            if chart_path:
                self.telegram_bot.send_photo(chart_path, "📈 График гонки портфелей")
            
            logger.info("Ежедневные отчеты отправлены успешно")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке отчетов: {e}")
            self.telegram_bot.send_message(f"❌ Ошибка при генерации отчетов: {e}")
    
    def start_daily_scheduler(self) -> None:
        """Запуск планировщика"""
        schedule.every().day.at(self.config.REPORT_TIME).do(self.run_daily_reports)
        
        logger.info(f"Планировщик запущен. Отчеты будут отправляться в {self.config.REPORT_TIME}")
        
        while True:
            schedule.run_pending()
            time.sleep(60)
''',
        
        f"{project_root}/src/utils.py": '''"""Вспомогательные функции"""
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
''',
        
        # Основные файлы проекта
        f"{project_root}/main.py": '''#!/usr/bin/env python3
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
        print("\n🛑 Бот остановлен")

if __name__ == "__main__":
    main()
''',
        
        f"{project_root}/setup_bot.py": '''#!/usr/bin/env python3
"""
Интерактивная настройка Portfolio Telegram Bot
"""

import json
import os
from src.telegram_bot import TelegramBot

def create_config():
    """Создание файла конфигурации"""
    print("🔧 Настройка Portfolio Telegram Bot")
    print("=" * 50)
    
    config = {}
    
    # Токен Тинькофф
    config['tinkoff_token'] = input("Введите токен Тинькофф Инвестиций: ").strip()
    
    # Токен Telegram бота
    config['telegram_token'] = input("Введите токен Telegram бота: ").strip()
    
    # Chat ID
    try:
        config['chat_id'] = int(input("Введите Chat ID Telegram: ").strip())
    except ValueError:
        print("❌ Неверный формат Chat ID")
        return
    
    # ID счета бот-трейдера
    config['bot_trader_account_id'] = input("Введите ID счета 'Бот-трейдер': ").strip()
    
    # Портфели для гонки
    print("\nНастройка портфелей для гонки:")
    portfolios = {}
    portfolio_names = ["Бот-трейдер", "Инвесткопилка", "Надёжный портфель", "Стандартный счет"]
    
    for name in portfolio_names:
        account_id = input(f"ID счета '{name}': ").strip()
        if account_id:
            portfolios[name] = account_id
    
    config['portfolio_accounts'] = portfolios
    
    # Остальные настройки
    config['timezone'] = 'Europe/Moscow'
    config['report_time'] = '11:00'
    config['data_directory'] = './data'
    config['logs_directory'] = './logs'
    
    # Сохранение конфигурации
    os.makedirs('config', exist_ok=True)
    with open('config/settings.json', 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    print("\n✅ Конфигурация сохранена в config/settings.json")
    
    # Тест отправки сообщения
    test = input("\nПротестировать отправку сообщения в Telegram? (y/n): ").strip().lower()
    if test == 'y':
        try:
            bot = TelegramBot(config['telegram_token'], config['chat_id'])
            bot.send_message("🤖 Portfolio Telegram Bot настроен и готов к работе!")
            print("✅ Тестовое сообщение отправлено успешно")
        except Exception as e:
            print(f"❌ Ошибка при отправке тестового сообщения: {e}")

if __name__ == "__main__":
    create_config()
''',
        
        # Файлы данных и конфигурации
        f"{project_root}/config/settings.json": json.dumps({
            "tinkoff_token": "YOUR_TINKOFF_TOKEN",
            "telegram_token": "YOUR_BOT_TOKEN",
            "chat_id": 123456789,
            "portfolio_accounts": {
                "Бот-трейдер": "2272101668",
                "Инвесткопилка": "account_id_2",
                "Надёжный портфель": "account_id_3",
                "Стандартный счет": "account_id_4"
            },
            "bot_trader_account_id": "2272101668",
            "timezone": "Europe/Moscow",
            "report_time": "11:00",
            "data_directory": "./data",
            "logs_directory": "./logs"
        }, ensure_ascii=False, indent=2),
        
        f"{project_root}/requirements.txt": '''tinkoff-investments>=0.2.0b0
python-telegram-bot>=20.0
schedule>=1.2.0
matplotlib>=3.5.0
seaborn>=0.11.0
pandas>=1.5.0
pytz>=2023.3
''',
        
        f"{project_root}/.gitignore": '''# === ВАЖНО: Токены и конфиденциальные данные ===
config/settings.json
Tokens/
*.token
*.key
.env
.env.local
*.csv
*.json
*.txt
*.png
data/
logs/

# === Python ===
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# === Виртуальное окружение ===
venv/
env/
ENV/
env.bak/
venv.bak/

# === IDE ===
.vscode/
.idea/
*.swp
*.swo
*~

# === OS ===
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db
desktop.ini

# === Логи и временные файлы ===
*.log
*.tmp
*.bak
*.backup

# === Jupyter Notebooks ===
.ipynb_checkpoints

# === MyPy ===
.mypy_cache/
.dmypy.json
dmypy.json

# === Coverage reports ===
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/

# === Pytest ===
.pytest_cache/
'''
    }
    
    # Создание файлов
    for file_path, content in files_content.items():
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"📄 Создан файл: {file_path}")
        except Exception as e:
            print(f"❌ Ошибка создания файла {file_path}: {e}")
    
    # Создание пустых файлов
    empty_files = [
        f"{project_root}/data/portfolio_race_history.csv"
    ]
    
    for file_path in empty_files:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                pass
            print(f"📄 Создан пустой файл: {file_path}")
        except Exception as e:
            print(f"❌ Ошибка создания файла {file_path}: {e}")

def main():
    """Основная функция"""
    print("🚀 Создание структуры проекта Portfolio Telegram Bot")
    print("=" * 60)
    
    create_project_structure()
    
    print("\n" + "=" * 60)
    print("✅ Структура проекта создана успешно!")
    print("\n📋 Следующие шаги:")
    print("1. cd portfolio_telegram_bot")
    print("2. pip install -r requirements.txt")
    print("3. python setup_bot.py  # Настройка бота")
    print("4. python main.py       # Запуск бота")
    print("\n🔧 Не забудьте настроить токены в config/settings.json")

if __name__ == "__main__":
    main()