"""Telegram бот"""
import logging
import time
from typing import List
import requests

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token: str, chat_id: int):
        self.token = token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.max_message_length = 4096
        self.max_retries = 3
        self.retry_delay = 2  # секунды
    
    def _make_request(self, method: str, data: dict = None, files: dict = None) -> bool:
        """Выполнение запроса к Telegram API с retry механизмом"""
        url = f"{self.api_url}/{method}"
        
        for attempt in range(self.max_retries):
            try:
                if files:
                    response = requests.post(url, data=data, files=files, timeout=30)
                else:
                    response = requests.post(url, json=data, timeout=30)
                
                response.raise_for_status()
                
                result = response.json()
                if result.get('ok'):
                    return True
                else:
                    logger.warning(f"Telegram API error: {result.get('description')}")
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    logger.error(f"All {self.max_retries} attempts failed for {method}")
                    return False
            
            except Exception as e:
                logger.error(f"Unexpected error in Telegram API call: {e}")
                return False
        
        return False
    
    def send_message(self, text: str, parse_mode='Markdown') -> bool:
        """Отправка сообщения"""
        if not text.strip():
            logger.warning("Попытка отправить пустое сообщение")
            return False
        
        # Если сообщение слишком длинное, разбиваем его
        if len(text) > self.max_message_length:
            return self.send_long_message(text, parse_mode)
        
        data = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        success = self._make_request('sendMessage', data)
        if success:
            logger.info(f"Сообщение отправлено ({len(text)} символов)")
        else:
            logger.error("Не удалось отправить сообщение")
        
        return success
    
    def send_photo(self, photo_path: str, caption: str = "") -> bool:
        """Отправка фото"""
        try:
            with open(photo_path, 'rb') as photo:
                files = {'photo': photo}
                data = {
                    'chat_id': self.chat_id,
                    'caption': caption[:1024] if caption else "",  # Ограничение Telegram
                    'parse_mode': 'Markdown'
                }
                
                success = self._make_request('sendPhoto', data, files)
                if success:
                    logger.info(f"Фото отправлено: {photo_path}")
                else:
                    logger.error(f"Не удалось отправить фото: {photo_path}")
                
                return success
                
        except FileNotFoundError:
            logger.error(f"Файл не найден: {photo_path}")
            return False
        except Exception as e:
            logger.error(f"Ошибка отправки фото: {e}")
            return False
    
    def send_long_message(self, text: str, parse_mode='Markdown') -> bool:
        """Отправка длинного сообщения с корректной разбивкой"""
        if len(text) <= self.max_message_length:
            return self.send_message(text, parse_mode)
        
        parts = self._split_message(text)
        all_sent = True
        
        for i, part in enumerate(parts):
            logger.info(f"Отправка части {i+1}/{len(parts)}")
            
            if not self.send_message(part, parse_mode):
                all_sent = False
                logger.error(f"Не удалось отправить часть {i+1}")
            
            # Небольшая задержка между сообщениями
            if i < len(parts) - 1:
                time.sleep(1)
        
        return all_sent
    
    def _split_message(self, text: str) -> List[str]:
        """Умная разбивка длинного текста на части"""
        if len(text) <= self.max_message_length:
            return [text]
        
        parts = []
        current_part = ""
        
        # Разбиваем по строкам для сохранения форматирования
        lines = text.split('\n')
        
        for line in lines:
            # Если даже одна строка слишком длинная
            if len(line) > self.max_message_length:
                # Сохраняем текущую часть если есть
                if current_part:
                    parts.append(current_part.strip())
                    current_part = ""
                
                # Разбиваем длинную строку по словам
                words = line.split(' ')
                temp_line = ""
                
                for word in words:
                    if len(temp_line + word + " ") > self.max_message_length:
                        if temp_line:
                            parts.append(temp_line.strip())
                        temp_line = word + " "
                    else:
                        temp_line += word + " "
                
                if temp_line:
                    current_part = temp_line.strip()
                continue
            
            # Проверяем, поместится ли строка в текущую часть
            test_part = current_part + "\n" + line if current_part else line
            
            if len(test_part) <= self.max_message_length:
                current_part = test_part
            else:
                # Сохраняем текущую часть и начинаем новую
                if current_part:
                    parts.append(current_part.strip())
                current_part = line
        
        # Добавляем последнюю часть
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    def send_error_notification(self, error_message: str) -> bool:
        """Отправка уведомления об ошибке"""
        error_text = f"❌ *ОШИБКА СИСТЕМЫ*\n\n`{error_message}`\n\n_Время: {time.strftime('%d.%m.%Y %H:%M:%S')}_"
        return self.send_message(error_text)
    
    def test_connection(self) -> bool:
        """Тест соединения с Telegram API"""
        try:
            data = {'chat_id': self.chat_id, 'text': '🤖 Тест соединения'}
            return self._make_request('sendMessage', data)
        except Exception as e:
            logger.error(f"Ошибка тестирования соединения: {e}")
            return False
    
    def get_updates(self, offset: int = 0, timeout: int = 30) -> dict:
        """Получение обновлений от Telegram (для обработки команд)"""
        try:
            url = f"{self.api_url}/getUpdates"
            params = {
                'offset': offset,
                'timeout': timeout,
                'allowed_updates': ['message']
            }
            
            response = requests.get(url, params=params, timeout=timeout + 5)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Ошибка получения обновлений: {e}")
            return {'ok': False, 'result': []}
    
    def set_commands(self, commands: list) -> bool:
        """Установка списка команд бота"""
        try:
            data = {'commands': commands}
            return self._make_request('setMyCommands', data)
        except Exception as e:
            logger.error(f"Ошибка установки команд: {e}")
            return False