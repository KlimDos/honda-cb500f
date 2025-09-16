#!/usr/bin/env python3
"""
Telegram notifier для отправки уведомлений о Honda CB500F/CB500X
"""

import os
import re
import aiohttp
import asyncio
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class TelegramNotifier:
    """Класс для отправки уведомлений в Telegram"""
    
    def __init__(self):
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID', "242426387")
        
        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set")
        
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def _extract_price(self, text: str) -> Optional[float]:
        """Извлекает цену из текста"""
        if not text:
            return None
        
        price_matches = re.findall(r'\$(\d{1,2}(?:,\d{3})*|\d{3,6})', text)
        if not price_matches:
            return None
        
        try:
            prices = [float(match.replace(',', '')) for match in price_matches]
            prices = [p for p in prices if 3000 <= p <= 10000]  # Разумные цены для мотоциклов
            return max(prices) if prices else None
        except ValueError:
            return None
    
    def _extract_year(self, text: str) -> Optional[int]:
        """Извлекает год из текста"""
        if not text:
            return None
        
        years = re.findall(r'\b(20(?:1[3-9]|2[0-5]))\b', text)
        return int(years[0]) if years else None
    
    def _format_listing_info(self, listing: Dict[str, Any]) -> str:
        """Форматирует информацию об объявлении"""
        title = listing.get('title', 'N/A')
        price_text = listing.get('price_text', 'N/A')
        location = listing.get('location', 'N/A')
        listed_date = listing.get('listed_date', 'N/A')
        url = listing.get('url', 'N/A')
        
        # Извлекаем цену и год
        all_text = f"{title} {price_text}"
        price = self._extract_price(all_text)
        year = self._extract_year(all_text)
        
        # Определяем модель
        text_lower = all_text.lower()
        if 'cb500x' in text_lower or 'cb 500x' in text_lower:
            model = "CB500X"
        elif 'cb500f' in text_lower or 'cb 500f' in text_lower:
            model = "CB500F"
        else:
            model = "CB500F/X"
        
        # Форматируем
        info_lines = []
        
        if year and price:
            info_lines.append(f"🏍 {year} Honda {model} - ${price:,.0f}")
        elif price:
            info_lines.append(f"🏍 Honda {model} - ${price:,.0f}")
        else:
            info_lines.append(f"🏍 {title}")
            if price_text != title:
                info_lines.append(f"💰 {price_text}")
        
        info_lines.append(f"📍 {location}")
        
        if listed_date and listed_date != 'N/A':
            info_lines.append(f"📅 {listed_date}")
        
        # Краткое описание
        description = listing.get('description', '')
        if description and len(description) > 20:
            # Берем первые 100 символов
            short_desc = description[:100]
            if len(description) > 100:
                short_desc += "..."
            info_lines.append(f"📝 {short_desc}")
        
        return "\n".join(info_lines)
    
    async def _send_message(self, message: str, parse_mode: str = None):
        """Отправляет сообщение в Telegram"""
        url = f"{self.api_url}/sendMessage"
        
        data = {
            'chat_id': self.chat_id,
            'text': message,
            'disable_web_page_preview': False
        }
        
        # Добавляем parse_mode только если указан
        if parse_mode:
            data['parse_mode'] = parse_mode
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger.info("Message sent successfully")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"Failed to send message: {response.status} - {error_text}")
                        return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
    
    async def send_new_listing(self, listing: Dict[str, Any]):
        """Отправляет уведомление о новом объявлении"""
        info = self._format_listing_info(listing)
        url = listing.get('url', 'N/A')
        
        message = f"""🆕 Новое объявление

{info}

🔗 Смотреть: {url}"""
        
        return await self._send_message(message)
    
    async def send_removed_listing(self, listing: Dict[str, Any]):
        """Отправляет уведомление об удаленном объявлении"""
        info = self._format_listing_info(listing)
        
        message = f"""❌ Объявление больше не доступно

{info}

Возможно, продано или снято с продажи."""
        
        await self._send_message(message)
    
    async def send_changes_summary(self, changes: List, new_count: int, removed_count: int, price_change_count: int):
        """Отправляет сводку изменений одним сообщением"""
        summary_lines = [
            "📊 СВОДКА ИЗМЕНЕНИЙ",
            ""
        ]
        
        if new_count > 0:
            summary_lines.append(f"🆕 Новых объявлений: {new_count}")
            
            # Добавляем детали новых объявлений
            for change in changes:
                if change.change_type == 'new':
                    listing = change.new_data
                    info = self._format_listing_info(listing)
                    url = listing.get('url', '')
                    summary_lines.append(f"")
                    summary_lines.append(info)
                    summary_lines.append(f"🔗 {url}")
        
        if removed_count > 0:
            summary_lines.append(f"")
            summary_lines.append(f"❌ Удаленных объявлений: {removed_count}")
        
        if price_change_count > 0:
            summary_lines.append(f"")
            summary_lines.append(f"💰 Изменений цены: {price_change_count}")
            
            # Добавляем детали изменений цены
            for change in changes:
                if change.change_type == 'price_change':
                    old_price = self._extract_price(f"{change.old_data.get('title', '')} {change.old_data.get('price_text', '')}")
                    new_price = self._extract_price(f"{change.new_data.get('title', '')} {change.new_data.get('price_text', '')}")
                    
                    if old_price and new_price:
                        direction = "📈" if new_price > old_price else "📉"
                        summary_lines.append(f"{direction} ${old_price:,.0f} → ${new_price:,.0f}")
        
        message = "\n".join(summary_lines)
        await self._send_message(message)
    
    async def send_price_change(self, old_listing: Dict[str, Any], new_listing: Dict[str, Any], price_diff: float):
        """Отправляет уведомление об изменении цены"""
        info = self._format_listing_info(new_listing)
        url = new_listing.get('url', 'N/A')
        
        old_price = self._extract_price(f"{old_listing.get('title', '')} {old_listing.get('price_text', '')}")
        new_price = self._extract_price(f"{new_listing.get('title', '')} {new_listing.get('price_text', '')}")
        
        if old_price and new_price:
            if price_diff > 0:
                direction = "📈"
                change_text = f"Цена повышена на ${abs(price_diff):,.0f}"
            else:
                direction = "📉"
                change_text = f"Цена снижена на ${abs(price_diff):,.0f}"
            
            price_line = f"{direction} ${old_price:,.0f} → ${new_price:,.0f}"
        else:
            direction = "🔄"
            change_text = "Цена изменена"
            price_line = f"Старая: {old_listing.get('price_text', 'N/A')} → Новая: {new_listing.get('price_text', 'N/A')}"
        
        message = f"""{direction} Изменение цены

{info}

💰 {price_line}
📊 {change_text}

🔗 Смотреть: {url}"""
        
        await self._send_message(message)
    
    async def send_daily_summary(self, listings: List[Dict[str, Any]]):
        """Отправляет ежедневную сводку"""
        total_count = len(listings)
        
        # Подсчитываем по моделям
        cb500f_count = sum(1 for l in listings if 'cb500f' in f"{l.get('title', '')} {l.get('price_text', '')}".lower())
        cb500x_count = sum(1 for l in listings if 'cb500x' in f"{l.get('title', '')} {l.get('price_text', '')}".lower())
        
        # Ценовая статистика
        prices = []
        for listing in listings:
            price = self._extract_price(f"{listing.get('title', '')} {listing.get('price_text', '')}")
            if price:
                prices.append(price)
        
        price_stats = ""
        if prices:
            avg_price = sum(prices) / len(prices)
            min_price = min(prices)
            max_price = max(prices)
            price_stats = f"""
💰 Ценовая статистика:
   • Средняя: ${avg_price:,.0f}
   • Минимум: ${min_price:,.0f}
   • Максимум: ${max_price:,.0f}"""
        
        message = f"""📊 Ежедневная сводка

🏍 Всего объявлений: {total_count}
   • CB500F: {cb500f_count}
   • CB500X: {cb500x_count}
{price_stats}

🕘 Мониторинг работает каждый час"""
        
        await self._send_message(message)
    
    async def send_error(self, error_message: str):
        """Отправляет уведомление об ошибке"""
        message = f"""⚠️ Ошибка мониторинга

{error_message}

Время: {asyncio.get_event_loop().time()}"""
        
        await self._send_message(message)
