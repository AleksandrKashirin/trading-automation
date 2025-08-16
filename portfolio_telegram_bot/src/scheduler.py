"""Планировщик задач"""
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
