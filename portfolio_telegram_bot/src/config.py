"""Конфигурация и настройки"""
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
