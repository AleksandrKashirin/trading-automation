#!/usr/bin/env python3
"""
Скрипт для получения состояния портфеля через API Тинькофф Инвестиций
Генерирует текстовый отчет вместо JSON
"""

import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from tinkoff.invest import Client, RequestError
from tinkoff.invest.schemas import MoneyValue, Quotation

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def quotation_to_decimal(quotation: Quotation) -> Decimal:
    """Конвертация Quotation в Decimal для точных вычислений"""
    return Decimal(str(quotation.units)) + Decimal(str(quotation.nano)) / Decimal(
        "1000000000"
    )


def money_value_to_decimal(money: MoneyValue) -> Decimal:
    """Конвертация MoneyValue в Decimal"""
    return Decimal(str(money.units)) + Decimal(str(money.nano)) / Decimal("1000000000")


def get_portfolio_data(
    token: str, account_id: Optional[str] = None, debug: bool = False
) -> Dict:
    """
    Получение данных портфеля с улучшенными расчетами

    Args:
        token: Токен доступа к API
        account_id: ID счета (если None, берется первый доступный)
        debug: Включить отладочную информацию

    Returns:
        Словарь с данными портфеля в формате JSON
    """

    with Client(token) as client:
        try:
            # Получение списка счетов
            accounts_response = client.users.get_accounts()
            accounts = accounts_response.accounts

            if not accounts:
                raise ValueError("Не найдено доступных счетов")

            # Выбор счета
            if account_id:
                selected_account = next(
                    (acc for acc in accounts if acc.id == account_id), None
                )
                if not selected_account:
                    raise ValueError(f"Счет с ID {account_id} не найден")
            else:
                selected_account = accounts[0]
                logger.info(
                    f"Используется счет: {selected_account.name} ({selected_account.id})"
                )

            account_id = selected_account.id

            # Получение портфеля
            portfolio_response = client.operations.get_portfolio(account_id=account_id)
            positions = portfolio_response.positions

            if debug:
                print(f"\n=== ОТЛАДКА: Найдено позиций: {len(positions)} ===")
                for pos in positions:
                    print(
                        f"Инструмент: {pos.instrument_type}, FIGI: {pos.figi}, Количество: {pos.quantity.units}"
                    )

            # Получение курсов валют
            currency_rates = {"RUB": Decimal("1")}
            try:
                # USD/RUB
                usd_response = client.market_data.get_last_prices(figi=["BBG0013HGFT4"])
                if usd_response.last_prices:
                    currency_rates["USD"] = quotation_to_decimal(
                        usd_response.last_prices[0].price
                    )

                # EUR/RUB
                eur_response = client.market_data.get_last_prices(figi=["BBG0013HJJ31"])
                if eur_response.last_prices:
                    currency_rates["EUR"] = quotation_to_decimal(
                        eur_response.last_prices[0].price
                    )

                if debug:
                    print(f"Курсы валют: {currency_rates}")
            except RequestError as e:
                logger.warning(f"Не удалось получить курсы валют: {e}")

            # Получение информации об инструментах
            instruments_info = {}
            figis_for_prices = []

            for position in positions:
                figi = position.figi
                instrument_type = position.instrument_type

                # Обрабатываем все типы инструментов
                if instrument_type in ["share", "bond", "etf"]:
                    figis_for_prices.append(figi)

                    try:
                        if instrument_type == "share":
                            instrument_response = client.instruments.share_by(
                                id_type=1, id=figi
                            )
                        elif instrument_type == "bond":
                            instrument_response = client.instruments.bond_by(
                                id_type=1, id=figi
                            )
                        elif instrument_type == "etf":
                            instrument_response = client.instruments.etf_by(
                                id_type=1, id=figi
                            )

                        instruments_info[figi] = {
                            "ticker": instrument_response.instrument.ticker,
                            "name": instrument_response.instrument.name,
                            "currency": instrument_response.instrument.currency,
                            "type": instrument_type,
                        }
                    except RequestError as e:
                        logger.warning(
                            f"Не удалось получить информацию об инструменте {figi}: {e}"
                        )
                        instruments_info[figi] = {
                            "ticker": f"UNKNOWN_{figi[:8]}",
                            "name": "Unknown instrument",
                            "currency": "RUB",
                            "type": instrument_type,
                        }

            # Получение текущих цен с разными методами
            current_prices = {}
            orderbook_prices = {}

            if figis_for_prices:
                try:
                    # Последние цены
                    prices_response = client.market_data.get_last_prices(
                        figi=figis_for_prices
                    )
                    for price in prices_response.last_prices:
                        current_prices[price.figi] = quotation_to_decimal(price.price)

                    # Стаканы (для более точных цен)
                    for figi in figis_for_prices[
                        :5
                    ]:  # Ограничиваем количество запросов
                        try:
                            orderbook_response = client.market_data.get_order_book(
                                figi=figi, depth=1
                            )
                            if orderbook_response.bids:
                                bid_price = quotation_to_decimal(
                                    orderbook_response.bids[0].price
                                )
                                orderbook_prices[figi] = bid_price
                        except:
                            pass

                except RequestError as e:
                    logger.warning(f"Не удалось получить текущие цены: {e}")

            # Получение стоп-заявок
            stop_orders = {}
            try:
                stop_orders_response = client.stop_orders.get_stop_orders(
                    account_id=account_id
                )
                for order in stop_orders_response.stop_orders:
                    if order.direction.name == "STOP_ORDER_DIRECTION_SELL":
                        stop_orders[order.figi] = quotation_to_decimal(order.stop_price)
            except RequestError as e:
                logger.warning(f"Не удалось получить стоп-заявки: {e}")

            # Формирование результата
            portfolio_data = {
                "date": datetime.now().isoformat(),
                "account_id": account_id,
                "account_name": selected_account.name,
                "currency_rates": {k: float(v) for k, v in currency_rates.items()},
                "positions": [],
                "summary": {},
                "debug_info": {} if debug else None,
            }

            total_value_rub = Decimal("0")
            total_pnl_rub = Decimal("0")
            cash_balances = {}

            # Обработка всех позиций
            for position in positions:
                figi = position.figi
                instrument_type = position.instrument_type
                quantity = quotation_to_decimal(position.quantity)

                if debug:
                    print(
                        f"\nОбработка позиции: {figi}, тип: {instrument_type}, количество: {quantity}"
                    )

                if instrument_type == "currency":
                    # Валютные позиции
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
                    instrument_info = instruments_info.get(figi, {})
                    ticker = instrument_info.get("ticker", "UNKNOWN")
                    currency = instrument_info.get("currency", "RUB")

                    # Средняя цена покупки
                    avg_price = money_value_to_decimal(position.average_position_price)

                    # Текущая цена (пробуем разные источники)
                    current_price = orderbook_prices.get(figi) or current_prices.get(
                        figi, Decimal("0")
                    )

                    # Конвертация в рубли
                    rate = currency_rates.get(currency, Decimal("1"))
                    avg_price_rub = avg_price * rate if currency != "RUB" else avg_price
                    current_price_rub = (
                        current_price * rate if currency != "RUB" else current_price
                    )

                    total_position_value = current_price_rub * quantity
                    position_pnl = total_position_value - (avg_price_rub * quantity)

                    total_value_rub += total_position_value
                    total_pnl_rub += position_pnl

                    stop_loss = stop_orders.get(figi)

                    position_data = {
                        "ticker": ticker,
                        "figi": figi,
                        "instrument_type": instrument_type,
                        "currency": currency,
                        "shares": float(quantity),
                        "cost_basis": float(avg_price),
                        "cost_basis_rub": float(avg_price_rub),
                        "stop_loss": float(stop_loss) if stop_loss else None,
                        "current_price": float(current_price),
                        "current_price_rub": float(current_price_rub),
                        "total_value": float(total_position_value),
                        "pnl": float(position_pnl)
                    }

                    if debug:
                        print(
                            f"  Тикер: {ticker}, Цена: {current_price} {currency}, P&L: {position_pnl:.2f} RUB"
                        )

                    portfolio_data["positions"].append(position_data)

            # Подсчет общего баланса наличных в рублях
            total_cash_rub = Decimal("0")
            for curr, amount in cash_balances.items():
                rate = currency_rates.get(curr, Decimal("1"))
                total_cash_rub += amount * rate

            total_equity = total_value_rub + total_cash_rub

            # Итоговая информация
            portfolio_data["summary"] = {
                "total_positions_value": float(total_value_rub),
                "total_pnl": float(total_pnl_rub),
                "cash_balance_rub": float(total_cash_rub),
                "cash_balances": {k: float(v) for k, v in cash_balances.items()},
                "total_equity": float(total_equity),
                "positions_count": len(portfolio_data["positions"]),
            }

            if debug:
                portfolio_data["debug_info"] = {
                    "raw_positions_count": len(positions),
                    "processed_positions": len(portfolio_data["positions"]),
                    "price_sources": {
                        "last_prices": len(current_prices),
                        "orderbook_prices": len(orderbook_prices),
                    },
                }

            return portfolio_data

        except RequestError as e:
            logger.error(f"Ошибка API: {e}")
            raise
        except Exception as e:
            logger.error(f"Неожиданная ошибка: {e}")
            raise


def generate_text_report(portfolio_data: Dict) -> str:
    """Генерация текстового отчета о портфеле"""
    
    summary = portfolio_data["summary"]
    positions = portfolio_data["positions"]
    
    report = []
    report.append("=" * 80)
    report.append("                         ОТЧЕТ О ПОРТФЕЛЕ")
    report.append("=" * 80)
    
    # Общая информация
    report.append(f"\nДата и время: {portfolio_data['date']}")
    report.append(f"Брокерский счет: {portfolio_data['account_name']} (ID: {portfolio_data['account_id']})")
    
    # Курсы валют
    if 'currency_rates' in portfolio_data:
        report.append(f"\nКурсы валют:")
        for curr, rate in portfolio_data['currency_rates'].items():
            if curr != 'RUB':
                report.append(f"  {curr}/RUB: {rate:.4f}")
    
    # Заголовок таблицы позиций
    report.append("\n" + "-" * 80)
    report.append("                            ПОЗИЦИИ")
    report.append("-" * 80)
    
    # Шапка таблицы
    header = f"{'Тикер':<8} {'Кол-во':<8} {'Ср.цена':<10} {'Тек.цена':<10} {'Стоп-лосс':<10} {'Стоимость':<12} {'P&L':<10} {'%':<8}"
    report.append(header)
    report.append("-" * 80)
    
    # Позиции
    total_invested = 0
    for pos in positions:
        ticker = pos['ticker']
        shares = pos['shares']
        cost_basis = pos['cost_basis_rub']
        current_price = pos['current_price_rub']
        stop_loss = pos.get('stop_loss')
        total_value = pos['total_value']
        pnl = pos['pnl']
        
        # Расчет процента изменения
        invested_amount = cost_basis * shares
        total_invested += invested_amount
        pnl_percent = (pnl / invested_amount * 100) if invested_amount > 0 else 0
        
        # Форматирование стоп-лосса
        stop_loss_str = f"{stop_loss:.2f}" if stop_loss else "—"
        
        line = f"{ticker:<8} {shares:<8.0f} {cost_basis:<10.2f} {current_price:<10.2f} {stop_loss_str:<10} {total_value:<12.2f} {pnl:<10.2f} {pnl_percent:<7.1f}%"
        report.append(line)
    
    # Итоговая секция
    report.append("-" * 80)
    report.append("                           ИТОГОВЫЕ ПОКАЗАТЕЛИ")
    report.append("-" * 80)
    
    cash_balance = summary['cash_balance_rub']
    total_positions_value = summary['total_positions_value']
    total_pnl = summary['total_pnl']
    total_equity = summary['total_equity']
    
    # Общий процент доходности
    total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0
    
    report.append(f"Количество позиций:          {summary['positions_count']}")
    report.append(f"Инвестированная сумма:       {total_invested:,.2f} ₽")
    report.append(f"Текущая стоимость позиций:   {total_positions_value:,.2f} ₽")
    report.append(f"Нереализованная прибыль/убыток: {total_pnl:,.2f} ₽ ({total_pnl_percent:+.2f}%)")
    report.append(f"Свободные средства:          {cash_balance:,.2f} ₽")
    report.append(f"Общий капитал:               {total_equity:,.2f} ₽")
    
    # Детализация по валютам
    cash_balances = summary.get('cash_balances', {})
    if len(cash_balances) > 1:
        report.append(f"\nДетализация наличных средств:")
        for currency, amount in cash_balances.items():
            report.append(f"  {currency}: {amount:,.2f}")
    
    # Анализ и рекомендации
    report.append("\n" + "-" * 80)
    report.append("                         АНАЛИЗ ПОРТФЕЛЯ")
    report.append("-" * 80)
    
    # Топ и худшие позиции
    if positions:
        # Сортировка по P&L
        sorted_by_pnl = sorted(positions, key=lambda x: x['pnl'], reverse=True)
        best_position = sorted_by_pnl[0]
        worst_position = sorted_by_pnl[-1]
        
        report.append(f"Лучшая позиция:     {best_position['ticker']} (+{best_position['pnl']:.2f} ₽)")
        report.append(f"Худшая позиция:     {worst_position['ticker']} ({worst_position['pnl']:+.2f} ₽)")
        
        # Позиции близко к стоп-лоссу
        near_stop_loss = []
        for pos in positions:
            if pos.get('stop_loss'):
                current = pos['current_price_rub']
                stop = pos['stop_loss']
                distance_percent = ((current - stop) / current * 100)
                if distance_percent < 5:  # Меньше 5% до стоп-лосса
                    near_stop_loss.append((pos['ticker'], distance_percent))
        
        if near_stop_loss:
            report.append(f"\nВнимание! Позиции близко к стоп-лоссу:")
            for ticker, distance in near_stop_loss:
                report.append(f"  {ticker}: {distance:.1f}% до стоп-лосса")
    
    report.append("\n" + "=" * 80)
    report.append(f"Отчет сгенерирован: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    report.append("=" * 80)
    
    return "\n".join(report)


def save_portfolio_report(portfolio_data: Dict, filename: str = "portfolio_report.txt"):
    """Сохранение текстового отчета о портфеле"""
    try:
        report_text = generate_text_report(portfolio_data)
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(report_text)
        
        logger.info(f"Текстовый отчет сохранен в файл: {filename}")
        return report_text
    except Exception as e:
        logger.error(f"Ошибка при сохранении отчета: {e}")
        raise


def save_portfolio_to_json(portfolio_data: Dict, filename: str = "portfolio.json"):
    """Сохранение данных портфеля в JSON файл (для отладки)"""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(portfolio_data, f, ensure_ascii=False, indent=2)
        logger.info(f"JSON данные сохранены в файл: {filename}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении JSON файла: {e}")
        raise


def main():
    """Основная функция"""
    # Ввод токена
    token = input("Введите ваш токен Тинькофф Инвестиций: ").strip()

    if not token:
        print("Ошибка: токен не может быть пустым")
        return

    # Режим отладки
    debug_mode = input("Включить режим отладки? (y/n): ").strip().lower() == "y"
    
    # Выбор формата отчета
    save_json = input("Сохранить также JSON файл для отладки? (y/n): ").strip().lower() == "y"

    try:
        # Получение данных портфеля
        print("Получение данных портфеля...")
        portfolio_data = get_portfolio_data(token, debug=debug_mode)

        # Сохранение текстового отчета
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_filename = f"portfolio_report_{timestamp}.txt"
        
        print("Генерация отчета...")
        report_text = save_portfolio_report(portfolio_data, report_filename)
        
        # Опционально сохраняем JSON для отладки
        if save_json:
            json_filename = f"portfolio_data_{timestamp}.json"
            save_portfolio_to_json(portfolio_data, json_filename)

        # Вывод отчета в консоль
        print("\n" + report_text)
        
        print(f"\n📄 Текстовый отчет сохранен: {report_filename}")
        if save_json:
            print(f"📊 JSON данные сохранены: {json_filename}")
        
        print(f"\n✅ Готово! Проверьте файл отчета для детального анализа.")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        if debug_mode:
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    main()