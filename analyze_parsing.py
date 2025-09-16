#!/usr/bin/env python3
"""
Анализ качества парсинга и предложения улучшений
"""

import json
import re
from typing import Dict, List, Any, Optional

def analyze_parsing_quality(listings: List[Dict]) -> Dict[str, Any]:
    """Анализирует качество парсинга объявлений"""
    
    issues = {
        'empty_locations': [],
        'empty_dates': [],
        'malformed_titles': [],
        'price_parsing_issues': [],
        'concatenated_fields': []
    }
    
    stats = {
        'total_listings': len(listings),
        'has_location': 0,
        'has_date': 0,
        'price_extracted_ok': 0,
        'title_clean': 0
    }
    
    for listing in listings:
        listing_id = listing.get('listing_id', 'unknown')
        title = listing.get('title', '')
        price_text = listing.get('price_text', '')
        location = listing.get('location', '')
        listed_date = listing.get('listed_date', '')
        
        # Проверка location
        if location.strip():
            stats['has_location'] += 1
        else:
            issues['empty_locations'].append(listing_id)
        
        # Проверка date
        if listed_date.strip():
            stats['has_date'] += 1
        else:
            issues['empty_dates'].append(listing_id)
        
        # Проверка title на конкатенацию
        if len(title) > 100 or ('$' in title and 'honda' in title.lower() and any(c in title for c in [',', 'NY', 'NJ', 'miles'])):
            issues['concatenated_fields'].append({
                'id': listing_id,
                'title': title,
                'suggested_fix': suggest_title_fix(title)
            })
        else:
            stats['title_clean'] += 1
        
        # Проверка извлечения цены
        extracted_price = extract_price(title + ' ' + price_text)
        if extracted_price > 0:
            stats['price_extracted_ok'] += 1
        else:
            issues['price_parsing_issues'].append({
                'id': listing_id,
                'title': title,
                'price_text': price_text
            })
    
    return {
        'stats': stats,
        'issues': issues,
        'quality_score': calculate_quality_score(stats)
    }

def extract_price(text: str) -> float:
    """Извлекает цену из текста"""
    if not text:
        return 0.0
    
    price_matches = re.findall(r'\$(\d{1,2}(?:,\d{3})*|\d{3,6})', text)
    if not price_matches:
        return 0.0
    
    try:
        prices = [float(match.replace(',', '')) for match in price_matches]
        return max(prices) if prices else 0.0
    except ValueError:
        return 0.0

def suggest_title_fix(title: str) -> Dict[str, str]:
    """Предлагает исправление для склеенного title"""
    suggestion = {
        'original': title,
        'suggested_title': '',
        'suggested_price': '',
        'suggested_location': '',
        'suggested_year_model': ''
    }
    
    # Попытка разделить склеенные поля
    parts = title.split()
    price_part = ''
    year_model_part = ''
    location_part = ''
    title_part = ''
    
    for i, part in enumerate(parts):
        # Цена
        if '$' in part:
            price_part += part + ' '
        # Год и модель
        elif re.match(r'\d{4}', part) or 'honda' in part.lower() or 'cb500' in part.lower():
            year_model_part += part + ' '
        # Локация (содержит штаты или города)
        elif any(state in part.upper() for state in ['NY', 'NJ', 'PA', 'CT', 'MA', 'DE', 'MD', 'VA']) or ',' in part:
            location_part += part + ' '
        # Миля или другие характеристики
        elif 'miles' in part.lower() or 'km' in part.lower():
            title_part += part + ' '
    
    suggestion['suggested_price'] = price_part.strip()
    suggestion['suggested_year_model'] = year_model_part.strip()
    suggestion['suggested_location'] = location_part.strip()
    suggestion['suggested_title'] = (year_model_part + title_part).strip()
    
    return suggestion

def calculate_quality_score(stats: Dict[str, int]) -> float:
    """Вычисляет общий балл качества парсинга"""
    total = stats['total_listings']
    if total == 0:
        return 0.0
    
    score = 0.0
    score += (stats['has_location'] / total) * 0.25  # 25% за локацию
    score += (stats['has_date'] / total) * 0.20      # 20% за дату
    score += (stats['price_extracted_ok'] / total) * 0.30  # 30% за цену
    score += (stats['title_clean'] / total) * 0.25   # 25% за чистоту title
    
    return score * 100

def generate_improvement_suggestions(analysis: Dict[str, Any]) -> List[str]:
    """Генерирует предложения по улучшению парсинга"""
    suggestions = []
    issues = analysis['issues']
    
    if issues['empty_locations']:
        suggestions.append(f"🏠 Исправить парсинг локации для {len(issues['empty_locations'])} объявлений")
        suggestions.append("   - Улучшить regex для определения городов/штатов")
        suggestions.append("   - Добавить fallback поиск локации в description")
    
    if issues['empty_dates']:
        suggestions.append(f"📅 Исправить парсинг дат для {len(issues['empty_dates'])} объявлений")
        suggestions.append("   - Расширить regex для относительных дат")
        suggestions.append("   - Добавить поиск дат в разных форматах")
    
    if issues['concatenated_fields']:
        suggestions.append(f"✂️ Исправить склеенные поля для {len(issues['concatenated_fields'])} объявлений")
        suggestions.append("   - Улучшить разделение текста на поля")
        suggestions.append("   - Добавить дополнительную обработку DOM структуры")
    
    if issues['price_parsing_issues']:
        suggestions.append(f"💰 Исправить парсинг цен для {len(issues['price_parsing_issues'])} объявлений")
    
    return suggestions

def main():
    """Главная функция"""
    print("🔍 Анализ качества парсинга CB500F мониторинга")
    
    # Загружаем данные (симуляция - в реальности из kubectl)
    sample_data = [
        {
            "listing_id": "1984086672351158",
            "title": "$5,495",
            "price_text": "2023 Honda cb500f",
            "location": "Dover, DE",
            "listed_date": "",
            "scraped_at": 1758055536.0910509
        },
        {
            "listing_id": "1469810090903514",
            "title": "$5,500",
            "price_text": "2022 Honda cb500f",
            "location": "Long Valley, NJ",
            "listed_date": "",
            "scraped_at": 1758055539.1850715
        },
        {
            "listing_id": "1708704936495618",
            "title": "$2,700$3,5002014 Honda cb500fJackson Heights, NY32K miles",
            "price_text": "$2,700$3,5002014 Honda cb500fJackson Heights, NY32K miles",
            "location": "",
            "listed_date": "",
            "scraped_at": 1758055583.894016
        }
    ]
    
    # Анализируем качество
    analysis = analyze_parsing_quality(sample_data)
    
    print(f"\n📊 Статистика качества парсинга:")
    print(f"Общий балл качества: {analysis['quality_score']:.1f}/100")
    print(f"Всего объявлений: {analysis['stats']['total_listings']}")
    print(f"С локацией: {analysis['stats']['has_location']}/{analysis['stats']['total_listings']}")
    print(f"С датой: {analysis['stats']['has_date']}/{analysis['stats']['total_listings']}")
    print(f"Цена извлечена: {analysis['stats']['price_extracted_ok']}/{analysis['stats']['total_listings']}")
    print(f"Чистый title: {analysis['stats']['title_clean']}/{analysis['stats']['total_listings']}")
    
    # Показываем проблемы
    print(f"\n❌ Найденные проблемы:")
    for issue_type, issues in analysis['issues'].items():
        if issues:
            print(f"  {issue_type}: {len(issues)} объявлений")
    
    # Детальный анализ проблемного объявления
    if analysis['issues']['concatenated_fields']:
        print(f"\n🔍 Детальный анализ склеенных полей:")
        for issue in analysis['issues']['concatenated_fields']:
            print(f"\nID: {issue['id']}")
            print(f"Оригинал: {issue['title']}")
            fix = issue['suggested_fix']
            print(f"Предлагаемые исправления:")
            print(f"  Title: {fix['suggested_title']}")
            print(f"  Price: {fix['suggested_price']}")
            print(f"  Location: {fix['suggested_location']}")
            print(f"  Year/Model: {fix['suggested_year_model']}")
    
    # Предложения по улучшению
    print(f"\n💡 Предложения по улучшению:")
    suggestions = generate_improvement_suggestions(analysis)
    for suggestion in suggestions:
        print(f"  {suggestion}")
    
    print(f"\n✅ Общий вывод:")
    print(f"Парсер работает на {analysis['quality_score']:.1f}% от идеала.")
    if analysis['quality_score'] >= 80:
        print("Качество хорошее, требуются мелкие улучшения.")
    elif analysis['quality_score'] >= 60:
        print("Качество удовлетворительное, требуются улучшения.")
    else:
        print("Качество низкое, требуется серьезная доработка.")

if __name__ == "__main__":
    main()
