#!/usr/bin/env python3
"""
Модуль для хранения и управления данными мониторинга
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class DataStorage:
    """Класс для работы с хранением данных"""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.current_state_file = data_dir / "current_state.json"
        self.historical_dir = data_dir / "historical"
        
        # Создаем необходимые директории
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.historical_dir.mkdir(parents=True, exist_ok=True)
    
    def load_current_state(self) -> Dict[str, Dict[str, Any]]:
        """Загружает текущее состояние базы объявлений"""
        if not self.current_state_file.exists():
            logger.info("No current state file found, starting fresh")
            return {}
        
        try:
            with open(self.current_state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Конвертируем список в словарь по listing_id
            if isinstance(data, list):
                state = {item.get('listing_id'): item for item in data if item.get('listing_id')}
            else:
                state = data
            
            logger.info(f"Loaded {len(state)} listings from current state")
            return state
            
        except (json.JSONDecodeError, Exception) as e:
            logger.error(f"Error loading current state: {e}")
            return {}
    
    def save_current_state(self, listings: List[Dict[str, Any]]):
        """Сохраняет текущее состояние"""
        try:
            # Создаем словарь по listing_id для удобства поиска
            state = {listing.get('listing_id'): listing for listing in listings if listing.get('listing_id')}
            
            # Сохраняем как список для совместимости
            listings_list = list(state.values())
            
            with open(self.current_state_file, 'w', encoding='utf-8') as f:
                json.dump(listings_list, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved current state with {len(listings_list)} listings")
            
        except Exception as e:
            logger.error(f"Error saving current state: {e}")
            raise
    
    def save_historical_data(self, listings: List[Dict[str, Any]], timestamp: datetime):
        """Сохраняет исторические данные"""
        try:
            # Форматируем имя файла
            filename = f"listings_{timestamp.strftime('%Y%m%d_%H%M%S')}.json"
            filepath = self.historical_dir / filename
            
            # Добавляем метаданные
            data = {
                'timestamp': timestamp.isoformat(),
                'count': len(listings),
                'listings': listings
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Saved historical data to {filename}")
            
            # Очистка старых файлов (оставляем последние 30 дней)
            self._cleanup_old_files()
            
        except Exception as e:
            logger.error(f"Error saving historical data: {e}")
    
    def _cleanup_old_files(self, keep_days: int = 30):
        """Очищает старые исторические файлы"""
        try:
            cutoff_timestamp = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)
            
            deleted_count = 0
            for file_path in self.historical_dir.glob("listings_*.json"):
                if file_path.stat().st_mtime < cutoff_timestamp:
                    file_path.unlink()
                    deleted_count += 1
            
            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old historical files")
                
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    def get_historical_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """Получает исторические данные за указанное количество дней"""
        try:
            cutoff_timestamp = datetime.now().timestamp() - (days * 24 * 60 * 60)
            historical_data = []
            
            for file_path in sorted(self.historical_dir.glob("listings_*.json")):
                if file_path.stat().st_mtime >= cutoff_timestamp:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        historical_data.append(data)
            
            return historical_data
            
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Получает статистику по данным"""
        try:
            current_state = self.load_current_state()
            historical_data = self.get_historical_data(7)
            
            stats = {
                'current_listings_count': len(current_state),
                'historical_files_count': len(historical_data),
                'total_historical_listings': sum(data.get('count', 0) for data in historical_data),
                'data_dir_size_mb': self._get_directory_size() / (1024 * 1024),
                'oldest_historical_file': None,
                'newest_historical_file': None
            }
            
            # Находим самый старый и новый файлы
            historical_files = list(self.historical_dir.glob("listings_*.json"))
            if historical_files:
                oldest_file = min(historical_files, key=lambda f: f.stat().st_mtime)
                newest_file = max(historical_files, key=lambda f: f.stat().st_mtime)
                
                stats['oldest_historical_file'] = datetime.fromtimestamp(oldest_file.stat().st_mtime).isoformat()
                stats['newest_historical_file'] = datetime.fromtimestamp(newest_file.stat().st_mtime).isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}
    
    def _get_directory_size(self) -> int:
        """Получает размер директории данных"""
        total_size = 0
        try:
            for file_path in self.data_dir.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception:
            pass
        return total_size
    
    def backup_data(self) -> Path:
        """Создает резервную копию всех данных"""
        try:
            backup_filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = self.data_dir / backup_filename
            
            # Собираем все данные
            backup_data = {
                'current_state': self.load_current_state(),
                'historical_data': self.get_historical_data(30),  # 30 дней истории
                'statistics': self.get_statistics(),
                'created_at': datetime.now().isoformat()
            }
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Created backup at {backup_path}")
            return backup_path
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise
