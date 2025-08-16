"""Telegram бот"""
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
