"""Отслеживание гонки портфелей"""
import csv
import os
import logging
from datetime import date, datetime
from typing import Dict, List
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import seaborn as sns
from .tinkoff_client import TinkoffClient

logger = logging.getLogger(__name__)

# Настройка графиков
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

class RaceTracker:
    def __init__(self, tinkoff_client: TinkoffClient, data_dir: str = "./data"):
        self.client = tinkoff_client
        self.data_dir = data_dir
        self.history_file = os.path.join(data_dir, "portfolio_race_history.csv")
        os.makedirs(data_dir, exist_ok=True)
    
    def update_daily_data(self, portfolio_accounts: Dict[str, str]) -> None:
        """Обновление ежедневных данных"""
        try:
            today = date.today().strftime('%Y-%m-%d')
            daily_data = {"date": today}
            
            # Получение данных портфелей
            portfolio_names = []
            for i, (name, account_id) in enumerate(portfolio_accounts.items(), 1):
                logger.info(f"Загрузка данных для {name}...")
                portfolio_value = self.client.get_portfolio_value(account_id)
                
                if portfolio_value:
                    daily_data[f'portfolio_{i}_value'] = portfolio_value['total_equity']
                    daily_data[f'portfolio_{i}_positions'] = portfolio_value['positions_count']
                    portfolio_names.append(name)
                else:
                    logger.error(f"Не удалось получить данные для {name}")
                    return
            
            # Получение данных MOEX
            logger.info("Загрузка индекса MOEX...")
            moex_price = self.client.get_moex_index_price()
            if moex_price:
                daily_data['moex_index'] = moex_price
            
            # Сохранение имен портфелей
            daily_data['portfolio_names'] = '|'.join(portfolio_names)
            
            # Сохранение данных
            self._save_daily_data(daily_data)
            
        except Exception as e:
            logger.error(f"Ошибка обновления данных гонки: {e}")
            raise
    
    def generate_race_report(self) -> Dict:
        """Генерация отчета о гонке"""
        try:
            historical_data = self.load_historical_data()
            
            if not historical_data:
                return {"error": "Нет данных для отчета"}
            
            latest_data = historical_data[-1]
            base_data = historical_data[0]
            
            # Получение имен портфелей
            portfolio_names = latest_data.get('portfolio_names', '').split('|')
            if len(portfolio_names) < 4:
                portfolio_names = [f"Портфель {i+1}" for i in range(4)]
            
            # Расчет производительности
            portfolio_performance = []
            for i in range(4):
                name = portfolio_names[i] if i < len(portfolio_names) else f"Портфель {i+1}"
                
                try:
                    base_value = float(base_data[f'portfolio_{i+1}_value'])
                    current_value = float(latest_data[f'portfolio_{i+1}_value'])
                    change_percent = ((current_value - base_value) / base_value) * 100
                    
                    portfolio_performance.append({
                        'name': name,
                        'current_value': current_value,
                        'change_percent': change_percent,
                        'index': i
                    })
                except (KeyError, ValueError, ZeroDivisionError):
                    continue
            
            # Сортировка по производительности
            portfolio_performance.sort(key=lambda x: x['change_percent'], reverse=True)
            
            # MOEX для сравнения
            moex_change = None
            if latest_data.get('moex_index') and base_data.get('moex_index'):
                try:
                    base_moex = float(base_data['moex_index'])
                    current_moex = float(latest_data['moex_index'])
                    moex_change = ((current_moex - base_moex) / base_moex) * 100
                except (ValueError, ZeroDivisionError):
                    pass
            
            # Изменения за последний день
            daily_changes = []
            if len(historical_data) >= 2:
                prev_data = historical_data[-2]
                for portfolio in portfolio_performance:
                    try:
                        idx = portfolio['index']
                        prev_value = float(prev_data[f'portfolio_{idx+1}_value'])
                        current_value = portfolio['current_value']
                        daily_change = ((current_value - prev_value) / prev_value) * 100
                        daily_changes.append({
                            'name': portfolio['name'],
                            'change_percent': daily_change
                        })
                    except (KeyError, ValueError, ZeroDivisionError):
                        daily_changes.append({
                            'name': portfolio['name'],
                            'change_percent': 0
                        })
            
            return {
                "period": {
                    "start_date": base_data['date'],
                    "end_date": latest_data['date'],
                    "days": len(historical_data)
                },
                "portfolio_performance": portfolio_performance,
                "moex_change": moex_change,
                "daily_changes": daily_changes,
                "portfolio_names": portfolio_names
            }
            
        except Exception as e:
            logger.error(f"Ошибка генерации отчета гонки: {e}")
            return {"error": str(e)}
    
    def create_performance_chart(self) -> str:
        """Создание графика производительности, возвращает путь к PNG"""
        try:
            historical_data = self.load_historical_data()
            
            if len(historical_data) < 2:
                logger.warning("Недостаточно данных для построения графика")
                return None
            
            # Получение имен портфелей
            latest_data = historical_data[-1]
            portfolio_names = latest_data.get('portfolio_names', '').split('|')
            if len(portfolio_names) < 4:
                portfolio_names = [f"Портфель {i+1}" for i in range(4)]
            
            # Подготовка данных
            dates = [datetime.strptime(row['date'], '%Y-%m-%d').date() for row in historical_data]
            
            # Базовые значения (первый день)
            base_data = historical_data[0]
            base_portfolios = []
            for i in range(4):
                try:
                    base_portfolios.append(float(base_data[f'portfolio_{i+1}_value']))
                except (KeyError, ValueError):
                    base_portfolios.append(1.0)  # Fallback
            
            base_moex = None
            try:
                if base_data.get('moex_index'):
                    base_moex = float(base_data['moex_index'])
            except (ValueError, TypeError):
                pass
            
            # Расчет процентных изменений
            portfolio_changes = [[] for _ in range(4)]
            moex_changes = []
            
            for row in historical_data:
                # Портфели
                for i in range(4):
                    try:
                        current_value = float(row[f'portfolio_{i+1}_value'])
                        change_percent = ((current_value - base_portfolios[i]) / base_portfolios[i]) * 100
                        portfolio_changes[i].append(change_percent)
                    except (KeyError, ValueError, ZeroDivisionError):
                        portfolio_changes[i].append(0)
                
                # MOEX
                if row.get('moex_index') and base_moex:
                    try:
                        current_moex = float(row['moex_index'])
                        moex_change = ((current_moex - base_moex) / base_moex) * 100
                        moex_changes.append(moex_change)
                    except (ValueError, ZeroDivisionError):
                        moex_changes.append(None)
                else:
                    moex_changes.append(None)
            
            # Создание графика
            plt.figure(figsize=(14, 8))
            
            # Цвета для портфелей
            colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']
            
            # График портфелей
            for i in range(4):
                portfolio_name = portfolio_names[i] if i < len(portfolio_names) else f"Портфель {i+1}"
                plt.plot(dates, portfolio_changes[i], 
                        label=portfolio_name, 
                        linewidth=2.5, 
                        color=colors[i],
                        marker='o', 
                        markersize=4)
            
            # График MOEX
            if any(x is not None for x in moex_changes):
                plt.plot(dates, moex_changes, 
                        label='Индекс MOEX', 
                        linewidth=2, 
                        color='#F39C12',
                        linestyle='--',
                        alpha=0.8)
            
            # Горизонтальная линия на 0%
            plt.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
            
            # Настройка осей
            plt.title('Гонка портфелей: Изменения относительно стартового дня', 
                      fontsize=16, fontweight='bold', pad=20)
            plt.xlabel('Дата', fontsize=12)
            plt.ylabel('Изменение (%)', fontsize=12)
            
            # Форматирование оси Y (проценты)
            def percent_formatter(x, pos):
                return f'{x:+.1f}%'
            
            plt.gca().yaxis.set_major_formatter(FuncFormatter(percent_formatter))
            
            # Форматирование оси X (даты)
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
            plt.xticks(rotation=45)
            
            # Легенда
            plt.legend(loc='upper left', frameon=True, fancybox=True, shadow=True)
            
            # Сетка
            plt.grid(True, alpha=0.3)
            
            # Плотная компоновка
            plt.tight_layout()
            
            # Сохранение
            charts_dir = os.path.join(self.data_dir, "charts")
            os.makedirs(charts_dir, exist_ok=True)
            chart_filename = os.path.join(charts_dir, f"portfolio_race_chart_{datetime.now().strftime('%Y%m%d')}.png")
            plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
            plt.close()  # Закрываем фигуру для освобождения памяти
            
            logger.info(f"График сохранен: {chart_filename}")
            return chart_filename
            
        except Exception as e:
            logger.error(f"Ошибка создания графика: {e}")
            return None
    
    def load_historical_data(self) -> List[Dict]:
        """Загрузка исторических данных"""
        if not os.path.exists(self.history_file):
            return []
        
        data = []
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Конвертируем строковые значения обратно в числа
                    for key in row:
                        if key not in ['date', 'portfolio_names']:
                            try:
                                row[key] = float(row[key]) if row[key] else None
                            except (ValueError, TypeError):
                                row[key] = None
                    data.append(row)
        except Exception as e:
            logger.error(f"Ошибка загрузки исторических данных: {e}")
            return []
        
        return data
    
    def _save_daily_data(self, data: Dict) -> None:
        """Сохранение данных за день"""
        file_exists = os.path.exists(self.history_file)
        
        try:
            with open(self.history_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=data.keys())
                
                if not file_exists:
                    writer.writeheader()
                
                writer.writerow(data)
            
            logger.info(f"Данные сохранены в {self.history_file}")
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {e}")
            raise