#!/usr/bin/env python3
"""
Мониторинг Honda CB500F/CB500X на Facebook Marketplace
Отправляет уведомления в Telegram при изменениях
"""

import asyncio
import json
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict
import aiohttp

# Загружаем переменные окружения из .env файла для локального тестирования
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv не обязателен в продакшене
    pass

from fb_scraper import FacebookMarketplaceScraper
from telegram_notifier import TelegramNotifier
from data_storage import DataStorage

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class SearchRegion:
    """Регион поиска"""
    name: str
    market_id: str
    radius_miles: int = 150

@dataclass
class ListingChange:
    """Изменение в объявлении"""
    change_type: str  # 'new', 'removed', 'price_change'
    listing_id: str
    old_data: Optional[Dict] = None
    new_data: Optional[Dict] = None
    price_diff: Optional[float] = None

class CB500Monitor:
    """Главный класс мониторинга"""
    
    # Регионы поиска в радиусе 150-200 миль от Summit, NJ
    SEARCH_REGIONS = [
        SearchRegion("New York Metro", "103727996333163"),  # NYC area
        SearchRegion("North Jersey", "109824442381734"),     # North NJ
        SearchRegion("Central Jersey", "104052089631773"),   # Central NJ
        SearchRegion("Philadelphia", "112724858717904"),     # Philly area
        SearchRegion("South Jersey", "104095516327164"),     # South NJ
        SearchRegion("Pennsylvania", "110396605639860"),     # PA general
        SearchRegion("Maryland", "106441769381283"),         # MD general
        SearchRegion("Virginia", "113301148664532"),         # VA general
        SearchRegion("Connecticut", "109415472407501"),      # CT general
        SearchRegion("Delaware", "106015479455140"),         # DE general
    ]
    
    # Модели для поиска
    SEARCH_QUERIES = ["cb500f", "cb500x", "cb 500f", "cb 500x"]
    
    # Ценовые фильтры
    MIN_PRICE = 3500
    MAX_PRICE = 5800
    
    def __init__(self, data_dir: Path, cookies_path: Path):
        self.data_dir = data_dir
        self.cookies_path = cookies_path
        self.storage = DataStorage(data_dir)
        self.scraper = FacebookMarketplaceScraper(cookies_path)
        self.telegram = TelegramNotifier()
        self.verbose_logging = os.getenv('VERBOSE_LOGGING', 'false').lower() == 'true'
        self.days_since_listed = int(os.getenv('DAYS_SINCE_LISTED', '14'))
        
        # Обеспечиваем существование директории данных
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_price(self, text: str) -> Optional[float]:
        """Извлекает цену из текста"""
        if not text:
            return None
        
        # Ищем цену в формате $XXXX
        price_matches = re.findall(r'\$(\d{1,2}(?:,\d{3})*|\d{3,6})', text)
        
        if not price_matches:
            return None
        
        try:
            # Берем самое большое число (скорее всего цена)
            prices = [float(match.replace(',', '')) for match in price_matches]
            prices = [p for p in prices if self.MIN_PRICE <= p <= self.MAX_PRICE]
            return max(prices) if prices else None
        except ValueError:
            return None
    
    def is_relevant_listing(self, listing: Dict[str, Any]) -> bool:
        """Проверяет релевантность объявления"""
        text = ' '.join([
            listing.get('title', ''),
            listing.get('price_text', ''),
            listing.get('description', '')
        ]).lower()
        
        # Проверяем наличие CB500
        has_cb500 = any(query in text for query in ['cb500f', 'cb500x', 'cb 500f', 'cb 500x'])
        
        # Исключаем другие модели
        excludes = ['cb650', 'cb300', 'cb1000', 'cbr500', 'cbr600']
        has_exclude = any(exclude in text for exclude in excludes)
        
        # Проверяем цену
        price = self.extract_price(listing.get('price_text', '') + listing.get('title', ''))
        valid_price = price is not None and self.MIN_PRICE <= price <= self.MAX_PRICE
        
        return has_cb500 and not has_exclude and valid_price
    
    async def scrape_region(self, region: SearchRegion, query: str) -> List[Dict[str, Any]]:
        """Скрапит объявления в одном регионе"""
        url = f"https://www.facebook.com/marketplace/{region.market_id}/search"
        params = {
            "daysSinceListed": str(self.days_since_listed),  # Настраиваемый диапазон
            "query": query,
            "sortBy": "creation_time_descend",
            "exact": "false"
        }
        
        try:
            logger.info(f"Scraping {region.name} for '{query}'")
            listings = await self.scraper.scrape_search(url, params, verbose=self.verbose_logging)
            
            # Фильтруем релевантные объявления
            relevant = [listing for listing in listings if self.is_relevant_listing(listing)]
            
            if self.verbose_logging:
                logger.info(f"Found {len(listings)} total listings, {len(relevant)} relevant in {region.name}")
            else:
                logger.info(f"Found {len(relevant)} relevant listings in {region.name}")
            return relevant
            
        except Exception as e:
            logger.error(f"Error scraping {region.name}: {e}")
            await self.telegram.send_error(f"❌ Ошибка скрапинга {region.name}: {e}")
            return []
    
    async def scrape_all_regions(self) -> List[Dict[str, Any]]:
        """Скрапит все регионы и запросы"""
        all_listings = []
        seen_ids = set()
        region_stats = {}
        
        for region in self.SEARCH_REGIONS:
            region_count = 0
            for query in self.SEARCH_QUERIES:
                try:
                    listings = await self.scrape_region(region, query)
                    region_count += len(listings)
                    
                    # Избегаем дубликатов
                    for listing in listings:
                        listing_id = listing.get('listing_id')
                        if listing_id and listing_id not in seen_ids:
                            listing['search_region'] = region.name
                            listing['search_query'] = query
                            all_listings.append(listing)
                            seen_ids.add(listing_id)
                    
                    # Небольшая задержка между запросами
                    await asyncio.sleep(2)
                    
                except Exception as e:
                    logger.error(f"Error in region {region.name}, query '{query}': {e}")
                    continue
            
            region_stats[region.name] = region_count
            if region_count > 0:
                logger.info(f"Region {region.name}: {region_count} total listings found")
        
        # Логируем общую статистику
        logger.info(f"Total unique listings found: {len(all_listings)}")
        logger.info(f"Regional breakdown: {region_stats}")
        logger.info(f"Duplicates removed: {sum(region_stats.values()) - len(all_listings)}")
        
        return all_listings
    
    def detect_changes(self, old_listings: Dict[str, Dict], new_listings: List[Dict]) -> List[ListingChange]:
        """Детектит изменения между старыми и новыми объявлениями"""
        changes = []
        new_listings_dict = {listing['listing_id']: listing for listing in new_listings}
        
        # Новые объявления
        for listing_id, listing in new_listings_dict.items():
            if listing_id not in old_listings:
                changes.append(ListingChange(
                    change_type='new',
                    listing_id=listing_id,
                    new_data=listing
                ))
        
        # Удаленные объявления
        for listing_id, listing in old_listings.items():
            if listing_id not in new_listings_dict:
                changes.append(ListingChange(
                    change_type='removed',
                    listing_id=listing_id,
                    old_data=listing
                ))
        
        # Изменения цен
        for listing_id in set(old_listings.keys()) & set(new_listings_dict.keys()):
            old_listing = old_listings[listing_id]
            new_listing = new_listings_dict[listing_id]
            
            old_price = self.extract_price(old_listing.get('price_text', '') + old_listing.get('title', ''))
            new_price = self.extract_price(new_listing.get('price_text', '') + new_listing.get('title', ''))
            
            if old_price and new_price and abs(old_price - new_price) > 50:  # Изменение > $50
                changes.append(ListingChange(
                    change_type='price_change',
                    listing_id=listing_id,
                    old_data=old_listing,
                    new_data=new_listing,
                    price_diff=new_price - old_price
                ))
        
        return changes
    
    async def send_change_notifications(self, changes: List[ListingChange]):
        """Отправляет уведомления об изменениях"""
        if not changes:
            return
        
        # Создаем саммари всех изменений
        new_count = sum(1 for c in changes if c.change_type == 'new')
        removed_count = sum(1 for c in changes if c.change_type == 'removed')
        price_change_count = sum(1 for c in changes if c.change_type == 'price_change')
        
        # Отправляем одно сообщение с саммари
        await self.telegram.send_changes_summary(changes, new_count, removed_count, price_change_count)
        
        # Небольшая задержка
        await asyncio.sleep(1)
    
    async def send_no_changes_summary(self, listings: List[Dict[str, Any]]):
        """Отправляет детальную сводку когда нет изменений"""
        try:
            # Создаем детальную сводку как в view_database.py
            summary_text = self.create_detailed_summary(listings)
            
            # Отправляем сводку в Telegram
            await self.telegram.send_message(f"📊 Детальная сводка (изменений нет)\n\n{summary_text}")
            
        except Exception as e:
            logger.error(f"Error sending no changes summary: {e}")
    
    def create_detailed_summary(self, listings: List[Dict[str, Any]]) -> str:
        """Создает детальную сводку объявлений с правильным форматированием Telegram"""
        if not listings:
            return "📭 *Объявлений не найдено*"
        
        # Группировка по регионам
        regions = {}
        for listing in listings:
            region = listing.get('search_region', 'Unknown')
            if region not in regions:
                regions[region] = 0
            regions[region] += 1
        
        # Создаем текст сводки с Markdown форматированием
        summary = f"📊 *СВОДКА БАЗЫ ДАННЫХ CB500F*\n"
        summary += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        summary += f"🏍 *Всего объявлений:* `{len(listings)}`\n\n"
        
        if regions:
            summary += "📍 *По регионам:*\n"
            for region, count in sorted(regions.items()):
                summary += f"  • {region}: `{count}`\n"
            summary += "\n"
        
        summary += "📋 *ДЕТАЛЬНЫЙ СПИСОК ОБЪЯВЛЕНИЙ*\n\n"
        
        # Добавляем детали каждого объявления (с ограничением размера)
        for i, listing in enumerate(listings, 1):
            # Проверяем, не превысили ли лимит Telegram (4096 символов)
            if len(summary) > 3200:  # Оставляем больше запаса
                remaining = len(listings) - i + 1
                summary += f"... и еще *{remaining}* объявлений\n"
                summary += f"� _Полный список: kubectl exec ... -- python /app/view_database.py --detailed_"
                break
                
            summary += f"🏍 *{i}. "
            
            # Извлекаем правильный ID
            listing_id = listing.get('id') or listing.get('listing_id') or 'N/A'
            summary += f"ID:* `{listing_id}`\n"
            
            # Сокращаем длинные заголовки и улучшаем форматирование
            title = listing.get('title', 'N/A')
            if title and title != 'N/A':
                if len(title) > 60:
                    title = title[:57] + "..."
                # Попытка извлечь год и модель из заголовка
                year_match = re.search(r'(20\d{2})', title)
                model_match = re.search(r'(CB\s*500[FX]?)', title, re.IGNORECASE)
                
                if year_match and model_match:
                    summary += f"📅 *{year_match.group(1)} Honda {model_match.group(1).upper()}*\n"
                else:
                    summary += f"🏷 _{title}_\n"
            
            # Цена с лучшим форматированием
            price = listing.get('price_text', 'N/A')
            if price and price != 'N/A':
                # Попытка извлечь основную цену
                price_match = re.search(r'\$[\d,]+', price)
                if price_match:
                    summary += f"💰 *{price_match.group()}*\n"
                else:
                    summary += f"💰 {price}\n"
            
            # Локация
            location = listing.get('location', 'N/A')
            if location and location != 'N/A':
                summary += f"📍 {location}\n"
            
            # Регион поиска
            region = listing.get('search_region', 'N/A')
            if region and region != 'N/A':
                summary += f"🗺 _{region}_\n"
            
            # Время в человеческом формате
            scraped_at = listing.get('scraped_at')
            if scraped_at:
                try:
                    if isinstance(scraped_at, (int, float)):
                        # Unix timestamp
                        dt = datetime.fromtimestamp(scraped_at)
                    else:
                        # Строка даты
                        dt = datetime.fromisoformat(str(scraped_at).replace('Z', '+00:00'))
                    
                    formatted_time = dt.strftime('%d.%m.%Y %H:%M')
                    summary += f"⏰ {formatted_time}\n"
                except:
                    summary += f"⏰ _{scraped_at}_\n"
            
            # Рабочая ссылка
            url = listing.get('url')
            if url:
                # Убираем лишние параметры из URL для чистоты
                clean_url = url.split('?')[0]
                if '/marketplace/item/' in clean_url:
                    summary += f"🔗 [Открыть объявление]({clean_url})\n"
                else:
                    summary += f"🔗 {clean_url}\n"
            
            summary += "\n"
        
        return summary
    
    async def run_monitor_cycle(self):
        """Запускает один цикл мониторинга"""
        timestamp = datetime.now()
        logger.info(f"Starting monitor cycle at {timestamp}")
        
        try:
            # Загружаем текущее состояние
            old_listings = self.storage.load_current_state()
            
            # Скрапим новые данные
            new_listings = await self.scrape_all_regions()
            
            if not new_listings:
                logger.warning("No listings found - possible scraping issue")
                await self.telegram.send_error("⚠️ Не найдено объявлений - возможная проблема со скрапингом")
                return
            
            # Детектим изменения
            changes = self.detect_changes(old_listings, new_listings)
            
            # Сохраняем новое состояние
            self.storage.save_current_state(new_listings)
            self.storage.save_historical_data(new_listings, timestamp)
            
            # Отправляем уведомления
            if changes:
                logger.info(f"Found {len(changes)} changes")
                await self.send_change_notifications(changes)
            else:
                logger.info("No changes detected")
                # Отправляем детальную сводку когда нет изменений
                await self.send_no_changes_summary(new_listings)
            
            # Отправляем сводку (раз в день в 9 утра)
            if timestamp.hour == 9 and timestamp.minute < 5:
                await self.telegram.send_daily_summary(new_listings)
            
        except Exception as e:
            logger.error(f"Error in monitor cycle: {e}")
            await self.telegram.send_error(f"❌ Ошибка мониторинга: {e}")
            raise

async def main():
    """Главная функция"""
    # Конфигурация из переменных окружения
    data_dir = Path(os.getenv('DATA_DIR', '/app/data'))
    cookies_path = Path(os.getenv('COOKIES_PATH', '/app/data/cookies.json'))
    
    # Проверяем наличие необходимых файлов
    if not cookies_path.exists():
        logger.error(f"Cookies file not found: {cookies_path}")
        return
    
    # Создаем монитор
    monitor = CB500Monitor(data_dir, cookies_path)
    
    # Запускаем цикл мониторинга
    await monitor.run_monitor_cycle()

if __name__ == "__main__":
    asyncio.run(main())
