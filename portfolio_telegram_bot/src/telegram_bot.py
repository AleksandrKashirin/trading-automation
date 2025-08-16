"""Telegram бот"""
import logging
from typing import List
import requests

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str, chat_id: int):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}"
    
    def send_message(self, text: str, parse_mode='Markdown') -> None:
        """Отправка сообщения"""
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': parse_mode
            }
            response = requests.post(url, data=data)
            response.raise_for_status()
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения: {e}")
    
    def send_photo(self, photo_path: str, caption: str = "") -> None:
        """Отправка фото"""
        try:
            url = f"{self.api_url}/sendPhoto"
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                data = {
                    'chat_id': self.chat_id,
                    'caption': caption,
                    'parse_mode': 'Markdown'
                }
                response = requests.post(url, files=files, data=data)
                response.raise_for_status()
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
    
    def send_long_message(self, text: str) -> None:
        """Отправка длинного сообщения с разбивкой"""
        max_length = 4096
        for i in range(0, len(text), max_length):
            part = text[i:i + max_length]
            self.send_message(part)