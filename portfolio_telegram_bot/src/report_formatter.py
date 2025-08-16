"""Форматирование отчетов для Telegram"""
from typing import Dict, List
from datetime import datetime

class ReportFormatter:
    @staticmethod
    def format_portfolio_report(data: Dict) -> str:
        """Форматирование отчета по портфелю для Telegram"""
        try:
            summary = data.get("summary", {})
            positions = data.get("positions", [])
            analysis = data.get("analysis", {})
            account_name = data.get("account_name", "Портфель")
            
            # Основная информация
            total_equity = summary.get("total_equity", 0)
            total_pnl = summary.get("total_pnl", 0)
            cash_balance = summary.get("cash_balance_rub", 0)
            positions_count = summary.get("positions_count", 0)
            
            # P&L с открытия счета
            total_pnl_inception = analysis.get("total_pnl_from_inception", total_pnl)
            
            # Расчет процента доходности
            invested_amount = total_equity - total_pnl if total_equity > total_pnl else total_equity
            pnl_percent = (total_pnl / invested_amount * 100) if invested_amount > 0 else 0
            pnl_inception_percent = (total_pnl_inception / invested_amount * 100) if invested_amount > 0 else 0
            
            report = []
            report.append(f"🤖 *{account_name.upper()}*")
            report.append(f"📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}")
            report.append("")
            
            # Общий капитал и прибыль
            report.append(f"💰 *ОБЩИЙ КАПИТАЛ:* {total_equity:,.0f} ₽")
            if total_pnl_inception != total_pnl:
                report.append(f"📈 *P&L С ОТКРЫТИЯ:* {total_pnl_inception:+,.0f} ₽ ({pnl_inception_percent:+.1f}%)")
            report.append(f"📊 *P&L ТЕКУЩИЙ:* {total_pnl:+,.0f} ₽ ({pnl_percent:+.1f}%)")
            report.append("")
            
            # Позиции
            if positions:
                report.append("*ПОЗИЦИИ:*")
                
                # Показываем только значимые позиции (топ-5 по стоимости)
                sorted_positions = sorted(positions, key=lambda x: abs(x.get("total_value", 0)), reverse=True)
                top_positions = sorted_positions[:5]
                
                for pos in top_positions:
                    ticker = pos.get("ticker", "UNKNOWN")
                    shares = pos.get("shares", 0)
                    pnl = pos.get("pnl", 0)
                    pnl_percent = pos.get("pnl_percent", 0)
                    
                    # Эмодзи в зависимости от P&L
                    emoji = "📈" if pnl > 0 else "📉" if pnl < 0 else "📊"
                    
                    report.append(f"{emoji} {ticker}: {shares:.0f} шт")
                    report.append(f"💸 {pnl:+.0f} ₽ ({pnl_percent:+.1f}%)")
                
                if len(positions) > 5:
                    report.append(f"... и еще {len(positions) - 5} позиций")
                
                report.append("")
            
            # Позиции близко к стоп-лоссу
            near_stop_loss = analysis.get("positions_near_stop_loss", [])
            if near_stop_loss:
                report.append("⚠️ *БЛИЗКО К СТОП-ЛОССУ:*")
                for pos in near_stop_loss[:3]:  # Показываем только 3 самые критичные
                    ticker = pos.get("ticker", "UNKNOWN")
                    distance = pos.get("distance_to_stop_loss_percent", 0)
                    report.append(f"🔴 {ticker}: {distance:.1f}% до стоп-лосса")
                report.append("")
            
            # Лучшая и худшая позиции
            best_pos = analysis.get("best_position", {})
            worst_pos = analysis.get("worst_position", {})
            
            if best_pos and worst_pos:
                report.append("*ЭКСТРЕМУМЫ:*")
                report.append(f"🏆 Лучшая: {best_pos.get('ticker', 'N/A')} ({best_pos.get('pnl', 0):+.0f} ₽)")
                report.append(f"💔 Худшая: {worst_pos.get('ticker', 'N/A')} ({worst_pos.get('pnl', 0):+.0f} ₽)")
                report.append("")
            
            # Свободные средства и итого
            report.append(f"💵 *СВОБОДНО:* {cash_balance:,.0f} ₽")
            report.append(f"🎯 *ВСЕГО ПОЗИЦИЙ:* {positions_count}")
            
            return "\n".join(report)
            
        except Exception as e:
            return f"❌ Ошибка форматирования отчета: {e}"
    
    @staticmethod
    def format_race_report(data: Dict) -> str:
        """Форматирование отчета о гонке для Telegram"""
        try:
            if "error" in data:
                return f"❌ {data['error']}"
            
            period = data.get("period", {})
            portfolio_performance = data.get("portfolio_performance", [])
            moex_change = data.get("moex_change")
            daily_changes = data.get("daily_changes", [])
            
            report = []
            report.append("🏁 *ГОНКА ПОРТФЕЛЕЙ*")
            
            # Период отслеживания
            if period:
                start_date = period.get("start_date", "")
                end_date = period.get("end_date", "")
                days = period.get("days", 0)
                
                # Форматируем даты
                try:
                    start_formatted = datetime.strptime(start_date, '%Y-%m-%d').strftime('%d.%m')
                    end_formatted = datetime.strptime(end_date, '%Y-%m-%d').strftime('%d.%m')
                    report.append(f"📅 День {days} ({start_formatted} — {end_formatted})")
                except:
                    report.append(f"📅 День {days}")
            
            report.append("")
            
            # Рейтинг портфелей
            if portfolio_performance:
                report.append("*РЕЙТИНГ:*")
                
                medals = ["🥇", "🥈", "🥉", "🔻"]
                
                for i, portfolio in enumerate(portfolio_performance):
                    name = portfolio.get("name", f"Портфель {i+1}")
                    change_percent = portfolio.get("change_percent", 0)
                    
                    # Ограничиваем длину названия
                    if len(name) > 15:
                        name = name[:12] + "..."
                    
                    medal = medals[i] if i < len(medals) else "🔹"
                    report.append(f"{medal} {name}: {change_percent:+.2f}%")
                
                report.append("")
            
            # Сравнение с MOEX
            if moex_change is not None:
                moex_emoji = "📈" if moex_change > 0 else "📉" if moex_change < 0 else "📊"
                report.append(f"{moex_emoji} MOEX: {moex_change:+.2f}%")
                report.append("")
            
            # Изменения за последний день
            if daily_changes:
                report.append("*ЗА ДЕНЬ:*")
                
                # Находим лучший и худший результат дня
                best_daily = max(daily_changes, key=lambda x: x.get("change_percent", 0))
                worst_daily = min(daily_changes, key=lambda x: x.get("change_percent", 0))
                
                best_name = best_daily.get("name", "N/A")
                best_change = best_daily.get("change_percent", 0)
                worst_name = worst_daily.get("name", "N/A") 
                worst_change = worst_daily.get("change_percent", 0)
                
                # Ограничиваем длину названий
                if len(best_name) > 15:
                    best_name = best_name[:12] + "..."
                if len(worst_name) > 15:
                    worst_name = worst_name[:12] + "..."
                
                report.append(f"📈 Лучший: {best_name} {best_change:+.2f}%")
                report.append(f"📉 Худший: {worst_name} {worst_change:+.2f}%")
            
            return "\n".join(report)
            
        except Exception as e:
            return f"❌ Ошибка форматирования отчета о гонке: {e}"
    
    @staticmethod
    def optimize_for_telegram(text: str) -> List[str]:
        """Разбивка длинного текста на части для Telegram"""
        max_length = 4096
        
        if len(text) <= max_length:
            return [text]
        
        parts = []
        current_part = ""
        
        # Разбиваем по строкам для сохранения форматирования
        lines = text.split('\n')
        
        for line in lines:
            # Если даже одна строка слишком длинная
            if len(line) > max_length:
                # Сохраняем текущую часть если есть
                if current_part:
                    parts.append(current_part.strip())
                    current_part = ""
                
                # Разбиваем длинную строку по предложениям
                sentences = line.split('. ')
                temp_line = ""
                
                for sentence in sentences:
                    test_line = temp_line + sentence + ". " if temp_line else sentence + ". "
                    
                    if len(test_line) > max_length:
                        if temp_line:
                            parts.append(temp_line.strip())
                        temp_line = sentence + ". "
                    else:
                        temp_line = test_line
                
                if temp_line:
                    current_part = temp_line.strip()
                continue
            
            # Проверяем, поместится ли строка в текущую часть
            test_part = current_part + "\n" + line if current_part else line
            
            if len(test_part) <= max_length:
                current_part = test_part
            else:
                # Сохраняем текущую часть и начинаем новую
                if current_part:
                    parts.append(current_part.strip())
                current_part = line
        
        # Добавляем последнюю часть
        if current_part:
            parts.append(current_part.strip())
        
        return parts if parts else [text]
    
    @staticmethod
    def format_error_report(error: str, context: str = "") -> str:
        """Форматирование отчета об ошибке"""
        report = []
        report.append("❌ *ОШИБКА СИСТЕМЫ*")
        report.append("")
        report.append(f"*Описание:* {error}")
        
        if context:
            report.append(f"*Контекст:* {context}")
        
        report.append("")
        report.append(f"*Время:* {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        
        return "\n".join(report)