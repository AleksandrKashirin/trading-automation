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
    
    def calculate_total_pnl_from_inception(self, account_id: str) -> float:
        """Расчет общей прибыли с момента открытия счета"""
        try:
            with Client(self.client.token) as client:
                # Получаем операции за последний год (максимальный период)
                end_date = datetime.now()
                start_date = end_date - timedelta(days=365)
                
                operations_response = client.operations.get_operations(
                    account_id=account_id,
                    from_=start_date,
                    to=end_date,
                    state=OperationState.OPERATION_STATE_EXECUTED
                )
                
                total_invested = Decimal("0")
                total_dividends = Decimal("0")
                
                # Анализируем операции
                for operation in operations_response.operations:
                    if operation.operation_type in [
                        OperationType.OPERATION_TYPE_BUY,
                        OperationType.OPERATION_TYPE_SELL
                    ]:
                        # Покупки и продажи
                        payment = self.client.money_value_to_decimal(operation.payment)
                        if operation.operation_type == OperationType.OPERATION_TYPE_BUY:
                            total_invested += abs(payment)  # Покупки уменьшают баланс
                        else:  # SELL
                            total_invested -= abs(payment)  # Продажи увеличивают баланс
                    
                    elif operation.operation_type in [
                        OperationType.OPERATION_TYPE_DIVIDEND,
                        OperationType.OPERATION_TYPE_COUPON
                    ]:
                        # Дивиденды и купоны
                        payment = self.client.money_value_to_decimal(operation.payment)
                        total_dividends += payment
                
                # Получаем текущую стоимость портфеля
                portfolio_data = self.client.get_portfolio_data(account_id)
                current_equity = Decimal(str(portfolio_data["summary"]["total_equity"]))
                
                # Общая прибыль = текущая стоимость + дивиденды - вложения
                total_pnl = current_equity + total_dividends - total_invested
                
                return float(total_pnl)
                
        except Exception as e:
            logger.warning(f"Не удалось рассчитать P&L с открытия для {account_id}: {e}")
            # Fallback к текущему P&L из позиций
            try:
                portfolio_data = self.client.get_portfolio_data(account_id)
                return portfolio_data["summary"]["total_pnl"]
            except:
                return 0.0
    
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