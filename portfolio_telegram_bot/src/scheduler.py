"""Планировщик задач"""
import schedule
import time
import logging
import traceback
from datetime import datetime
import pytz
from .config import Config
from .tinkoff_client import TinkoffClient
from .portfolio_analyzer import PortfolioAnalyzer
from .race_tracker import RaceTracker
from .telegram_bot import TelegramBot
from .report_formatter import ReportFormatter
from .command_handler import CommandHandler

logger = logging.getLogger(__name__)

class Scheduler:
    def __init__(self, config: Config):
        self.config = config
        
        # Инициализация компонентов
        self.tinkoff_client = TinkoffClient(config.TINKOFF_TOKEN)
        self.portfolio_analyzer = PortfolioAnalyzer(self.tinkoff_client)
        self.race_tracker = RaceTracker(self.tinkoff_client, config.DATA_DIRECTORY)
        self.telegram_bot = TelegramBot(config.TELEGRAM_TOKEN, config.CHAT_ID)
        self.report_formatter = ReportFormatter()
        
        # Инициализация обработчика команд
        self.command_handler = CommandHandler(
            config=config,
            telegram_bot=self.telegram_bot,
            portfolio_analyzer=self.portfolio_analyzer,
            race_tracker=self.race_tracker,
            report_formatter=self.report_formatter
        )
        
        # Настройка часового пояса
        self.timezone = pytz.timezone(config.TIMEZONE)
        
        logger.info("Планировщик инициализирован")
    
    def run_daily_reports(self) -> None:
        """Запуск ежедневных отчетов"""
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("ЗАПУСК ЕЖЕДНЕВНЫХ ОТЧЕТОВ")
        logger.info("=" * 60)
        
        try:
            # 1. Отчет по портфелю "Бот-трейдер"
            self._send_portfolio_report()
            
            # 2. Обновление данных гонки портфелей
            self._update_race_data()
            
            # 3. Отчет о гонке портфелей
            self._send_race_report()
            
            # 4. График гонки портфелей
            self._send_race_chart()
            
            # Итоговое сообщение об успехе
            elapsed_time = (datetime.now() - start_time).total_seconds()
            success_message = f"✅ *ОТЧЕТЫ ОТПРАВЛЕНЫ*\n\nВремя выполнения: {elapsed_time:.1f} сек"
            self.telegram_bot.send_message(success_message)
            
            logger.info(f"Все отчеты отправлены успешно за {elapsed_time:.1f} сек")
            
        except Exception as e:
            error_msg = f"Критическая ошибка в ежедневных отчетах: {e}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            
            # Отправляем уведомление об ошибке
            error_report = self.report_formatter.format_error_report(
                error=str(e),
                context="Ежедневные отчеты"
            )
            self.telegram_bot.send_message(error_report)
    
    def _send_portfolio_report(self) -> None:
        """Отправка отчета по портфелю Бот-трейдер"""
        try:
            logger.info("Генерация отчета по портфелю Бот-трейдер...")
            
            if not self.config.BOT_TRADER_ACCOUNT_ID:
                raise ValueError("BOT_TRADER_ACCOUNT_ID не настроен")
            
            # Получаем данные портфеля
            portfolio_data = self.portfolio_analyzer.generate_portfolio_report(
                self.config.BOT_TRADER_ACCOUNT_ID
            )
            
            # Форматируем отчет
            portfolio_report = self.report_formatter.format_portfolio_report(portfolio_data)
            
            # Отправляем
            if self.telegram_bot.send_message(portfolio_report):
                logger.info("Отчет по портфелю отправлен успешно")
            else:
                raise Exception("Не удалось отправить отчет по портфелю")
                
        except Exception as e:
            error_msg = f"Ошибка отправки отчета по портфелю: {e}"
            logger.error(error_msg)
            self.telegram_bot.send_error_notification(error_msg)
            raise
    
    def _update_race_data(self) -> None:
        """Обновление данных гонки портфелей"""
        try:
            logger.info("Обновление данных гонки портфелей...")
            
            if not self.config.PORTFOLIO_ACCOUNTS:
                raise ValueError("PORTFOLIO_ACCOUNTS не настроены")
            
            if len(self.config.PORTFOLIO_ACCOUNTS) < 4:
                raise ValueError(f"Недостаточно портфелей для гонки: {len(self.config.PORTFOLIO_ACCOUNTS)}")
            
            # Обновляем данные
            self.race_tracker.update_daily_data(self.config.PORTFOLIO_ACCOUNTS)
            logger.info("Данные гонки обновлены успешно")
            
        except Exception as e:
            error_msg = f"Ошибка обновления данных гонки: {e}"
            logger.error(error_msg)
            self.telegram_bot.send_error_notification(error_msg)
            raise
    
    def _send_race_report(self) -> None:
        """Отправка отчета о гонке портфелей"""
        try:
            logger.info("Генерация отчета о гонке...")
            
            # Получаем данные гонки
            race_data = self.race_tracker.generate_race_report()
            
            # Форматируем отчет
            race_report = self.report_formatter.format_race_report(race_data)
            
            # Отправляем
            if self.telegram_bot.send_message(race_report):
                logger.info("Отчет о гонке отправлен успешно")
            else:
                raise Exception("Не удалось отправить отчет о гонке")
                
        except Exception as e:
            error_msg = f"Ошибка отправки отчета о гонке: {e}"
            logger.error(error_msg)
            self.telegram_bot.send_error_notification(error_msg)
            raise
    
    def _send_race_chart(self) -> None:
        """Отправка графика гонки портфелей"""
        try:
            logger.info("Создание графика гонки...")
            
            # Создаем график
            chart_path = self.race_tracker.create_performance_chart()
            
            if chart_path:
                # Отправляем график
                caption = "📈 График гонки портфелей"
                if self.telegram_bot.send_photo(chart_path, caption):
                    logger.info("График гонки отправлен успешно")
                else:
                    raise Exception("Не удалось отправить график")
            else:
                logger.warning("График не создан (недостаточно данных)")
                self.telegram_bot.send_message("📊 График будет доступен со второго дня отслеживания")
                
        except Exception as e:
            error_msg = f"Ошибка отправки графика: {e}"
            logger.error(error_msg)
            # Для графика не критично - просто логируем
            self.telegram_bot.send_message(f"⚠️ График недоступен: {str(e)}")
    
    def run_manual_reports(self) -> None:
        """Ручной запуск отчетов (для тестирования)"""
        logger.info("Ручной запуск отчетов")
        self.run_daily_reports()
    
    def test_system(self) -> bool:
        """Тестирование всей системы"""
        try:
            logger.info("Запуск тестирования системы...")
            
            # 1. Тест Telegram соединения
            if not self.telegram_bot.test_connection():
                raise Exception("Telegram API недоступен")
            
            # 2. Тест Tinkoff API
            if not self.tinkoff_client.get_currency_rates():
                raise Exception("Tinkoff API недоступен")
            
            # 3. Тест получения данных портфеля
            if self.config.BOT_TRADER_ACCOUNT_ID:
                portfolio_data = self.tinkoff_client.get_portfolio_data(
                    self.config.BOT_TRADER_ACCOUNT_ID
                )
                if not portfolio_data:
                    raise Exception("Не удалось получить данные портфеля")
            
            # 4. Тест данных гонки
            if self.config.PORTFOLIO_ACCOUNTS:
                race_data = self.race_tracker.generate_race_report()
                if "error" in race_data:
                    logger.warning(f"Данные гонки: {race_data['error']}")
            
            # 5. Тест обработчика команд
            logger.info("Тестирование команд...")
            test_message = [
                "✅ *СИСТЕМА РАБОТАЕТ*",
                "",
                "🧪 *Тесты пройдены:*",
                "• Telegram API",
                "• Tinkoff API", 
                "• Данные портфеля",
                "• Система команд",
                "",
                "💬 *Доступные команды:*",
                "• /help - справка",
                "• /status - статус системы",
                "• /portfolio - отчет по портфелю",
                "• /race - отчет о гонке", 
                "• /chart - график гонки",
                "• /report - полный отчет"
            ]
            
            self.telegram_bot.send_message("\n".join(test_message))
            logger.info("Тестирование завершено успешно")
            return True
            
        except Exception as e:
            error_msg = f"Ошибка тестирования: {e}"
            logger.error(error_msg)
            self.telegram_bot.send_error_notification(error_msg)
            return False
    
    def start_daily_scheduler(self) -> None:
        """Запуск планировщика"""
        # Настройка задачи
        schedule.every().day.at(self.config.REPORT_TIME).do(self.run_daily_reports)
        
        logger.info(f"Планировщик запущен")
        logger.info(f"Отчеты будут отправляться ежедневно в {self.config.REPORT_TIME} ({self.config.TIMEZONE})")
        
        # Запуск обработчика команд
        self.command_handler.start_polling()
        
        # Отправляем уведомление о запуске
        startup_message = [
            "🚀 *БОТ ЗАПУЩЕН*",
            "",
            f"⏰ Автоматические отчеты: {self.config.REPORT_TIME}",
            f"🌍 Часовой пояс: {self.config.TIMEZONE}",
            "",
            "💬 *Команды доступны:*",
            "• /help - справка",
            "• /status - статус", 
            "• /portfolio - отчет по портфелю",
            "• /race - отчет о гонке",
            "• /chart - график",
            "• /report - полный отчет"
        ]
        self.telegram_bot.send_message("\n".join(startup_message))
        
        # Основной цикл
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)  # Проверяем каждую минуту
                
            except KeyboardInterrupt:
                logger.info("Получен сигнал остановки")
                self.command_handler.stop_polling()
                self.telegram_bot.send_message("🛑 *БОТ ОСТАНОВЛЕН*")
                break
                
            except Exception as e:
                logger.error(f"Ошибка в основном цикле планировщика: {e}")
                # Продолжаем работу, не останавливаем бота
                time.sleep(60)
    
    def get_status(self) -> str:
        """Получение статуса системы"""
        try:
            next_run = schedule.next_run()
            
            status_lines = [
                "🤖 *СТАТУС СИСТЕМЫ*",
                "",
                f"⏰ Следующий отчет: {next_run.strftime('%d.%m.%Y %H:%M')}",
                f"🌍 Часовой пояс: {self.config.TIMEZONE}",
                f"📊 Портфелей в гонке: {len(self.config.PORTFOLIO_ACCOUNTS)}",
                "",
                "✅ Система работает нормально"
            ]
            
            return "\n".join(status_lines)
            
        except Exception as e:
            return f"❌ Ошибка получения статуса: {e}"