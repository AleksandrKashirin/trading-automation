"""Обработчик команд Telegram бота"""
import logging
import threading
import time
from typing import Dict, List, Callable
from .telegram_bot import TelegramBot
from .portfolio_analyzer import PortfolioAnalyzer
from .race_tracker import RaceTracker
from .report_formatter import ReportFormatter
from .config import Config

logger = logging.getLogger(__name__)

class CommandHandler:
    def __init__(self, config: Config, telegram_bot: TelegramBot, 
                 portfolio_analyzer: PortfolioAnalyzer, race_tracker: RaceTracker,
                 report_formatter: ReportFormatter):
        self.config = config
        self.telegram_bot = telegram_bot
        self.portfolio_analyzer = portfolio_analyzer
        self.race_tracker = race_tracker
        self.report_formatter = report_formatter
        
        self.last_update_id = 0
        self.running = False
        self.polling_thread = None
        
        # Регистрация команд
        self.commands = {
            '/start': self._cmd_start,
            '/help': self._cmd_help,
            '/status': self._cmd_status,
            '/portfolio': self._cmd_portfolio,
            '/race': self._cmd_race,
            '/chart': self._cmd_chart,
            '/report': self._cmd_full_report,
        }
        
        # Установка команд в Telegram
        self._setup_bot_commands()
    
    def _setup_bot_commands(self) -> None:
        """Установка списка команд в Telegram"""
        commands_list = [
            {'command': 'start', 'description': '🚀 Запуск бота'},
            {'command': 'help', 'description': '❓ Справка по командам'},
            {'command': 'status', 'description': '📊 Статус системы'},
            {'command': 'portfolio', 'description': '💼 Отчет по портфелю'},
            {'command': 'race', 'description': '🏁 Отчет о гонке'},
            {'command': 'chart', 'description': '📈 График гонки'},
            {'command': 'report', 'description': '📋 Полный отчет'},
        ]
        
        if self.telegram_bot.set_commands(commands_list):
            logger.info("Команды бота установлены")
        else:
            logger.warning("Не удалось установить команды бота")
    
    def start_polling(self) -> None:
        """Запуск polling для обработки команд"""
        if self.running:
            logger.warning("Polling уже запущен")
            return
        
        self.running = True
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        
        logger.info("Command handler polling запущен")
    
    def stop_polling(self) -> None:
        """Остановка polling"""
        self.running = False
        if self.polling_thread:
            self.polling_thread.join(timeout=5)
        logger.info("Command handler polling остановлен")
    
    def _polling_loop(self) -> None:
        """Основной цикл получения обновлений"""
        while self.running:
            try:
                updates = self.telegram_bot.get_updates(
                    offset=self.last_update_id + 1,
                    timeout=30
                )
                
                if updates.get('ok') and updates.get('result'):
                    for update in updates['result']:
                        self._process_update(update)
                        self.last_update_id = update['update_id']
                
                time.sleep(1)  # Небольшая пауза между запросами
                
            except Exception as e:
                logger.error(f"Ошибка в polling loop: {e}")
                time.sleep(5)  # Пауза при ошибке
    
    def _process_update(self, update: dict) -> None:
        """Обработка одного обновления"""
        try:
            message = update.get('message', {})
            if not message:
                return
            
            chat_id = message.get('chat', {}).get('id')
            user_id = message.get('from', {}).get('id')
            text = message.get('text', '').strip()
            
            # Проверяем, что сообщение из нужного чата
            if chat_id != self.config.CHAT_ID:
                logger.warning(f"Сообщение из неизвестного чата: {chat_id}")
                return
            
            # Логируем команду
            username = message.get('from', {}).get('username', 'Unknown')
            logger.info(f"Команда от @{username}: {text}")
            
            # Обрабатываем команду
            if text.startswith('/'):
                command = text.split()[0].lower()
                if command in self.commands:
                    self.commands[command](message)
                else:
                    self._cmd_unknown(message, command)
            
        except Exception as e:
            logger.error(f"Ошибка обработки обновления: {e}")
    
    def _cmd_start(self, message: dict) -> None:
        """Команда /start"""
        welcome_text = [
            "🤖 *PORTFOLIO TELEGRAM BOT*",
            "",
            "Добро пожаловать! Я буду отправлять ежедневные отчеты о ваших портфелях.",
            "",
            "*Доступные команды:*",
            "📊 /status - статус системы",
            "💼 /portfolio - отчет по портфелю",
            "🏁 /race - отчет о гонке",
            "📈 /chart - график гонки",
            "📋 /report - полный отчет",
            "❓ /help - справка",
            "",
            f"⏰ Автоматические отчеты: {self.config.REPORT_TIME}",
            f"🌍 Часовой пояс: {self.config.TIMEZONE}"
        ]
        
        self.telegram_bot.send_message("\n".join(welcome_text))
    
    def _cmd_help(self, message: dict) -> None:
        """Команда /help"""
        help_text = [
            "❓ *СПРАВКА ПО КОМАНДАМ*",
            "",
            "📊 `/status` - показать статус системы и время следующего отчета",
            "",
            "💼 `/portfolio` - получить отчет по портфелю Бот-трейдер",
            "• Общий капитал и P&L",
            "• Текущие позиции",
            "• Позиции близко к стоп-лоссу",
            "",
            "🏁 `/race` - отчет о гонке портфелей",
            "• Рейтинг всех портфелей",
            "• Сравнение с MOEX",
            "• Изменения за день",
            "",
            "📈 `/chart` - график динамики гонки",
            "",
            "📋 `/report` - полный отчет (портфель + гонка + график)",
            "",
            "*Автоматические отчеты:*",
            f"Бот автоматически отправляет отчеты каждый день в {self.config.REPORT_TIME}"
        ]
        
        self.telegram_bot.send_message("\n".join(help_text))
    
    def _cmd_status(self, message: dict) -> None:
        """Команда /status"""
        try:
            import schedule
            from datetime import datetime
            
            next_run = schedule.next_run()
            now = datetime.now()
            
            # Проверяем доступность API
            moex_price = self.race_tracker.client.get_moex_index_price()
            api_status = "✅ Доступен" if moex_price else "❌ Недоступен"
            
            status_lines = [
                "📊 *СТАТУС СИСТЕМЫ*",
                "",
                f"🤖 Бот: Активен",
                f"🔗 Tinkoff API: {api_status}",
                f"📱 Telegram API: ✅ Работает",
                "",
                f"⏰ Текущее время: {now.strftime('%d.%m.%Y %H:%M:%S')}",
                f"📅 Следующий отчет: {next_run.strftime('%d.%m.%Y %H:%M')}",
                f"🌍 Часовой пояс: {self.config.TIMEZONE}",
                "",
                f"📊 Портфелей в гонке: {len(self.config.PORTFOLIO_ACCOUNTS)}",
                f"💼 Основной портфель: {self.config.BOT_TRADER_ACCOUNT_ID[-4:]}...{self.config.BOT_TRADER_ACCOUNT_ID[-4:]}" if self.config.BOT_TRADER_ACCOUNT_ID else "Не настроен",
            ]
            
            if moex_price:
                status_lines.extend([
                    "",
                    f"📈 MOEX: {moex_price:.2f} пунктов"
                ])
            
            self.telegram_bot.send_message("\n".join(status_lines))
            
        except Exception as e:
            error_text = self.report_formatter.format_error_report(str(e), "Статус системы")
            self.telegram_bot.send_message(error_text)
    
    def _cmd_portfolio(self, message: dict) -> None:
        """Команда /portfolio"""
        try:
            if not self.config.BOT_TRADER_ACCOUNT_ID:
                self.telegram_bot.send_message("❌ Портфель Бот-трейдер не настроен")
                return
            
            self.telegram_bot.send_message("📊 Генерирую отчет по портфелю...")
            
            # Получаем данные портфеля
            portfolio_data = self.portfolio_analyzer.generate_portfolio_report(
                self.config.BOT_TRADER_ACCOUNT_ID
            )
            
            # Форматируем и отправляем
            portfolio_report = self.report_formatter.format_portfolio_report(portfolio_data)
            self.telegram_bot.send_message(portfolio_report)
            
        except Exception as e:
            error_text = self.report_formatter.format_error_report(str(e), "Отчет по портфелю")
            self.telegram_bot.send_message(error_text)
    
    def _cmd_race(self, message: dict) -> None:
        """Команда /race"""
        try:
            if not self.config.PORTFOLIO_ACCOUNTS:
                self.telegram_bot.send_message("❌ Портфели для гонки не настроены")
                return
            
            self.telegram_bot.send_message("🏁 Генерирую отчет о гонке...")
            
            # Получаем данные гонки
            race_data = self.race_tracker.generate_race_report()
            
            # Форматируем и отправляем
            race_report = self.report_formatter.format_race_report(race_data)
            self.telegram_bot.send_message(race_report)
            
        except Exception as e:
            error_text = self.report_formatter.format_error_report(str(e), "Отчет о гонке")
            self.telegram_bot.send_message(error_text)
    
    def _cmd_chart(self, message: dict) -> None:
        """Команда /chart"""
        try:
            self.telegram_bot.send_message("📈 Создаю график гонки...")
            
            # Создаем график
            chart_path = self.race_tracker.create_performance_chart()
            
            if chart_path:
                caption = "📈 График гонки портфелей"
                self.telegram_bot.send_photo(chart_path, caption)
            else:
                self.telegram_bot.send_message("📊 График недоступен (недостаточно данных для построения)")
                
        except Exception as e:
            error_text = self.report_formatter.format_error_report(str(e), "График гонки")
            self.telegram_bot.send_message(error_text)
    
    def _cmd_full_report(self, message: dict) -> None:
        """Команда /report - полный отчет"""
        try:
            self.telegram_bot.send_message("📋 Генерирую полный отчет...")
            
            # 1. Отчет по портфелю
            if self.config.BOT_TRADER_ACCOUNT_ID:
                portfolio_data = self.portfolio_analyzer.generate_portfolio_report(
                    self.config.BOT_TRADER_ACCOUNT_ID
                )
                portfolio_report = self.report_formatter.format_portfolio_report(portfolio_data)
                self.telegram_bot.send_message(portfolio_report)
                time.sleep(1)  # Небольшая пауза между сообщениями
            
            # 2. Отчет о гонке
            if self.config.PORTFOLIO_ACCOUNTS:
                race_data = self.race_tracker.generate_race_report()
                race_report = self.report_formatter.format_race_report(race_data)
                self.telegram_bot.send_message(race_report)
                time.sleep(1)
            
            # 3. График
            chart_path = self.race_tracker.create_performance_chart()
            if chart_path:
                caption = "📈 График гонки портфелей"
                self.telegram_bot.send_photo(chart_path, caption)
            
            self.telegram_bot.send_message("✅ Полный отчет готов!")
            
        except Exception as e:
            error_text = self.report_formatter.format_error_report(str(e), "Полный отчет")
            self.telegram_bot.send_message(error_text)
    
    def _cmd_unknown(self, message: dict, command: str) -> None:
        """Обработка неизвестной команды"""
        unknown_text = [
            f"❓ Неизвестная команда: `{command}`",
            "",
            "Доступные команды:",
            "• /help - справка",
            "• /status - статус системы",
            "• /portfolio - отчет по портфелю",
            "• /race - отчет о гонке",
            "• /chart - график гонки",
            "• /report - полный отчет"
        ]
        
        self.telegram_bot.send_message("\n".join(unknown_text))