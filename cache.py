from typing import Optional, Dict, Any
import time
from datetime import datetime, timedelta
import json
from logger import logger

class Cache:
    """Класс для кэширования ответов бота"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Инициализация кэша
        
        Args:
            max_size (int): Максимальный размер кэша
            ttl (int): Время жизни записи в секундах
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl = ttl
        logger.info(f"Кэш инициализирован: max_size={max_size}, ttl={ttl}")
    
    def _generate_key(self, message: str) -> str:
        """
        Генерация ключа для кэша
        
        Args:
            message (str): Сообщение пользователя
            
        Returns:
            str: Ключ для кэша
        """
        # Нормализуем сообщение: приводим к нижнему регистру и убираем лишние пробелы
        normalized = " ".join(message.lower().split())
        return normalized
    
    def get(self, message: str) -> Optional[str]:
        """
        Получение ответа из кэша
        
        Args:
            message (str): Сообщение пользователя
            
        Returns:
            Optional[str]: Закэшированный ответ или None
        """
        key = self._generate_key(message)
        if key in self._cache:
            cache_data = self._cache[key]
            # Проверяем не истекло ли время жизни записи
            if time.time() - cache_data['timestamp'] <= self.ttl:
                logger.info(f"Найден кэш для сообщения: {message[:50]}...")
                return cache_data['response']
            else:
                # Удаляем устаревшую запись
                del self._cache[key]
                logger.info(f"Удалена устаревшая запись кэша для: {message[:50]}...")
        return None
    
    def set(self, message: str, response: str) -> None:
        """
        Сохранение ответа в кэш
        
        Args:
            message (str): Сообщение пользователя
            response (str): Ответ бота
        """
        # Если кэш переполнен, удаляем самую старую запись
        if len(self._cache) >= self.max_size:
            oldest_key = min(self._cache.items(), key=lambda x: x[1]['timestamp'])[0]
            del self._cache[oldest_key]
            logger.info("Удалена самая старая запись кэша из-за переполнения")
        
        key = self._generate_key(message)
        self._cache[key] = {
            'response': response,
            'timestamp': time.time()
        }
        logger.info(f"Добавлен кэш для сообщения: {message[:50]}...")
    
    def clear_expired(self) -> None:
        """Очистка устаревших записей"""
        current_time = time.time()
        expired_keys = [
            key for key, data in self._cache.items()
            if current_time - data['timestamp'] > self.ttl
        ]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            logger.info(f"Очищено {len(expired_keys)} устаревших записей кэша")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики кэша
        
        Returns:
            Dict[str, Any]: Статистика кэша
        """
        return {
            'total_entries': len(self._cache),
            'max_size': self.max_size,
            'ttl': self.ttl,
            'memory_usage': len(json.dumps(self._cache).encode('utf-8'))
        }
    
    def clear_user_history(self, user_id: int) -> None:
        """
        Очистка истории диалога для конкретного пользователя
        
        Args:
            user_id (int): ID пользователя
        """
        # Создаем ключ для пользователя
        user_key = f"user_{user_id}"
        
        # Удаляем все записи, связанные с пользователем
        keys_to_delete = [
            key for key in self._cache.keys()
            if key.startswith(user_key)
        ]
        
        for key in keys_to_delete:
            del self._cache[key]
            
        logger.info(f"Очищена история диалога для пользователя {user_id}") 