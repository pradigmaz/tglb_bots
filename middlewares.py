from aiogram import types
from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import BaseMiddleware
from typing import Dict, Any
from rate_limiter import RateLimiter
from validators import validator
from utils import is_admin, safe_reply
from logger import logger

class RateLimitMiddleware(BaseMiddleware):
    """
    Middleware для ограничения частоты запросов
    """
    
    def __init__(self):
        super().__init__()
        self.limiter = RateLimiter()
        logger.info("Rate limit middleware инициализирован")
    
    async def on_pre_process_message(self, message: types.Message, data: Dict[str, Any]):
        """
        Проверка ограничений перед обработкой сообщения
        
        Args:
            message (types.Message): Сообщение
            data (Dict[str, Any]): Данные обработчика
        """
        user_id = message.from_user.id
        
        # Определяем тип пользователя
        user_type = 'admin' if is_admin(user_id) else 'default'
        
        # Проверяем лимиты
        allowed, time_to_reset = self.limiter.check_limit(user_id, user_type)
        
        if not allowed:
            # Если лимит превышен
            violations_count = self.limiter.add_violation(user_id)
            
            # Формируем сообщение об ошибке
            if time_to_reset:
                minutes = int(time_to_reset // 60)
                seconds = int(time_to_reset % 60)
                time_str = f"{minutes}м {seconds}с" if minutes > 0 else f"{seconds}с"
                
                warning_message = (
                    f"⚠️ *Слишком много сообщений*\n\n"
                    f"Пожалуйста, подождите {time_str} перед отправкой "
                    f"следующего сообщения.\n\n"
                    f"❗️ Нарушение #{violations_count}"
                )
            else:
                warning_message = (
                    "⚠️ *Превышен лимит сообщений*\n\n"
                    "Пожалуйста, подождите немного перед "
                    "отправкой следующего сообщения."
                )
            
            # Отправляем предупреждение
            await safe_reply(message, warning_message)
            
            # Отменяем обработку сообщения
            raise CancelHandler()
        
        # Если всё в порядке, добавляем запрос
        self.limiter.add_request(user_id)
    
    async def on_post_process_message(self, message: types.Message, data: Dict[str, Any], *args: Any):
        """
        Действия после обработки сообщения
        
        Args:
            message (types.Message): Сообщение
            data (Dict[str, Any]): Данные обработчика
        """
        # Можно добавить дополнительную логику после обработки сообщения
        pass

class ValidationMiddleware(BaseMiddleware):
    """
    Middleware для валидации входящих сообщений
    """
    
    def __init__(self):
        super().__init__()
        logger.info("Validation middleware инициализирован")
    
    async def on_pre_process_message(self, message: types.Message, data: Dict[str, Any]):
        """
        Валидация сообщения перед обработкой
        
        Args:
            message (types.Message): Сообщение
            data (Dict[str, Any]): Данные обработчика
        """
        if not message.text:
            return
            
        # Определяем тип сообщения
        msg_type = 'command' if message.text.startswith('/') else 'default'
        if message.text.startswith('sk-'):
            msg_type = 'api_key'
        
        # Проверяем сообщение
        is_valid, error_reason = validator.validate_message(message.text, msg_type)
        
        if not is_valid:
            # Формируем сообщение об ошибке
            error_message = (
                f"⚠️ *Ошибка валидации*\n\n"
                f"{error_reason}\n\n"
                "Пожалуйста, проверьте ваше сообщение и попробуйте снова."
            )
            
            # Логируем ошибку
            logger.warning(
                f"Ошибка валидации для пользователя {message.from_user.id}: "
                f"{error_reason} (тип: {msg_type})"
            )
            
            # Отправляем сообщение об ошибке
            await safe_reply(message, error_message)
            
            # Отменяем обработку сообщения
            raise CancelHandler()
        
        # Если сообщение прошло валидацию, очищаем его
        if msg_type == 'default':
            message.text = validator.sanitize_message(message.text)
    
    async def on_post_process_message(self, message: types.Message, data: Dict[str, Any], *args: Any):
        """
        Действия после обработки сообщения
        
        Args:
            message (types.Message): Сообщение
            data (Dict[str, Any]): Данные обработчика
        """
        pass 