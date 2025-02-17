from typing import Optional, List, Union
from aiogram import types
from logger import logger
import re
from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv
from formatting import format_error, safe_format_message

# Загружаем переменные окружения
load_dotenv()

def is_valid_api_key(api_key: str) -> bool:
    """
    Проверка формата API-ключа
    """
    # OpenRouter API-ключи обычно начинаются с 'sk-' и содержат буквы, цифры и дефисы
    return bool(api_key and api_key.startswith('sk-'))

def format_error_message(error: Exception) -> str:
    """
    Форматирование сообщения об ошибке для пользователя
    """
    # Базовые сообщения об ошибках
    error_messages = {
        'InvalidAPIKey': '❌ Неверный API-ключ\nПожалуйста, проверьте ключ и попробуйте снова.',
        'RateLimitError': '⚠️ Превышен лимит запросов\nПожалуйста, подождите немного.',
        'ConnectionError': '🔌 Проблема с подключением к серверу\nПопробуйте позже.',
        'TimeoutError': '⏳ Превышено время ожидания ответа\nПопробуйте позже.',
    }
    
    # Получаем имя класса ошибки
    error_type = error.__class__.__name__
    
    # Возвращаем соответствующее сообщение или общее сообщение об ошибке
    return error_messages.get(
        error_type,
        '❌ Произошла ошибка\nПожалуйста, попробуйте позже или обратитесь к администратору.'
    )

def format_moderation_message(reason: str) -> str:
    """
    Форматирование сообщения о нарушении для пользователя
    """
    base_message = "⚠️ Ваше сообщение не может быть обработано"
    if reason:
        return f"{base_message}\n\nПричина: {reason}"
    return f"{base_message}\n\nПожалуйста, убедитесь, что ваш запрос соответствует правилам."

async def safe_reply(message: types.Message, text: str, parse_mode: Optional[str] = None) -> bool:
    """
    Безопасная отправка сообщения с обработкой ошибок
    
    Args:
        message (types.Message): Сообщение, на которое отвечаем
        text (str): Текст ответа
        parse_mode (Optional[str]): Режим форматирования
        
    Returns:
        bool: True если сообщение отправлено успешно
    """
    try:
        formatted_text = safe_format_message(text) if parse_mode else text
        await message.reply(formatted_text, parse_mode=parse_mode)
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        try:
            # Пробуем отправить без форматирования
            await message.reply(text)
            return True
        except Exception as e:
            logger.error(f"Критическая ошибка при отправке сообщения: {e}")
            return False

def split_long_message(text: str, max_length: int = 3500) -> List[str]:
    """
    Разделение длинного сообщения на части с сохранением форматирования
    """
    if len(text) <= max_length:
        return [text]
        
    parts = []
    current_part = ""
    code_block = False
    
    for line in text.split('\n'):
        # Проверяем начало/конец блока кода
        if line.strip().startswith('```'):
            code_block = not code_block
            
        # Если текущая часть станет слишком длинной
        if len(current_part) + len(line) + 2 > max_length and not code_block:
            parts.append(current_part)
            current_part = line
        else:
            current_part += '\n' + line if current_part else line
            
    if current_part:
        parts.append(current_part)
        
    return parts

def encrypt_api_key(api_key: str) -> Optional[str]:
    """
    Шифрование API-ключа
    
    Args:
        api_key (str): API-ключ для шифрования
        
    Returns:
        Optional[str]: Зашифрованный ключ или None в случае ошибки
    """
    try:
        # Получаем ключ шифрования из переменных окружения
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            logger.error("Отсутствует ключ шифрования в переменных окружения")
            return None
            
        # Создаем объект Fernet с ключом шифрования
        f = Fernet(encryption_key.encode())
        
        # Шифруем API-ключ
        encrypted_key = f.encrypt(api_key.encode())
        return encrypted_key.decode()
    except Exception as e:
        logger.error(f"Ошибка при шифровании API-ключа: {e}")
        return None

def decrypt_api_key(encrypted_key: str) -> Optional[str]:
    """
    Расшифровка API-ключа
    
    Args:
        encrypted_key (str): Зашифрованный API-ключ
        
    Returns:
        Optional[str]: Расшифрованный ключ или None в случае ошибки
    """
    try:
        # Получаем ключ шифрования из переменных окружения
        encryption_key = os.getenv('ENCRYPTION_KEY')
        if not encryption_key:
            logger.error("Отсутствует ключ шифрования в переменных окружения")
            return None
            
        # Создаем объект Fernet с ключом шифрования
        f = Fernet(encryption_key.encode())
        
        # Расшифровываем API-ключ
        decrypted_key = f.decrypt(encrypted_key.encode())
        return decrypted_key.decode()
    except Exception as e:
        logger.error(f"Ошибка при расшифровке API-ключа: {e}")
        return None 

def is_admin(user_id: int) -> bool:
    """
    Проверка, является ли пользователь администратором
    
    Args:
        user_id (int): ID пользователя
        
    Returns:
        bool: True если пользователь администратор, False иначе
    """
    # Получаем список ID администраторов из переменной окружения
    admin_ids_str = os.getenv('ADMIN_IDS', '')
    if not admin_ids_str:
        logger.warning("Список администраторов пуст")
        return False
        
    try:
        # Преобразуем строку с ID в список чисел
        admin_ids = [int(id_str) for id_str in admin_ids_str.split(',')]
        return user_id in admin_ids
    except ValueError:
        logger.error("Некорректный формат списка администраторов")
        return False
