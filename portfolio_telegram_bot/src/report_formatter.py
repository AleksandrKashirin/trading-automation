"""Форматирование отчетов для Telegram"""
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
        
        for line in text.split(''):
            if len(current_part) + len(line) + 1 > max_length:
                if current_part:
                    parts.append(current_part.strip())
                current_part = line
            else:
                if current_part:
                    current_part += '' + line
                else:
                    current_part = line
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
