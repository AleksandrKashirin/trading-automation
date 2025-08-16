#!/usr/bin/env python3
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
    print("
Настройка портфелей для гонки:")
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
    
    print("
✅ Конфигурация сохранена в config/settings.json")
    
    # Тест отправки сообщения
    test = input("
Протестировать отправку сообщения в Telegram? (y/n): ").strip().lower()
    if test == 'y':
        try:
            bot = TelegramBot(config['telegram_token'], config['chat_id'])
            bot.send_message("🤖 Portfolio Telegram Bot настроен и готов к работе!")
            print("✅ Тестовое сообщение отправлено успешно")
        except Exception as e:
            print(f"❌ Ошибка при отправке тестового сообщения: {e}")

if __name__ == "__main__":
    create_config()
