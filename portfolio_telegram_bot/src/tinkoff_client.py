"""Работа с API Тинькофф"""
import logging
import time
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from tinkoff.invest import Client, RequestError
from tinkoff.invest.schemas import MoneyValue, Quotation

logger = logging.getLogger(__name__)

class TinkoffClient:
    def __init__(self, token: str):
        self.token = token
        self._currency_cache = {}
        self._cache_expiry = {}
        self.cache_duration = 3600  # 60 минут
    
    def quotation_to_decimal(self, quotation: Quotation) -> Decimal:
        """Конвертация Quotation в Decimal"""
        return Decimal(str(quotation.units)) + Decimal(str(quotation.nano)) / Decimal("1000000000")
    
    def money_value_to_decimal(self, money: MoneyValue) -> Decimal:
        """Конвертация MoneyValue в Decimal"""
        return Decimal(str(money.units)) + Decimal(str(money.nano)) / Decimal("1000000000")
    
    def get_currency_rates(self) -> Dict[str, float]:
        """Получение курсов валют с кэшированием"""
        now = time.time()
        
        # Проверяем кэш
        if (self._currency_cache and 
            self._cache_expiry.get('currency', 0) > now):
            return self._currency_cache.copy()
        
        rates = {"RUB": 1.0}
        
        try:
            with Client(self.token) as client:
                # USD/RUB
                try:
                    usd_response = client.market_data.get_last_prices(figi=["BBG0013HGFT4"])
                    if usd_response.last_prices:
                        rates["USD"] = float(self.quotation_to_decimal(usd_response.last_prices[0].price))
                except RequestError:
                    rates["USD"] = 90.0  # Fallback
                
                # EUR/RUB
                try:
                    eur_response = client.market_data.get_last_prices(figi=["BBG0013HJJ31"])
                    if eur_response.last_prices:
                        rates["EUR"] = float(self.quotation_to_decimal(eur_response.last_prices[0].price))
                except RequestError:
                    rates["EUR"] = 100.0  # Fallback
                
                # Обновляем кэш
                self._currency_cache = rates.copy()
                self._cache_expiry['currency'] = now + self.cache_duration
                
        except Exception as e:
            logger.warning(f"Ошибка получения курсов валют: {e}")
            # Возвращаем кэш или дефолтные значения
            if self._currency_cache:
                return self._currency_cache.copy()
            rates.update({"USD": 90.0, "EUR": 100.0})
        
        return rates
    
    def get_moex_index_price(self) -> Optional[float]:
        """Получение текущего значения индекса MOEX"""
        try:
            with Client(self.token) as client:
                moex_figi = "BBG004730ZJ9"
                response = client.market_data.get_last_prices(figi=[moex_figi])
                
                if response.last_prices:
                    return float(self.quotation_to_decimal(response.last_prices[0].price))
                
        except RequestError as e:
            logger.error(f"Ошибка получения индекса MOEX: {e}")
        
        return None
    
    def get_portfolio_data(self, account_id: str) -> Dict:
        """Получение полных данных портфеля"""
        try:
            with Client(self.token) as client:
                # Получение портфеля
                portfolio_response = client.operations.get_portfolio(account_id=account_id)
                positions = portfolio_response.positions
                
                # Получение курсов валют
                currency_rates = self.get_currency_rates()
                
                # Получение информации об инструментах
                instruments_info = {}
                figis_for_prices = []
                
                for position in positions:
                    if position.instrument_type in ["share", "bond", "etf"] and position.quantity.units > 0:
                        figi = position.figi
                        figis_for_prices.append(figi)
                        
                        try:
                            if position.instrument_type == "share":
                                instrument_response = client.instruments.share_by(id_type=1, id=figi)
                            elif position.instrument_type == "bond":
                                instrument_response = client.instruments.bond_by(id_type=1, id=figi)
                            elif position.instrument_type == "etf":
                                instrument_response = client.instruments.etf_by(id_type=1, id=figi)
                            
                            instruments_info[figi] = {
                                'ticker': instrument_response.instrument.ticker,
                                'name': instrument_response.instrument.name,
                                'currency': instrument_response.instrument.currency,
                                'type': position.instrument_type,
                            }
                        except RequestError:
                            instruments_info[figi] = {
                                'ticker': f"UNKNOWN_{figi[:8]}",
                                'name': "Unknown instrument", 
                                'currency': 'RUB',
                                'type': position.instrument_type,
                            }
                
                # Получение текущих цен
                current_prices = {}
                if figis_for_prices:
                    try:
                        prices_response = client.market_data.get_last_prices(figi=figis_for_prices)
                        for price in prices_response.last_prices:
                            current_prices[price.figi] = self.quotation_to_decimal(price.price)
                    except RequestError:
                        pass
                
                # Получение стоп-заявок
                stop_orders = {}
                try:
                    stop_orders_response = client.stop_orders.get_stop_orders(account_id=account_id)
                    for order in stop_orders_response.stop_orders:
                        if order.direction.name == "STOP_ORDER_DIRECTION_SELL":
                            stop_orders[order.figi] = self.quotation_to_decimal(order.stop_price)
                except RequestError:
                    pass
                
                # Получение информации о счете
                account_name = "Unknown Account"
                try:
                    accounts_response = client.users.get_accounts()
                    for account in accounts_response.accounts:
                        if account.id == account_id:
                            account_name = account.name
                            break
                except RequestError:
                    pass
                
                # Обработка позиций
                portfolio_positions = []
                total_value_rub = Decimal("0")
                total_pnl_rub = Decimal("0")
                cash_balances = {}
                
                for position in positions:
                    figi = position.figi
                    instrument_type = position.instrument_type
                    quantity = self.quotation_to_decimal(position.quantity)
                    
                    if instrument_type == "currency":
                        # Валютные позиции (наличные)
                        if figi == "RUB000UTSTOM":
                            cash_balances["RUB"] = quantity
                        elif figi == "USD000UTSTOM":
                            cash_balances["USD"] = quantity
                        elif figi == "EUR000UTSTOM":
                            cash_balances["EUR"] = quantity
                        continue
                    
                    if quantity <= 0 or instrument_type not in ["share", "bond", "etf"]:
                        continue
                    
                    instrument_info = instruments_info.get(figi, {})
                    ticker = instrument_info.get('ticker', 'UNKNOWN')
                    currency = instrument_info.get('currency', 'RUB')
                    
                    # Средняя цена покупки
                    avg_price = self.money_value_to_decimal(position.average_position_price)
                    
                    # Текущая цена
                    current_price = current_prices.get(figi, Decimal("0"))
                    
                    # Конвертация в рубли
                    rate = Decimal(str(currency_rates.get(currency, 1.0)))
                    avg_price_rub = avg_price * rate if currency != "RUB" else avg_price
                    current_price_rub = current_price * rate if currency != "RUB" else current_price
                    
                    total_position_value = current_price_rub * quantity
                    position_pnl = total_position_value - (avg_price_rub * quantity)
                    
                    total_value_rub += total_position_value
                    total_pnl_rub += position_pnl
                    
                    stop_loss = stop_orders.get(figi)
                    
                    position_data = {
                        "ticker": ticker,
                        "figi": figi,
                        "instrument_type": instrument_type,
                        "name": instrument_info.get('name', 'Unknown'),
                        "currency": currency,
                        "shares": float(quantity),
                        "cost_basis": float(avg_price),
                        "cost_basis_rub": float(avg_price_rub),
                        "stop_loss": float(stop_loss) if stop_loss else None,
                        "current_price": float(current_price),
                        "current_price_rub": float(current_price_rub),
                        "total_value": float(total_position_value),
                        "pnl": float(position_pnl),
                        "pnl_percent": float((position_pnl / (avg_price_rub * quantity)) * 100) if avg_price_rub * quantity > 0 else 0
                    }
                    
                    portfolio_positions.append(position_data)
                
                # Подсчет общего баланса наличных в рублях
                total_cash_rub = Decimal("0")
                for curr, amount in cash_balances.items():
                    rate = Decimal(str(currency_rates.get(curr, 1.0)))
                    total_cash_rub += amount * rate
                
                total_equity = total_value_rub + total_cash_rub
                
                return {
                    "date": datetime.now().isoformat(),
                    "account_id": account_id,
                    "account_name": account_name,
                    "currency_rates": currency_rates,
                    "positions": portfolio_positions,
                    "summary": {
                        "total_positions_value": float(total_value_rub),
                        "total_pnl": float(total_pnl_rub),
                        "cash_balance_rub": float(total_cash_rub),
                        "cash_balances": {k: float(v) for k, v in cash_balances.items()},
                        "total_equity": float(total_equity),
                        "positions_count": len(portfolio_positions),
                    }
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения портфеля {account_id}: {e}")
            raise
    
    def get_portfolio_value(self, account_id: str) -> Dict:
        """Упрощенное получение стоимости портфеля для гонки"""
        try:
            portfolio_data = self.get_portfolio_data(account_id)
            return {
                "total_equity": portfolio_data["summary"]["total_equity"],
                "positions_value": portfolio_data["summary"]["total_positions_value"], 
                "cash_balance": portfolio_data["summary"]["cash_balance_rub"],
                "positions_count": portfolio_data["summary"]["positions_count"]
            }
        except Exception as e:
            logger.error(f"Ошибка получения стоимости портфеля {account_id}: {e}")
            return None