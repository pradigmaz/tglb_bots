from typing import Tuple, Optional, Dict, Any
import re
from logger import logger

class MessageValidator:
    """
    Валидатор сообщений с настраиваемыми правилами
    """
    
    def __init__(self):
        # Базовые ограничения
        self.limits = {
            'text_length': 4096,  # Максимальная длина текста
            'command_length': 32,  # Максимальная длина команды
            'min_length': 2,      # Минимальная длина сообщения
        }
        
        # Паттерны для проверки
        self.patterns = {
            'api_key': r'^sk-[a-zA-Z0-9-]{30,}$',  # Формат API-ключа
            'command': r'^/[a-zA-Z0-9_]+(?:\s+\S+)*$',  # Формат команды с опциональными параметрами
            'special_chars': r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]',  # Спец. символы
        }
        
        # Правила для разных типов сообщений
        self.rules = {
            'default': {
                'max_length': self.limits['text_length'],
                'min_length': self.limits['min_length'],
                'allow_commands': True,
                'allow_special_chars': False,
            },
            'command': {
                'max_length': self.limits['command_length'],
                'min_length': 1,
                'pattern': self.patterns['command'],
            },
            'api_key': {
                'pattern': self.patterns['api_key'],
                'strip': True,
            }
        }
        
        logger.info("Валидатор сообщений инициализирован")
    
    def validate_message(self, text: str, msg_type: str = 'default') -> Tuple[bool, Optional[str]]:
        """
        Проверка сообщения на соответствие правилам
        
        Args:
            text (str): Текст для проверки
            msg_type (str): Тип сообщения ('default', 'command', 'api_key')
            
        Returns:
            Tuple[bool, Optional[str]]: (валидно ли, причина ошибки)
        """
        if not text:
            return False, "Пустое сообщение"
            
        # Получаем правила для типа сообщения
        rules = self.rules.get(msg_type, self.rules['default'])
        
        # Очищаем текст, если нужно
        if rules.get('strip', False):
            text = text.strip()
        
        # Проверяем длину
        if 'max_length' in rules and len(text) > rules['max_length']:
            return False, f"Сообщение слишком длинное (максимум {rules['max_length']} символов)"
            
        if 'min_length' in rules and len(text) < rules['min_length']:
            return False, f"Сообщение слишком короткое (минимум {rules['min_length']} символов)"
        
        # Проверяем паттерн
        if 'pattern' in rules and not re.match(rules['pattern'], text):
            if msg_type == 'command':
                return False, "Неверный формат команды"
            elif msg_type == 'api_key':
                return False, "Неверный формат API-ключа"
            else:
                return False, "Сообщение содержит недопустимые символы"
        
        # Проверяем специальные символы
        if not rules.get('allow_special_chars', True) and re.search(self.patterns['special_chars'], text):
            return False, "Сообщение содержит недопустимые специальные символы"
        
        return True, None
    
    def validate_command(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Проверка команды
        
        Args:
            command (str): Команда для проверки
            
        Returns:
            Tuple[bool, Optional[str]]: (валидно ли, причина ошибки)
        """
        return self.validate_message(command, 'command')
    
    def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """
        Проверка API-ключа
        
        Args:
            api_key (str): API-ключ для проверки
            
        Returns:
            Tuple[bool, Optional[str]]: (валидно ли, причина ошибки)
        """
        return self.validate_message(api_key, 'api_key')
    
    def sanitize_message(self, text: str) -> str:
        """
        Очистка сообщения от недопустимых символов
        
        Args:
            text (str): Текст для очистки
            
        Returns:
            str: Очищенный текст
        """
        # Удаляем специальные символы
        text = re.sub(self.patterns['special_chars'], '', text)
        
        # Обрезаем до максимальной длины
        if len(text) > self.limits['text_length']:
            text = text[:self.limits['text_length']]
        
        return text.strip()

def escape_markdown(text: str) -> str:
    """
    Экранирует специальные символы Markdown для безопасной отправки в Telegram.
    Поддерживает базовый и MarkdownV2 режимы.
    """
    if not text:
        return text
        
    # Специальные символы, которые нужно экранировать
    special_chars = ['_', '*', '`', '[', ']', '(', ')', '~', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    escaped_text = text
    for char in special_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')
        
    return escaped_text

def format_markdown_message(text: str, parse_mode: str = 'MarkdownV2') -> str:
    """
    Форматирует текст для отправки с учетом режима разметки.
    
    Args:
        text: Исходный текст
        parse_mode: Режим разметки ('Markdown' или 'MarkdownV2')
    
    Returns:
        Отформатированный текст, готовый к отправке
    """
    if parse_mode == 'MarkdownV2':
        return escape_markdown(text)
    
    # Для обычного Markdown экранируем только базовые символы
    basic_chars = ['_', '*', '`', '[', ']']
    escaped_text = text
    for char in basic_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')
    
    return escaped_text

# Создаем глобальный экземпляр валидатора
validator = MessageValidator()