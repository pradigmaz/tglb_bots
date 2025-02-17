from typing import Optional, Dict, Any, List, Tuple
import re
from api_client import OpenRouterClient
from api_reconnector import APIReconnector
from logger import logger, log_moderation_details
from moderation_rules import moderation_rules

class Moderator:
    """Класс для модерации сообщений"""
    
    def __init__(self):
        """
        Инициализация модератора
        """
        # Триггеры для активации AI-модерации
        self.triggers = [
            # Длинные сообщения
            lambda msg: len(msg) > 500,
            # Капс
            lambda msg: sum(1 for c in msg if c.isupper()) / len(msg) > 0.5 if msg else False,
            # Повторяющиеся сообщения (будет дополнено)
            lambda msg: False  # Заглушка
        ]
        
        # Счетчики для отслеживания переключений между моделями
        self.gemini_failures = 0
        self.deepseek_failures = 0
        self.max_failures = 3  # После 3 неудач переключаемся
    
    def check_word_combinations(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        Проверка комбинаций стоп-слов в сообщении
        """
        is_violation, combo_info = moderation_rules.check_combination(message)
        if is_violation:
            words = combo_info['words']
            category = combo_info['category']
            severity = combo_info['severity']
            reason = f"Обнаружена запрещенная комбинация слов: '{words[0]}' + '{words[1]}' (категория: {category}, важность: {severity})"
            logger.info(f"{reason} в сообщении: {message[:100]}")
            return True, reason
        return False, None

    def check_partial_matches(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        Проверка частичных совпадений со стоп-словами
        """
        message_lower = message.lower()
        words = message_lower.split()
        
        for word in words:
            is_violation, category = moderation_rules.check_word(word)
            if is_violation:
                reason = f"Обнаружено запрещенное слово: '{word}' (категория: {category})"
                logger.info(f"{reason} в сообщении: {message[:100]}")
                return True, reason
        return False, None

    def check_triggers(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        Проверка наличия триггеров в сообщении
        """
        # Проверка комбинаций слов
        is_violation, reason = self.check_word_combinations(message)
        if is_violation:
            return True, reason
            
        # Проверка частичных совпадений
        is_violation, reason = self.check_partial_matches(message)
        if is_violation:
            return True, reason
            
        # Проверка спам-паттернов
        for pattern_info in moderation_rules.get_spam_patterns():
            pattern = pattern_info['pattern']
            description = pattern_info['description']
            if match := re.search(pattern, message):
                reason = f"Обнаружен спам-паттерн: {description} - найдено: {match.group()}"
                logger.info(f"{reason} в сообщении: {message[:100]}")
                return True, reason
        
        # Проверка триггеров
        for i, trigger in enumerate(self.triggers):
            if trigger(message):
                trigger_type = "длинное сообщение" if i == 0 else "капс" if i == 1 else "повторяющееся сообщение"
                reason = f"Сработал триггер модерации: {trigger_type}"
                logger.info(f"{reason} в сообщении: {message[:100]}")
                return True, reason
        
        logger.info(f"Сообщение прошло все проверки триггеров: {message[:100]}")
        return False, None
    
    async def moderate_with_ai(self, message: str, api_client: APIReconnector) -> Tuple[bool, Optional[str]]:
        """
        Модерация с использованием AI моделей
        Возвращает кортеж (is_violation, reason)
        """
        # Сначала пробуем Gemini
        if self.gemini_failures < self.max_failures:
            logger.info(f"Отправка на модерацию Gemini: {message[:100]}")
            result = await api_client.get_gemini_response(message)
            if result is not None:
                self.gemini_failures = 0  # Сбрасываем счетчик при успехе
                log_moderation_details(0, "Gemini", "AI Moderation", message, result)
                return result.get('is_violation', False), result.get('reason')
            self.gemini_failures += 1
            logger.warning(f"Ошибка Gemini (попытка {self.gemini_failures}) для сообщения: {message[:100]}")
        
        # Если Gemini не доступен, пробуем DeepSeek
        if self.deepseek_failures < self.max_failures:
            logger.info(f"Отправка на модерацию DeepSeek: {message[:100]}")
            result = await api_client.get_deepseek_response(message)
            if result is not None:
                self.deepseek_failures = 0  # Сбрасываем счетчик при успехе
                log_moderation_details(0, "DeepSeek", "AI Moderation", message, result)
                return result.get('is_violation', False), result.get('reason')
            self.deepseek_failures += 1
            logger.warning(f"Ошибка DeepSeek (попытка {self.deepseek_failures}) для сообщения: {message[:100]}")
        
        # Если обе модели недоступны
        logger.error(f"Обе модели модерации недоступны для сообщения: {message[:100]}")
        return False, None
    
    async def moderate_message(self, message: str, api_client: APIReconnector) -> Tuple[bool, Optional[str]]:
        """
        Полная модерация сообщения
        """
        # Сначала проверяем локальные триггеры
        is_violation, reason = self.check_triggers(message)
        if is_violation:
            logger.info(f"Сработали локальные триггеры: {reason}")
            # Дополнительная проверка через AI
            ai_violation, ai_reason = await self.moderate_with_ai(message, api_client)
            if ai_violation:
                final_reason = f"Локальная причина: {reason}. AI причина: {ai_reason}"
            else:
                final_reason = reason
            return True, final_reason
        
        logger.info("Сообщение прошло локальную проверку")
        return False, None 