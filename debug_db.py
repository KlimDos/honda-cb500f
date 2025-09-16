#!/usr/bin/env python3
"""
Утилита для анализа базы данных мониторинга CB500F
"""

import json
import subprocess
import sys
from datetime import datetime
from typing import Dict, List, Any

def run_kubectl_cmd(cmd: str) -> str:
    """Запускает kubectl команду и возвращает результат"""
    try:
        result = subprocess.run(
            ["kubectl"] + cmd.split()[1:], 
            capture_output=True, 
            text=True, 
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running kubectl command: {e}")
        return ""

def get_pod_name() -> str:
    """Получает имя активного пода"""
    output = run_kubectl_cmd("kubectl get pods -n cb500f -o name")
    for line in output.split('\n'):
        if 'cb500-monitor' in line and 'Running' in run_kubectl_cmd(f"kubectl get {line} -n cb500f"):
            return line.split('/')[-1]
    return ""

def load_current_state() -> List[Dict]:
    """Загружает текущее состояние из пода"""
    pod_name = get_pod_name()
    if not pod_name:
        print("No running pod found")
        return []
    
    try:
        data = run_kubectl_cmd(f"kubectl exec {pod_name} -n cb500f -- cat /app/data/current_state.json")
        return json.loads(data)
    except json.JSONDecodeError:
        print("Error parsing current_state.json")
        return []

def load_historical_data() -> List[Dict]:
    """Загружает исторические данные"""
    pod_name = get_pod_name()
    if not pod_name:
        return []
    
    # Получаем список файлов
    files = run_kubectl_cmd(f"kubectl exec {pod_name} -n cb500f -- ls /app/data/historical/")
    historical_data = []
    
    for filename in files.split('\n'):
        if filename.endswith('.json'):
            try:
                data = run_kubectl_cmd(f"kubectl exec {pod_name} -n cb500f -- cat /app/data/historical/{filename}")
                parsed = json.loads(data)
                historical_data.append({
                    'filename': filename,
                    'timestamp': parsed.get('timestamp'),
                    'count': parsed.get('count'),
                    'listings': parsed.get('listings', [])
                })
            except json.JSONDecodeError:
                continue
    
    return sorted(historical_data, key=lambda x: x['filename'])

def extract_price(text: str) -> float:
    """Извлекает цену из текста"""
    import re
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

def analyze_listing(listing: Dict) -> Dict:
    """Анализирует одно объявление"""
    price = extract_price(listing.get('price_text', '') + listing.get('title', ''))
    
    return {
        'id': listing.get('listing_id', 'unknown'),
        'title': listing.get('title', ''),
        'price_text': listing.get('price_text', ''),
        'price_extracted': price,
        'location': listing.get('location', ''),
        'search_region': listing.get('search_region', ''),
        'search_query': listing.get('search_query', ''),
        'url': listing.get('url', ''),
        'scraped_at': datetime.fromtimestamp(listing.get('scraped_at', 0)).strftime('%Y-%m-%d %H:%M:%S') if listing.get('scraped_at') else ''
    }

def print_listing_summary(listings: List[Dict]):
    """Выводит краткую сводку объявлений"""
    print(f"\n📊 Найдено {len(listings)} объявлений:")
    print("=" * 80)
    
    for i, listing in enumerate(listings, 1):
        analyzed = analyze_listing(listing)
        print(f"{i}. ID: {analyzed['id']}")
        print(f"   Название: {analyzed['title'][:70]}")
        print(f"   Цена: {analyzed['price_text']} (извлечено: ${analyzed['price_extracted']:.0f})")
        print(f"   Локация: {analyzed['location']}")
        print(f"   Регион поиска: {analyzed['search_region']}")
        print(f"   Запрос: {analyzed['search_query']}")
        print(f"   Время скрапинга: {analyzed['scraped_at']}")
        print(f"   URL: {analyzed['url'][:50]}...")
        print("-" * 80)

def main():
    """Главная функция"""
    print("🔍 Анализ базы данных CB500F мониторинга")
    
    # Текущее состояние
    current = load_current_state()
    print(f"\n📁 Текущее состояние: {len(current)} объявлений")
    if current:
        print_listing_summary(current)
    
    # Историческе данные
    historical = load_historical_data()
    print(f"\n📚 Исторические данные: {len(historical)} файлов")
    
    for hist in historical:
        print(f"\n📅 {hist['filename']} - {hist['timestamp']} - {hist['count']} объявлений")
        if len(sys.argv) > 1 and sys.argv[1] == '--detailed':
            print_listing_summary(hist['listings'])
    
    # Статистика
    all_listings = []
    all_listings.extend(current)
    for hist in historical:
        all_listings.extend(hist['listings'])
    
    # Уникальные ID
    unique_ids = set(listing.get('listing_id') for listing in all_listings)
    
    # Статистика по регионам
    region_stats = {}
    for listing in all_listings:
        region = listing.get('search_region', 'Unknown')
        if region not in region_stats:
            region_stats[region] = 0
        region_stats[region] += 1
    
    print(f"\n📈 Статистика:")
    print(f"Всего уникальных ID: {len(unique_ids)}")
    print(f"Всего записей: {len(all_listings)}")
    print("\nПо регионам:")
    for region, count in sorted(region_stats.items()):
        print(f"  {region}: {count}")

if __name__ == "__main__":
    main()
