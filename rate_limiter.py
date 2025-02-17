from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import time
from logger import logger

class RateLimiter:
    """
    Простой rate limiter для защиты от флуда
    
    Attributes:
        limits (Dict): Настройки лимитов для разных типов пользователей
        requests (Dict): Хранилище запросов пользователей
        violations (Dict): Счетчик нарушений пользователей
    """
    
    def __init__(self):
        # Настройки лимитов: количество запросов и интервал в секундах
        self.limits = {
            'default': {'requests': 20, 'interval': 60},  # 20 запросов в минуту
            'admin': {'requests': 100, 'interval': 60},   # 100 запросов в минуту
            'new_user': {'requests': 10, 'interval': 60}  # 10 запросов в минуту для новых пользователей
        }
        
        # Хранилище запросов пользователей: {user_id: [(timestamp, count)]}
        self.requests = defaultdict(list)
        
        # Счетчик нарушений: {user_id: count}
        self.violations = defaultdict(int)
        
        logger.info("Rate limiter инициализирован")
    
    def _clean_old_requests(self, user_id: int, interval: int) -> None:
        """
        Очистка устаревших запросов пользователя
        
        Args:
            user_id (int): ID пользователя
            interval (int): Интервал в секундах
        """
        current_time = time.time()
        self.requests[user_id] = [
            (ts, count) for ts, count in self.requests[user_id]
            if current_time - ts < interval
        ]
    
    def check_limit(self, user_id: int, user_type: str = 'default') -> Tuple[bool, Optional[float]]:
        """
        Проверка, не превышен ли лимит запросов
        
        Args:
            user_id (int): ID пользователя
            user_type (str): Тип пользователя ('default', 'admin', 'new_user')
            
        Returns:
            Tuple[bool, Optional[float]]: (разрешено ли, время до сброса)
        """
        limit = self.limits.get(user_type, self.limits['default'])
        max_requests = limit['requests']
        interval = limit['interval']
        
        # Очищаем старые запросы
        self._clean_old_requests(user_id, interval)
        
        # Считаем текущее количество запросов
        current_time = time.time()
        total_requests = sum(count for ts, count in self.requests[user_id])
        
        if total_requests >= max_requests:
            # Находим время до сброса лимита
            oldest_ts = min(ts for ts, _ in self.requests[user_id]) if self.requests[user_id] else current_time
            time_to_reset = interval - (current_time - oldest_ts)
            return False, max(0, time_to_reset)
            
        return True, None
    
    def add_request(self, user_id: int) -> None:
        """
        Добавление нового запроса
        
        Args:
            user_id (int): ID пользователя
        """
        current_time = time.time()
        self.requests[user_id].append((current_time, 1))
        logger.debug(f"Добавлен новый запрос для пользователя {user_id}")
    
    def add_violation(self, user_id: int) -> int:
        """
        Добавление нарушения и получение общего количества
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            int: Общее количество нарушений
        """
        self.violations[user_id] += 1
        violations_count = self.violations[user_id]
        logger.warning(f"Добавлено нарушение для пользователя {user_id}. Всего нарушений: {violations_count}")
        return violations_count
    
    def reset_violations(self, user_id: int) -> None:
        """
        Сброс счетчика нарушений
        
        Args:
            user_id (int): ID пользователя
        """
        if user_id in self.violations:
            del self.violations[user_id]
            logger.info(f"Сброшены нарушения для пользователя {user_id}")
    
    def get_user_stats(self, user_id: int) -> Dict:
        """
        Получение статистики пользователя
        
        Args:
            user_id (int): ID пользователя
            
        Returns:
            Dict: Статистика пользователя
        """
        self._clean_old_requests(user_id, max(limit['interval'] for limit in self.limits.values()))
        
        return {
            'requests': len(self.requests[user_id]),
            'violations': self.violations[user_id],
            'last_request': max((ts for ts, _ in self.requests[user_id]), default=None)
        } 