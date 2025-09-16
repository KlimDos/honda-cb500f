#!/usr/bin/env python3
"""
Локальный тест мониторинга CB500F/CB500X
"""

import asyncio
import sys
import os
from pathlib import Path

# Добавляем src в путь
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dotenv import load_dotenv
from monitor import CB500Monitor

async def test_telegram():
    """Тест Telegram уведомлений"""
    from telegram_notifier import TelegramNotifier
    
    print("🔍 Тестирование Telegram...")
    telegram = TelegramNotifier()
    
    # Тестовое объявление
    test_listing = {
        'listing_id': 'test123',
        'title': '2019 Honda CB500F',
        'price_text': '$4,200',
        'location': 'Test Location, NJ',
        'url': 'https://facebook.com/marketplace/item/test123',
        'description': 'Test motorcycle in excellent condition',
        'listed_date': '2 days ago',
        'image': None
    }
    
    try:
        result = await telegram.send_new_listing(test_listing)
        if result:
            print("✅ Telegram тест прошел успешно!")
            return True
        else:
            print("❌ Telegram вернул ошибку (проверьте токен и права бота)")
            return False
    except Exception as e:
        print(f"❌ Ошибка Telegram: {e}")
        return False

async def test_scraper():
    """Тест скрапера (без реального запроса)"""
    from fb_scraper import FacebookMarketplaceScraper
    
    print("🔍 Тестирование скрапера...")
    
    cookies_path = Path("cookies.json")
    if not cookies_path.exists():
        print("❌ Файл cookies.json не найден")
        return False
    
    try:
        scraper = FacebookMarketplaceScraper(cookies_path)
        print("✅ Скрапер инициализирован успешно!")
        return True
    except Exception as e:
        print(f"❌ Ошибка скрапера: {e}")
        return False

async def test_storage():
    """Тест системы хранения"""
    from data_storage import DataStorage
    
    print("🔍 Тестирование хранилища...")
    
    try:
        storage = DataStorage(Path("data"))
        
        # Тестовые данные
        test_data = [
            {
                'listing_id': 'test1',
                'title': 'Test Listing 1',
                'price_text': '$4000'
            }
        ]
        
        storage.save_current_state(test_data)
        loaded = storage.load_current_state()
        
        if len(loaded) == 1 and loaded['test1']['title'] == 'Test Listing 1':
            print("✅ Хранилище работает!")
            return True
        else:
            print("❌ Ошибка хранилища: данные не совпадают")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка хранилища: {e}")
        return False

async def test_monitor_light():
    """Легкий тест мониторинга (без реального скрапинга)"""
    print("🔍 Тестирование мониторинга...")
    
    try:
        data_dir = Path("data")
        cookies_path = Path("cookies.json")
        
        if not cookies_path.exists():
            print("❌ Файл cookies.json не найден")
            return False
        
        monitor = CB500Monitor(data_dir, cookies_path)
        
        # Тест извлечения цены
        test_price = monitor.extract_price("$4,500")
        if test_price == 4500:
            print("✅ Извлечение цены работает!")
        else:
            print(f"❌ Ошибка извлечения цены: {test_price}")
            return False
        
        # Тест проверки релевантности
        test_listing = {
            'title': '2019 Honda CB500F',
            'price_text': '$4,200',
            'description': 'Great bike'
        }
        
        if monitor.is_relevant_listing(test_listing):
            print("✅ Проверка релевантности работает!")
        else:
            print("❌ Ошибка проверки релевантности")
            return False
        
        print("✅ Мониторинг инициализирован успешно!")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка мониторинга: {e}")
        return False

async def main():
    """Главная функция тестирования"""
    print("🚀 Локальное тестирование CB500F/CB500X мониторинга")
    print("=" * 50)
    
    # Загружаем .env
    load_dotenv()
    
    # Проверяем переменные окружения
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN не установлен в .env")
        return
    
    if not chat_id:
        print("❌ TELEGRAM_CHAT_ID не установлен в .env")
        return
    
    print(f"✅ Bot token: {bot_token[:10]}...")
    print(f"✅ Chat ID: {chat_id}")
    print()
    
    # Запускаем тесты
    tests = [
        ("Хранилище данных", test_storage),
        ("Скрапер Facebook", test_scraper),
        ("Telegram уведомления", test_telegram),
        ("Мониторинг (легкий)", test_monitor_light),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"📋 {test_name}...")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Критическая ошибка в {test_name}: {e}")
            results.append((test_name, False))
        print()
    
    # Итоги
    print("📊 Результаты тестирования:")
    print("-" * 30)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1
    
    print(f"\nПройдено: {passed}/{len(results)} тестов")
    
    if passed == len(results):
        print("\n🎉 Все тесты прошли! Готово к запуску полного мониторинга.")
    else:
        print(f"\n⚠️ Исправьте ошибки перед запуском.")

if __name__ == "__main__":
    asyncio.run(main())
