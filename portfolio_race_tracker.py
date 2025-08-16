#!/usr/bin/env python3
"""
Скрипт для отслеживания гонки между портфелями
Ежедневный мониторинг роста 4 портфелей vs индекс MOEX
"""

import json
import logging
import csv
import os
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter
import seaborn as sns

from tinkoff.invest import Client, RequestError
from tinkoff.invest.schemas import MoneyValue, Quotation

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка графиков
plt.style.use('seaborn-v0_8')
sns.set_palette("husl")


def quotation_to_decimal(quotation: Quotation) -> Decimal:
    """Конвертация Quotation в Decimal для точных вычислений"""
    return Decimal(str(quotation.units)) + Decimal(str(quotation.nano)) / Decimal("1000000000")


def money_value_to_decimal(money: MoneyValue) -> Decimal:
    """Конвертация MoneyValue в Decimal"""
    return Decimal(str(money.units)) + Decimal(str(money.nano)) / Decimal("1000000000")


def get_moex_index_price(client: Client) -> float:
    """Получение текущего значения индекса MOEX"""
    try:
        # FIGI для индекса MOEX
        moex_figi = "BBG004730ZJ9"
        response = client.market_data.get_last_prices(figi=[moex_figi])
        
        if response.last_prices:
            return float(quotation_to_decimal(response.last_prices[0].price))
        else:
            logger.warning("Не удалось получить цену индекса MOEX")
            return None
    except RequestError as e:
        logger.error(f"Ошибка получения индекса MOEX: {e}")
        return None


def get_portfolio_value(client: Client, account_id: str) -> Dict:
    """Получение общей стоимости портфеля"""
    try:
        portfolio_response = client.operations.get_portfolio(account_id=account_id)
        positions = portfolio_response.positions
        
        # Получение курсов валют
        currency_rates = {"RUB": Decimal("1")}
        try:
            usd_response = client.market_data.get_last_prices(figi=["BBG0013HGFT4"])
            if usd_response.last_prices:
                currency_rates["USD"] = quotation_to_decimal(usd_response.last_prices[0].price)
            
            eur_response = client.market_data.get_last_prices(figi=["BBG0013HJJ31"])
            if eur_response.last_prices:
                currency_rates["EUR"] = quotation_to_decimal(eur_response.last_prices[0].price)
        except RequestError:
            pass
        
        # Получение цен для всех инструментов
        figis_for_prices = []
        instruments_info = {}
        
        for position in positions:
            if position.instrument_type in ["share", "bond", "etf"]:
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
                        'currency': instrument_response.instrument.currency
                    }
                except RequestError:
                    instruments_info[figi] = {'currency': 'RUB'}
        
        # Получение текущих цен
        current_prices = {}
        if figis_for_prices:
            try:
                prices_response = client.market_data.get_last_prices(figi=figis_for_prices)
                for price in prices_response.last_prices:
                    current_prices[price.figi] = quotation_to_decimal(price.price)
            except RequestError:
                pass
        
        # Расчет общей стоимости
        total_value_rub = Decimal("0")
        cash_balances = {}
        positions_count = 0
        
        for position in positions:
            figi = position.figi
            instrument_type = position.instrument_type
            quantity = quotation_to_decimal(position.quantity)
            
            if instrument_type == "currency":
                if figi == "RUB000UTSTOM":
                    cash_balances["RUB"] = quantity
                elif figi == "USD000UTSTOM":
                    cash_balances["USD"] = quantity
                elif figi == "EUR000UTSTOM":
                    cash_balances["EUR"] = quantity
                continue
            
            if quantity <= 0:
                continue
                
            if instrument_type in ["share", "bond", "etf"]:
                positions_count += 1
                current_price = current_prices.get(figi, Decimal("0"))
                currency = instruments_info.get(figi, {}).get('currency', 'RUB')
                
                # Конвертация в рубли
                rate = currency_rates.get(currency, Decimal("1"))
                current_price_rub = current_price * rate if currency != "RUB" else current_price
                
                total_value_rub += current_price_rub * quantity
        
        # Добавляем наличные в рублях
        total_cash_rub = Decimal("0")
        for curr, amount in cash_balances.items():
            rate = currency_rates.get(curr, Decimal("1"))
            total_cash_rub += amount * rate
        
        total_equity = total_value_rub + total_cash_rub
        
        return {
            "total_equity": float(total_equity),
            "positions_value": float(total_value_rub),
            "cash_balance": float(total_cash_rub),
            "positions_count": positions_count
        }
        
    except Exception as e:
        logger.error(f"Ошибка получения портфеля {account_id}: {e}")
        return None


def load_historical_data(filename: str = "portfolio_race_history.csv") -> List[Dict]:
    """Загрузка исторических данных"""
    if not os.path.exists(filename):
        return []
    
    data = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Конвертируем строковые значения обратно в числа
                for key in row:
                    if key != 'date' and key != 'portfolio_names':
                        try:
                            row[key] = float(row[key]) if row[key] else None
                        except (ValueError, TypeError):
                            row[key] = None
                data.append(row)
    except Exception as e:
        logger.error(f"Ошибка загрузки исторических данных: {e}")
        return []
    
    return data


def save_daily_data(data: Dict, filename: str = "portfolio_race_history.csv"):
    """Сохранение данных за день"""
    file_exists = os.path.exists(filename)
    
    try:
        with open(filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=data.keys())
            
            if not file_exists:
                writer.writeheader()
            
            writer.writerow(data)
        
        logger.info(f"Данные сохранены в {filename}")
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")


def create_performance_chart(historical_data: List[Dict], portfolio_names: List[str]):
    """Создание графика производительности портфелей"""
    if len(historical_data) < 2:
        print("Недостаточно данных для построения графика (нужно минимум 2 дня)")
        return
    
    # Подготовка данных
    dates = [datetime.strptime(row['date'], '%Y-%m-%d').date() for row in historical_data]
    
    # Базовые значения (первый день)
    base_data = historical_data[0]
    base_portfolios = [float(base_data[f'portfolio_{i+1}_value']) for i in range(4)]
    base_moex = float(base_data['moex_index']) if base_data.get('moex_index') else None
    
    # Расчет процентных изменений
    portfolio_changes = [[] for _ in range(4)]
    moex_changes = []
    
    for row in historical_data:
        # Портфели
        for i in range(4):
            current_value = float(row[f'portfolio_{i+1}_value'])
            change_percent = ((current_value - base_portfolios[i]) / base_portfolios[i]) * 100
            portfolio_changes[i].append(change_percent)
        
        # MOEX
        if row.get('moex_index') and base_moex:
            current_moex = float(row['moex_index'])
            moex_change = ((current_moex - base_moex) / base_moex) * 100
            moex_changes.append(moex_change)
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
    chart_filename = f"portfolio_race_chart_{datetime.now().strftime('%Y%m%d')}.png"
    plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
    plt.show()
    
    print(f"📈 График сохранен: {chart_filename}")


def generate_race_report(historical_data: List[Dict], portfolio_names: List[str]) -> str:
    """Генерация отчета о гонке портфелей"""
    if not historical_data:
        return "Нет данных для отчета"
    
    latest_data = historical_data[-1]
    base_data = historical_data[0]
    
    report = []
    report.append("=" * 80)
    report.append("                    ОТЧЕТ О ГОНКЕ ПОРТФЕЛЕЙ")
    report.append("=" * 80)
    
    report.append(f"\nПериод отслеживания: {base_data['date']} — {latest_data['date']}")
    report.append(f"Дней в гонке: {len(historical_data)}")
    
    # Таблица текущих результатов
    report.append("\n" + "-" * 80)
    report.append("                     ТЕКУЩИЕ РЕЗУЛЬТАТЫ")
    report.append("-" * 80)
    
    header = f"{'Портфель':<20} {'Стоимость':<15} {'Изменение':<12} {'Позиция':<8}"
    report.append(header)
    report.append("-" * 80)
    
    # Расчет изменений и рейтинга
    portfolio_performance = []
    for i in range(4):
        portfolio_name = portfolio_names[i] if i < len(portfolio_names) else f"Портфель {i+1}"
        base_value = float(base_data[f'portfolio_{i+1}_value'])
        current_value = float(latest_data[f'portfolio_{i+1}_value'])
        change_percent = ((current_value - base_value) / base_value) * 100
        
        portfolio_performance.append({
            'name': portfolio_name,
            'current_value': current_value,
            'change_percent': change_percent,
            'index': i
        })
    
    # Сортировка по производительности
    portfolio_performance.sort(key=lambda x: x['change_percent'], reverse=True)
    
    # Вывод результатов
    for rank, portfolio in enumerate(portfolio_performance, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🔹"
        
        line = f"{medal} {portfolio['name']:<17} {portfolio['current_value']:>12,.0f} ₽ {portfolio['change_percent']:>+8.2f}% #{rank}"
        report.append(line)
    
    # MOEX для сравнения
    if latest_data.get('moex_index') and base_data.get('moex_index'):
        base_moex = float(base_data['moex_index'])
        current_moex = float(latest_data['moex_index'])
        moex_change = ((current_moex - base_moex) / base_moex) * 100
        
        report.append("-" * 80)
        report.append(f"📊 Индекс MOEX:        {current_moex:>12.2f}    {moex_change:>+8.2f}%")
    
    # Статистика
    report.append("\n" + "-" * 80)
    report.append("                         СТАТИСТИКА")
    report.append("-" * 80)
    
    changes = [p['change_percent'] for p in portfolio_performance]
    
    report.append(f"Лучший результат:    {max(changes):+.2f}% ({portfolio_performance[0]['name']})")
    report.append(f"Худший результат:    {min(changes):+.2f}% ({portfolio_performance[-1]['name']})")
    report.append(f"Разброс:             {max(changes) - min(changes):.2f} п.п.")
    report.append(f"Средний результат:   {sum(changes) / len(changes):+.2f}%")
    
    # Динамика последних дней
    if len(historical_data) >= 2:
        prev_data = historical_data[-2]
        report.append(f"\n📈 Изменения за последний день:")
        
        for i, portfolio in enumerate(portfolio_performance):
            idx = portfolio['index']
            prev_value = float(prev_data[f'portfolio_{idx+1}_value'])
            current_value = portfolio['current_value']
            daily_change = ((current_value - prev_value) / prev_value) * 100
            
            report.append(f"  {portfolio['name']}: {daily_change:+.2f}%")
    
    report.append("\n" + "=" * 80)
    report.append(f"Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    report.append("=" * 80)
    
    return "\n".join(report)


def main():
    """Основная функция"""
    print("🏁 Трекер гонки портфелей")
    print("=" * 50)
    
    # Ввод токена
    token = input("Введите токен доступа к портфелям: ").strip()
    if not token:
        print("❌ Ошибка: токен не может быть пустым")
        return
    
    try:
        with Client(token) as client:
            # Получение списка счетов
            print("🔍 Получение списка портфелей...")
            accounts_response = client.users.get_accounts()
            accounts = accounts_response.accounts
            
            if len(accounts) < 4:
                print(f"❌ Найдено только {len(accounts)} счетов, нужно минимум 4")
                return
            
            # Отображение доступных счетов
            print(f"\n📋 Найдено {len(accounts)} портфелей:")
            for i, account in enumerate(accounts):
                print(f"  {i+1}. {account.name} (ID: {account.id})")
            
            # Выбор 4 портфелей для гонки
            selected_accounts = []
            portfolio_names = []
            
            for i in range(4):
                while True:
                    try:
                        choice = input(f"\nВыберите портфель #{i+1} (номер 1-{len(accounts)}): ")
                        idx = int(choice) - 1
                        
                        if 0 <= idx < len(accounts) and accounts[idx] not in selected_accounts:
                            selected_accounts.append(accounts[idx])
                            
                            # Запрос названия для гонки
                            custom_name = input(f"Название для гонки (или Enter для '{accounts[idx].name}'): ").strip()
                            portfolio_names.append(custom_name if custom_name else accounts[idx].name)
                            
                            print(f"✅ Добавлен: {portfolio_names[-1]}")
                            break
                        else:
                            print("❌ Неверный номер или портфель уже выбран")
                    except ValueError:
                        print("❌ Введите корректный номер")
            
            # Получение данных портфелей
            print(f"\n📊 Получение данных портфелей...")
            today = date.today().strftime('%Y-%m-%d')
            daily_data = {"date": today}
            
            # Данные по портфелям
            for i, account in enumerate(selected_accounts):
                print(f"  Загрузка {portfolio_names[i]}...")
                portfolio_data = get_portfolio_value(client, account.id)
                
                if portfolio_data:
                    daily_data[f'portfolio_{i+1}_value'] = portfolio_data['total_equity']
                    daily_data[f'portfolio_{i+1}_positions'] = portfolio_data['positions_count']
                else:
                    print(f"❌ Ошибка получения данных для {portfolio_names[i]}")
                    return
            
            # Данные по MOEX
            print("  Загрузка индекса MOEX...")
            moex_price = get_moex_index_price(client)
            if moex_price:
                daily_data['moex_index'] = moex_price
            
            # Сохранение имен портфелей
            daily_data['portfolio_names'] = '|'.join(portfolio_names)
            
            # Сохранение данных
            save_daily_data(daily_data)
            
            # Загрузка исторических данных
            historical_data = load_historical_data()
            
            # Генерация отчета
            report = generate_race_report(historical_data, portfolio_names)
            
            # Сохранение текстового отчета
            report_filename = f"portfolio_race_report_{datetime.now().strftime('%Y%m%d')}.txt"
            with open(report_filename, 'w', encoding='utf-8') as f:
                f.write(report)
            
            # Вывод отчета
            print("\n" + report)
            
            # Создание графика (если есть данные для сравнения)
            if len(historical_data) >= 2:
                print("\n📈 Создание графика производительности...")
                create_performance_chart(historical_data, portfolio_names)
            else:
                print("\n📊 График будет доступен со второго дня запуска")
            
            print(f"\n✅ Готово!")
            print(f"📄 Отчет сохранен: {report_filename}")
            print(f"📈 Данные обновлены в: portfolio_race_history.csv")
            print(f"\n🏁 Запускайте этот скрипт ежедневно для отслеживания гонки!")
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()