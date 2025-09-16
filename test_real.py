#!/usr/bin/env python3
"""
Тестовый запуск мониторинга с ограниченным скрапингом
"""

import asyncio
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from monitor import CB500Monitor

async def test_real_scraping():
    """Тест реального скрапинга с одним регионом"""
    load_dotenv()
    
    print("🚀 Запуск реального мониторинга (тестовый режим)")
    print("=" * 50)
    
    data_dir = Path("data")
    cookies_path = Path("cookies.json")
    
    if not cookies_path.exists():
        print("❌ Файл cookies.json не найден")
        return
    
    monitor = CB500Monitor(data_dir, cookies_path)
    
    # Тестируем только один регион
    original_regions = monitor.SEARCH_REGIONS
    monitor.SEARCH_REGIONS = [original_regions[0]]  # Только первый регион
    
    # Ограничиваем количество запросов
    original_queries = monitor.SEARCH_QUERIES
    monitor.SEARCH_QUERIES = ["cb500f"]  # Только один запрос
    
    print(f"🔍 Тестируем только регион: {monitor.SEARCH_REGIONS[0].name}")
    print(f"🔍 Поисковый запрос: {monitor.SEARCH_QUERIES[0]}")
    print()
    
    try:
        # Запускаем один цикл мониторинга
        await monitor.run_monitor_cycle()
        print("\n✅ Тестовый мониторинг завершен успешно!")
        
        # Показываем сохраненные данные
        current_state = monitor.storage.load_current_state()
        print(f"📊 Найдено и сохранено: {len(current_state)} объявлений")
        
        if current_state:
            print("\n📝 Примеры найденных объявлений:")
            for i, (listing_id, listing) in enumerate(list(current_state.items())[:3]):
                print(f"  {i+1}. {listing.get('title', 'N/A')} - {listing.get('price_text', 'N/A')}")
                print(f"     📍 {listing.get('location', 'N/A')}")
                print(f"     🔗 {listing.get('url', 'N/A')[:50]}...")
                print()
        
    except Exception as e:
        print(f"❌ Ошибка при тестировании: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_real_scraping())