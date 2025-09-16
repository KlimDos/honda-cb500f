#!/usr/bin/env python3
"""
Скрипт для просмотра базы данных CB500F мониторинга через kubectl exec
"""

import json
import sys
from datetime import datetime
from typing import Dict, List, Any

def format_listing(listing: Dict[str, Any], index: int) -> str:
    """Форматирует объявление для вывода"""
    listing_id = listing.get('listing_id', 'unknown')
    title = listing.get('title', 'N/A')
    price_text = listing.get('price_text', 'N/A')
    location = listing.get('location', 'N/A')
    search_region = listing.get('search_region', 'N/A')
    search_query = listing.get('search_query', 'N/A')
    url = listing.get('url', 'N/A')
    
    # Время скрапинга
    scraped_at = listing.get('scraped_at', 0)
    if scraped_at:
        scraped_time = datetime.fromtimestamp(scraped_at).strftime('%Y-%m-%d %H:%M:%S')
    else:
        scraped_time = 'N/A'
    
    return f"""
{'='*60}
{index}. ID: {listing_id}
   Заголовок: {title}
   Цена: {price_text}
   Локация: {location}
   Регион поиска: {search_region}
   Запрос: {search_query}
   Время скрапинга: {scraped_time}
   URL: {url[:80]}{'...' if len(url) > 80 else ''}
"""

def show_summary(listings: List[Dict[str, Any]]):
    """Показывает краткую сводку"""
    total = len(listings)
    
    # Группировка по регионам
    regions = {}
    for listing in listings:
        region = listing.get('search_region', 'Unknown')
        regions[region] = regions.get(region, 0) + 1
    
    # Группировка по запросам
    queries = {}
    for listing in listings:
        query = listing.get('search_query', 'Unknown')
        queries[query] = queries.get(query, 0) + 1
    
    print(f"""
📊 СВОДКА БАЗЫ ДАННЫХ CB500F
{'='*50}
Всего объявлений: {total}

По регионам:""")
    
    for region, count in sorted(regions.items()):
        print(f"  {region}: {count}")
    
    print("\nПо поисковым запросам:")
    for query, count in sorted(queries.items()):
        print(f"  '{query}': {count}")

def main():
    """Главная функция"""
    if len(sys.argv) < 2:
        print("Использование: python view_database.py <json_file_path>")
        print("Например: python view_database.py /app/data/current_state.json")
        return
    
    file_path = sys.argv[1]
    show_details = '--detailed' in sys.argv
    
    try:
        # Читаем JSON из stdin (из kubectl exec)
        if file_path == '-':
            data = json.load(sys.stdin)
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        # Определяем формат данных
        if isinstance(data, list):
            # Формат current_state.json
            listings = data
            print(f"📁 Текущее состояние ({len(listings)} объявлений)")
        elif isinstance(data, dict) and 'listings' in data:
            # Формат historical data
            listings = data['listings']
            timestamp = data.get('timestamp', 'Unknown')
            count = data.get('count', len(listings))
            print(f"📅 Исторические данные от {timestamp} ({count} объявлений)")
        else:
            print("❌ Неизвестный формат данных")
            return
        
        # Показываем сводку
        show_summary(listings)
        
        if show_details:
            print(f"\n📋 ДЕТАЛЬНЫЙ СПИСОК ОБЪЯВЛЕНИЙ")
            for i, listing in enumerate(listings, 1):
                print(format_listing(listing, i))
        else:
            print(f"\n💡 Для детального просмотра используйте флаг --detailed")
    
    except FileNotFoundError:
        print(f"❌ Файл не найден: {file_path}")
    except json.JSONDecodeError as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    main()
