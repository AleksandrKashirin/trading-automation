"""Работа с API Тинькофф"""
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
