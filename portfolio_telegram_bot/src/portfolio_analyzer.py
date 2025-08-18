"""Анализ отдельного портфеля"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List
from tinkoff.invest import Client, RequestError
from tinkoff.invest.schemas import OperationState, OperationType
from .tinkoff_client import TinkoffClient

logger = logging.getLogger(__name__)

class PortfolioAnalyzer:
    def __init__(self, tinkoff_client: TinkoffClient):
        self.client = tinkoff_client
    
    def generate_portfolio_report(self, account_id: str) -> Dict:
        """Генерация отчета по портфелю"""
        try:
            # Получаем базовые данные портфеля
            portfolio_data = self.client.get_portfolio_data(account_id)
            
            # Добавляем дополнительную аналитику
            portfolio_data["analysis"] = {
                "total_pnl_from_inception": self.calculate_total_pnl_from_inception(account_id),
                "positions_near_stop_loss": self.get_positions_near_stop_loss(account_id),
                "best_position": self._get_best_position(portfolio_data["positions"]),
                "worst_position": self._get_worst_position(portfolio_data["positions"]),
            }
            
            return portfolio_data
            
        except Exception as e:
            logger.error(f"Ошибка генерации отчета по портфелю {account_id}: {e}")
            raise
    
    def calculate_total_pnl_from_inception(self, account_id: str) -> Dict[str, float]:
        """Расчет общей прибыли с момента открытия счета"""
        try:
            with Client(self.client.token) as client:
                # Получаем операции с самого начала (максимально доступный период)
                end_date = datetime.now()
                start_date = datetime(2020, 1, 1)  # Начинаем с 2020 года
                
                operations_response = client.operations.get_operations(
                    account_id=account_id,
                    from_=start_date,
                    to=end_date,
                    state=OperationState.OPERATION_STATE_EXECUTED
                )
                
                total_money_in = Decimal("0")     # Общие пополнения
                total_money_out = Decimal("0")    # Общие выводы
                total_dividends = Decimal("0")    # Дивиденды и купоны
                total_commissions = Decimal("0")  # Комиссии
                
                # Анализируем все операции
                for operation in operations_response.operations:
                    payment = self.client.money_value_to_decimal(operation.payment)
                    
                    if operation.operation_type == OperationType.OPERATION_TYPE_INPUT:
                        # Пополнение счета
                        total_money_in += payment
                        
                    elif operation.operation_type == OperationType.OPERATION_TYPE_OUTPUT:
                        # Вывод средств
                        total_money_out += abs(payment)
                        
                    elif operation.operation_type in [
                        OperationType.OPERATION_TYPE_DIVIDEND,
                        OperationType.OPERATION_TYPE_COUPON
                    ]:
                        # Дивиденды и купоны
                        total_dividends += payment
                        
                    elif operation.operation_type in [
                        OperationType.OPERATION_TYPE_BROKER_FEE,
                        OperationType.OPERATION_TYPE_SERVICE_FEE
                    ]:
                        # Комиссии и сборы
                        total_commissions += abs(payment)
                
                # Получаем текущую стоимость портфеля
                portfolio_data = self.client.get_portfolio_data(account_id)
                current_equity = Decimal(str(portfolio_data["summary"]["total_equity"]))
                
                # Правильная формула P&L:
                # P&L = Текущая стоимость + Выведенные средства + Дивиденды - Вложенные средства - Комиссии
                net_invested = total_money_in - total_money_out
                total_pnl = current_equity + total_money_out + total_dividends - total_money_in - total_commissions
                
                return {
                    "total_pnl": float(total_pnl),
                    "money_invested": float(total_money_in),
                    "money_withdrawn": float(total_money_out),
                    "dividends_received": float(total_dividends),
                    "commissions_paid": float(total_commissions),
                    "current_equity": float(current_equity),
                    "net_invested": float(net_invested)
                }
                
        except Exception as e:
            logger.warning(f"Не удалось рассчитать P&L с открытия для {account_id}: {e}")
            # Fallback к текущему P&L из позиций
            try:
                portfolio_data = self.client.get_portfolio_data(account_id)
                return {
                    "total_pnl": portfolio_data["summary"]["total_pnl"],
                    "money_invested": 0,
                    "money_withdrawn": 0,
                    "dividends_received": 0,
                    "commissions_paid": 0,
                    "current_equity": portfolio_data["summary"]["total_equity"],
                    "net_invested": 0
                }
            except:
                return {
                    "total_pnl": 0,
                    "money_invested": 0,
                    "money_withdrawn": 0,
                    "dividends_received": 0,
                    "commissions_paid": 0,
                    "current_equity": 0,
                    "net_invested": 0
                }
    
    def get_trading_history(self, account_id: str, days: int = 30) -> List[Dict]:
        """Получение истории торговых операций"""
        try:
            with Client(self.client.token) as client:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                
                operations_response = client.operations.get_operations(
                    account_id=account_id,
                    from_=start_date,
                    to=end_date,
                    state=OperationState.OPERATION_STATE_EXECUTED
                )
                
                trading_operations = []
                
                for operation in operations_response.operations:
                    if operation.operation_type in [
                        OperationType.OPERATION_TYPE_BUY,
                        OperationType.OPERATION_TYPE_SELL
                    ]:
                        # Получаем информацию об инструменте
                        instrument_name = "Unknown"
                        ticker = "UNKNOWN"
                        
                        try:
                            if operation.instrument_type == "share":
                                instrument = client.instruments.share_by(id_type=1, id=operation.figi)
                            elif operation.instrument_type == "bond":
                                instrument = client.instruments.bond_by(id_type=1, id=operation.figi)
                            elif operation.instrument_type == "etf":
                                instrument = client.instruments.etf_by(id_type=1, id=operation.figi)
                            else:
                                continue
                            
                            instrument_name = instrument.instrument.name
                            ticker = instrument.instrument.ticker
                        except:
                            pass
                        
                        payment = self.client.money_value_to_decimal(operation.payment)
                        quantity = operation.quantity
                        price = abs(payment) / quantity if quantity > 0 else 0
                        
                        trading_operations.append({
                            "date": operation.date.strftime('%d.%m.%Y %H:%M'),
                            "operation_type": "Покупка" if operation.operation_type == OperationType.OPERATION_TYPE_BUY else "Продажа",
                            "ticker": ticker,
                            "instrument_name": instrument_name,
                            "quantity": int(quantity),
                            "price": float(price),
                            "amount": float(abs(payment)),
                            "currency": operation.currency
                        })
                
                # Сортируем по дате (новые первыми)
                trading_operations.sort(key=lambda x: datetime.strptime(x["date"], '%d.%m.%Y %H:%M'), reverse=True)
                
                return trading_operations
                
        except Exception as e:
            logger.error(f"Ошибка получения истории операций: {e}")
            return []
    
    def get_positions_near_stop_loss(self, account_id: str, threshold_percent: float = 5.0) -> List[Dict]:
        """Получение позиций близко к стоп-лоссу"""
        try:
            portfolio_data = self.client.get_portfolio_data(account_id)
            near_stop_loss = []
            
            for position in portfolio_data["positions"]:
                stop_loss = position.get("stop_loss")
                if not stop_loss:
                    continue
                
                current_price = position["current_price_rub"]
                
                # Расчет расстояния до стоп-лосса в процентах
                distance_percent = ((current_price - stop_loss) / current_price) * 100
                
                if 0 <= distance_percent <= threshold_percent:
                    position_info = position.copy()
                    position_info["distance_to_stop_loss_percent"] = round(distance_percent, 2)
                    near_stop_loss.append(position_info)
            
            # Сортируем по расстоянию до стоп-лосса (ближайшие первые)
            near_stop_loss.sort(key=lambda x: x["distance_to_stop_loss_percent"])
            
            return near_stop_loss
            
        except Exception as e:
            logger.error(f"Ошибка поиска позиций близко к стоп-лоссу: {e}")
            return []
    
    def _get_best_position(self, positions: List[Dict]) -> Dict:
        """Получение лучшей позиции по P&L"""
        if not positions:
            return {}
        
        best = max(positions, key=lambda x: x["pnl"])
        return {
            "ticker": best["ticker"],
            "pnl": best["pnl"],
            "pnl_percent": best["pnl_percent"]
        }
    
    def _get_worst_position(self, positions: List[Dict]) -> Dict:
        """Получение худшей позиции по P&L"""
        if not positions:
            return {}
        
        worst = min(positions, key=lambda x: x["pnl"])
        return {
            "ticker": worst["ticker"],
            "pnl": worst["pnl"], 
            "pnl_percent": worst["pnl_percent"]
        }