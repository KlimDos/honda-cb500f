#!/usr/bin/env python3
"""
Facebook Marketplace scraper для мониторинга
Базируется на существующем scraper из основного проекта
"""

import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
import re
from datetime import datetime, timedelta

from playwright.async_api import async_playwright, Page, BrowserContext

# Константы
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
)

ANCHOR_SELECTOR = "a[href*='/marketplace/item/']"
MIN_ID_LENGTH = 10

@dataclass
class Listing:
    """Объявление с Facebook Marketplace"""
    listing_id: str
    title: str
    price_text: str
    location: str
    url: str
    image: Optional[str]
    description: str
    listed_date: str
    listed_date_parsed: str
    scraped_at: float
    search_region: Optional[str] = None
    search_query: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

class FacebookMarketplaceScraper:
    """Скрапер Facebook Marketplace"""
    
    def __init__(self, cookies_path: Path):
        self.cookies_path = cookies_path
        self.cookies = self._load_cookies()
    
    def _load_cookies(self) -> List[Dict[str, Any]]:
        """Загружает cookies из файла"""
        try:
            with open(self.cookies_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if isinstance(data, list):
                cookies = []
                for c in data:
                    if 'name' in c and 'value' in c:
                        cookies.append({
                            'name': c['name'],
                            'value': c['value'],
                            'domain': c.get('domain', '.facebook.com'),
                            'path': c.get('path', '/'),
                        })
                return cookies
        except (json.JSONDecodeError, FileNotFoundError) as e:
            raise Exception(f"Error loading cookies: {e}")
        
        return []
    
    def _parse_relative_date(self, relative_str: str) -> str:
        """Парсит относительную дату"""
        if not relative_str:
            return ""
        
        try:
            relative_str = relative_str.lower().strip()
            now = datetime.now()
            
            match = re.search(r'(\d+)\s*(minute|hour|day|week|month)s?\s*ago', relative_str)
            if not match:
                return relative_str
            
            number = int(match.group(1))
            unit = match.group(2)
            
            if unit == 'minute':
                target_date = now - timedelta(minutes=number)
            elif unit == 'hour':
                target_date = now - timedelta(hours=number)
            elif unit == 'day':
                target_date = now - timedelta(days=number)
            elif unit == 'week':
                target_date = now - timedelta(weeks=number)
            elif unit == 'month':
                target_date = now - timedelta(days=number * 30)
            else:
                return relative_str
            
            return target_date.strftime('%Y-%m-%d')
            
        except Exception:
            return relative_str
    
    def _split_concatenated_field(self, text: str) -> Dict[str, str]:
        """Разделяет склеенное поле на составляющие"""
        result = {
            'price': '',
            'location': '',
            'clean_title': ''
        }
        
        # Поиск цены
        price_matches = re.findall(r'\$\d{1,2}(?:,\d{3})*|\$\d{3,6}', text)
        if price_matches:
            result['price'] = ' '.join(price_matches)
            # Удаляем цены из текста
            for price in price_matches:
                text = text.replace(price, ' ')
        
        # Поиск локации (штат + город)
        location_pattern = r'([A-Za-z\s]+,\s*(?:NY|NJ|PA|CT|MA|DE|MD|VA|FL|NC|SC)(?:\s*\d+K?\s*miles?)?)'
        location_match = re.search(location_pattern, text)
        if location_match:
            result['location'] = location_match.group(1).strip()
            text = text.replace(location_match.group(0), ' ')
        
        # Оставшийся текст как title
        # Удаляем лишние пробелы и оставляем осмысленную часть
        clean_parts = []
        for part in text.split():
            if len(part) > 2 and not part.isdigit():
                clean_parts.append(part)
        
        result['clean_title'] = ' '.join(clean_parts[:6])  # Ограничиваем 6 словами
        
        return result
    
    async def _extract_listings_from_page(self, page: Page, verbose: bool = False) -> List[Listing]:
        """Извлекает объявления со страницы"""
        results = []
        seen_ids = set()
        
        # Находим все ссылки на объявления
        anchors = await page.query_selector_all(ANCHOR_SELECTOR)
        
        if verbose:
            print(f"Found {len(anchors)} candidate anchors")
        
        for anchor in anchors:
            try:
                href = await anchor.get_attribute('href') or ''
                if not href or '/marketplace/item/' not in href:
                    continue
                
                # Извлекаем listing_id
                listing_id = ''
                for part in href.split('/'):
                    if part.isdigit() and len(part) >= MIN_ID_LENGTH:
                        listing_id = part
                        break
                
                if not listing_id or listing_id in seen_ids:
                    continue
                
                # Получаем текст контейнера
                container = await anchor.evaluate("(node) => node.closest('div') || node")
                if container:
                    text_content = await anchor.evaluate("(node) => (node.closest('div') || node).innerText")
                else:
                    text_content = await anchor.inner_text()
                
                lines = [l.strip() for l in text_content.split('\n') if l.strip()]
                
                # Парсим поля
                raw_title = lines[0] if lines else ''
                price_text = ''
                location = ''
                description = ''
                listed_date = ''
                
                # Умное определение полей
                for i, line in enumerate(lines[1:10], 1):
                    if not price_text and ('$' in line or (any(ch.isdigit() for ch in line) and len(line) < 20)):
                        price_text = line
                        continue
                    elif not location and (',' in line and any(state in line.upper() for state in ['NY', 'NJ', 'PA', 'CT', 'MA', 'DE', 'MD', 'VA'])):
                        location = line
                        continue
                    elif not listed_date and any(word in line.lower() for word in ['ago', 'day', 'week', 'month', 'hour', 'minute']):
                        listed_date = line
                        continue
                    elif len(line) > 25 and not any(word in line.lower() for word in ['ago', 'day', 'week']) and '$' not in line:
                        if not description:
                            description = line
                        else:
                            description += ' ' + line
                
                # Обработка title/price swap
                title = raw_title
                if '$' in raw_title and not price_text:
                    price_text = raw_title
                    for line in lines[1:4]:
                        if '$' not in line and len(line) > 5 and not any(word in line.lower() for word in ['ago', 'day', 'week']):
                            title = line
                            break
                
                # Улучшенная обработка склеенных полей
                if len(title) > 80 and ('$' in title or 'honda' in title.lower()):
                    # Попытка разделить склеенное поле
                    title_parts = self._split_concatenated_field(title)
                    if title_parts['price'] and not price_text:
                        price_text = title_parts['price']
                    if title_parts['location'] and not location:
                        location = title_parts['location']
                    if title_parts['clean_title']:
                        title = title_parts['clean_title']
                
                # Извлекаем изображение
                img_element = await anchor.query_selector('img')
                image_url = await img_element.get_attribute('src') if img_element else None
                
                # Формируем полную ссылку
                full_url = href if href.startswith('http') else f"https://www.facebook.com{href}"
                
                # Парсим дату
                parsed_date = self._parse_relative_date(listed_date)
                
                listing = Listing(
                    listing_id=listing_id,
                    title=title,
                    price_text=price_text,
                    location=location,
                    url=full_url,
                    image=image_url,
                    description=description,
                    listed_date=listed_date,
                    listed_date_parsed=parsed_date,
                    scraped_at=time.time()
                )
                
                results.append(listing)
                seen_ids.add(listing_id)
                
            except Exception as e:
                if verbose:
                    print(f"Error extracting listing: {e}")
                continue
        
        return results
    
    async def _scroll_and_collect(self, page: Page, max_scrolls: int = 3, delay: float = 2.0, verbose: bool = False) -> List[Listing]:
        """Прокручивает страницу и собирает объявления"""
        aggregated = {}
        last_height = 0
        stable_repeats = 0
        
        for i in range(max_scrolls):
            listings = await self._extract_listings_from_page(page, verbose=verbose)
            
            if verbose:
                print(f"Scroll {i}: found {len(listings)} listings (total unique: {len(aggregated)})")
            
            for listing in listings:
                aggregated[listing.listing_id] = listing
            
            # Прокрутка
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight);")
            await asyncio.sleep(delay)
            
            # Проверка изменения высоты
            height = await page.evaluate('document.body.scrollHeight')
            if height == last_height:
                stable_repeats += 1
                if stable_repeats >= 2:
                    break
            else:
                stable_repeats = 0
            last_height = height
        
        return list(aggregated.values())
    
    async def scrape_search(self, base_url: str, params: Dict[str, str], verbose: bool = False) -> List[Dict[str, Any]]:
        """Скрапит результаты поиска"""
        # Формируем URL с параметрами
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        url = f"{base_url}?{query_string}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"]
            )
            
            context = await browser.new_context(user_agent=USER_AGENT)
            
            # Применяем cookies
            if self.cookies:
                await context.add_cookies(self.cookies)
            
            page = await context.new_page()
            
            try:
                # Переходим на страницу
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                
                # Собираем данные
                listings = await self._scroll_and_collect(page, max_scrolls=3, verbose=verbose)
                
                # Конвертируем в словари
                return [listing.to_dict() for listing in listings]
                
            except Exception as e:
                if verbose:
                    print(f"Error scraping {url}: {e}")
                raise
            finally:
                await browser.close()
