from aiogram.utils.markdown import text, bold, italic, code, pre
from aiogram.utils.exceptions import CantParseEntities
from typing import Optional, Union, List
from logger import logger

def escape_markdown(text: str) -> str:
    """
    Экранирование специальных символов для Markdown V2
    """
    chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars:
        text = text.replace(char, f"\\{char}")
    return text

def format_message(message: str) -> str:
    """
    Форматирует сообщение используя утилиты aiogram
    
    Args:
        message (str): Исходный текст сообщения
        
    Returns:
        str: Отформатированный текст
    """
    if not message:
        return message
    
    try:
        # Разбиваем сообщение на части, сохраняя блоки кода
        parts = []
        current_text = ""
        in_code_block = False
        code_block_content = ""
        code_language = "python"  # По умолчанию Python
        
        for line in message.split('\n'):
            # Проверяем начало блока кода
            if line.strip().startswith('```'):
                if not in_code_block:
                    # Начало блока кода
                    if current_text:
                        parts.append(('text', current_text))
                        current_text = ""
                    in_code_block = True
                    # Получаем язык программирования
                    lang_spec = line.strip()[3:].strip()
                    if lang_spec:
                        code_language = lang_spec
                    continue
                else:
                    # Конец блока кода
                    in_code_block = False
                    if code_block_content:
                        parts.append(('code', code_block_content.strip(), code_language))
                    code_block_content = ""
                    code_language = "python"
                    continue
            
            if in_code_block:
                code_block_content += line + '\n'
            else:
                current_text += line + '\n'
        
        # Добавляем оставшийся текст
        if current_text:
            parts.append(('text', current_text))
        
        # Форматируем каждую часть
        formatted_parts = []
        for part_type, *content in parts:
            if part_type == 'text':
                text_content = content[0]
                # Экранируем специальные символы
                text_content = escape_markdown(text_content)
                # Обрабатываем маркированные списки
                lines = text_content.split('\n')
                formatted_lines = []
                for line in lines:
                    if line.strip().startswith('•') or line.strip().startswith('*'):
                        # Это элемент списка
                        formatted_lines.append(line.replace('*', '•', 1))
                    else:
                        formatted_lines.append(line)
                formatted_parts.append('\n'.join(formatted_lines))
            elif part_type == 'code':
                code_content, language = content
                formatted_parts.append(pre(code_content, language=language))
        
        # Объединяем все части
        return text(*formatted_parts)
    except Exception as e:
        logger.error(f"Ошибка при форматировании сообщения: {str(e)}")
        return message

def format_code(code: str, language: str = "python") -> str:
    """
    Форматирует блок кода с подсветкой синтаксиса
    
    Args:
        code (str): Исходный код
        language (str): Язык программирования
        
    Returns:
        str: Отформатированный блок кода
    """
    if not code:
        return code
        
    try:
        # Очищаем код от лишних пробелов
        code = code.strip()
        return pre(code, language=language)
    except Exception as e:
        logger.error(f"Ошибка при форматировании кода: {str(e)}")
        return code

def format_error(error_text: str, recommendation: Optional[str] = None) -> str:
    """
    Форматирует сообщение об ошибке
    
    Args:
        error_text (str): Текст ошибки
        recommendation (str, optional): Рекомендация по исправлению
        
    Returns:
        str: Отформатированное сообщение об ошибке
    """
    try:
        parts = [
            bold("❌ Ошибка"),
            "",
            error_text
        ]
        
        if recommendation:
            parts.extend([
                "",
                italic("💡 " + recommendation)
            ])
            
        return text(*parts)
    except Exception as e:
        logger.error(f"Ошибка при форматировании сообщения об ошибке: {str(e)}")
        return f"❌ Ошибка: {error_text}"

def format_section(title: str, *content: str) -> str:
    """
    Форматирует секцию с заголовком и содержимым
    
    Args:
        title (str): Заголовок секции
        *content (str): Строки содержимого
        
    Returns:
        str: Отформатированная секция
    """
    try:
        return text(
            bold(title),
            "",
            *content
        )
    except Exception as e:
        logger.error(f"Ошибка при форматировании секции: {str(e)}")
        return f"{title}\n\n{text(*content)}"

def format_list(items: List[str], marker: str = "•") -> str:
    """
    Форматирует список элементов
    
    Args:
        items (List[str]): Элементы списка
        marker (str): Маркер списка
        
    Returns:
        str: Отформатированный список
    """
    try:
        # Экранируем специальные символы в каждом элементе списка
        formatted_items = [f"{marker} {escape_markdown(item)}" for item in items]
        return text(*formatted_items)
    except Exception as e:
        logger.error(f"Ошибка при форматировании списка: {str(e)}")
        return "\n".join(f"{marker} {item}" for item in items)

def safe_format_message(message: Union[str, Exception]) -> str:
    """
    Безопасное форматирование сообщения с обработкой ошибок
    
    Args:
        message (Union[str, Exception]): Сообщение или объект ошибки
        
    Returns:
        str: Отформатированное сообщение
    """
    try:
        if isinstance(message, Exception):
            return format_error(str(message))
        return format_message(str(message))
    except CantParseEntities:
        # Если не удалось отформатировать, возвращаем без форматирования
        return str(message)
    except Exception as e:
        logger.error(f"Ошибка при безопасном форматировании: {str(e)}")
        return str(message) 