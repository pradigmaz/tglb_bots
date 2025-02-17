import asyncio
import logging
from typing import Optional, Dict, Any, Callable, TypeVar
from functools import wraps
from api_client import OpenRouterClient

# Тип для обобщенного возвращаемого значения
T = TypeVar('T')

logger = logging.getLogger(__name__)

def with_reconnection(max_retries: int = 3, initial_delay: float = 1.0):
    """
    Декоратор для автоматического переподключения при ошибках API
    
    Args:
        max_retries (int): Максимальное количество попыток
        initial_delay (float): Начальная задержка между попытками (в секундах)
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            retries = 0
            delay = initial_delay
            
            while retries < max_retries:
                try:
                    return await func(self, *args, **kwargs)
                except Exception as e:
                    retries += 1
                    if retries == max_retries:
                        logger.error(f"Failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    logger.warning(f"Attempt {retries} failed: {str(e)}. Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                    delay *= 2  # Экспоненциальная задержка
                    
                    # Пробуем переподключиться
                    await self.reconnect()
            
            return None
        return wrapper
    return decorator

class APIReconnector:
    """
    Класс для управления подключением к API с автоматическим восстановлением
    """
    
    def __init__(self, api_key: str):
        """
        Инициализация менеджера подключений
        
        Args:
            api_key (str): API ключ для OpenRouter
        """
        self.api_key = api_key
        self.client = OpenRouterClient(api_key)
        self._connection_lock = asyncio.Lock()
        self._is_connected = True
    
    async def reconnect(self) -> bool:
        """
        Попытка переподключения к API
        
        Returns:
            bool: Успешность переподключения
        """
        async with self._connection_lock:
            if not self._is_connected:
                logger.info("Attempting to reconnect to API...")
                try:
                    self.client = OpenRouterClient(self.api_key)
                    if await self.client.check_api_key():
                        self._is_connected = True
                        logger.info("Successfully reconnected to API")
                        return True
                    else:
                        logger.error("Failed to validate API key during reconnection")
                        return False
                except Exception as e:
                    logger.error(f"Reconnection failed: {str(e)}")
                    return False
            return True
    
    @with_reconnection(max_retries=3, initial_delay=1.0)
    async def get_learnlm_response(self, message: str) -> Optional[str]:
        """
        Получение ответа от модели LearnLM с автоматическим переподключением
        """
        return await self.client.get_learnlm_response(message)
    
    @with_reconnection(max_retries=3, initial_delay=1.0)
    async def get_gemini_response(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Получение ответа от модели Gemini с автоматическим переподключением
        """
        return await self.client.get_gemini_response(message)
    
    @with_reconnection(max_retries=3, initial_delay=1.0)
    async def get_deepseek_response(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Получение ответа от модели DeepSeek с автоматическим переподключением
        """
        return await self.client.get_deepseek_response(message)