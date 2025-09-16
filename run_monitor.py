#!/usr/bin/env python3
"""
Полный запуск мониторинга Honda CB500F/CB500X
"""

import asyncio
import sys
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from monitor import CB500Monitor

async def run_full_monitor():
    """Полный мониторинг всех регионов"""
    load_dotenv()
    
    print("🚀 Запуск полного мониторинга Honda CB500F/CB500X")
    print("=" * 50)
    
    data_dir = Path("data")
    cookies_path = Path("cookies.json")
    
    if not cookies_path.exists():
        print("❌ Файл cookies.json не найден")
        return
    
    monitor = CB500Monitor(data_dir, cookies_path)
    
    print(f"🔍 Мониторинг регионов: {len(monitor.SEARCH_REGIONS)}")
    for region in monitor.SEARCH_REGIONS:
        print(f"  • {region.name}")
    
    print(f"🔍 Поисковые запросы: {', '.join(monitor.SEARCH_QUERIES)}")
    print(f"💰 Ценовой диапазон: ${monitor.MIN_PRICE:,} - ${monitor.MAX_PRICE:,}")
    print()
    
    try:
        # Запускаем полный цикл мониторинга
        await monitor.run_monitor_cycle()
        
        print("\n✅ Полный мониторинг завершен успешно!")
        
        # Показываем статистику
        current_state = monitor.storage.load_current_state()
        print(f"📊 Всего найдено объявлений: {len(current_state)}")
        
        # Группируем по регионам
        by_region = {}
        for listing in current_state.values():
            region = listing.get('search_region', 'Unknown')
            by_region[region] = by_region.get(region, 0) + 1
        
        print("\n📍 По регионам:")
        for region, count in sorted(by_region.items()):
            print(f"  • {region}: {count}")
        
        # Группируем по моделям
        cb500f_count = 0
        cb500x_count = 0
        for listing in current_state.values():
            text = f"{listing.get('title', '')} {listing.get('price_text', '')}".lower()
            if 'cb500x' in text:
                cb500x_count += 1
            elif 'cb500f' in text:
                cb500f_count += 1
        
        print(f"\n🏍️ По моделям:")
        print(f"  • CB500F: {cb500f_count}")
        print(f"  • CB500X: {cb500x_count}")
        
        # Ценовая статистика
        prices = []
        for listing in current_state.values():
            price = monitor.extract_price(f"{listing.get('title', '')} {listing.get('price_text', '')}")
            if price:
                prices.append(price)
        
        if prices:
            print(f"\n💰 Ценовая статистика:")
            print(f"  • Средняя: ${sum(prices)/len(prices):,.0f}")
            print(f"  • Минимум: ${min(prices):,.0f}")
            print(f"  • Максимум: ${max(prices):,.0f}")
        
        print(f"\n📁 Данные сохранены в: {data_dir}")
        
    except Exception as e:
        print(f"❌ Ошибка при мониторинге: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(run_full_monitor())