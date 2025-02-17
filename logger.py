from rich.console import Console
from rich.logging import RichHandler
import logging
from datetime import datetime
import os
import sys
from typing import Optional
import locale

# Устанавливаем локаль для корректной работы с кириллицей
try:
    locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'Russian_Russia.1251')
    except locale.Error:
        print("Внимание: Не удалось установить русскую локаль")

# Создаем директорию для логов, если её нет
try:
    os.makedirs("logs", exist_ok=True)
    print("Директория logs создана или уже существует")
except Exception as e:
    print(f"Ошибка при создании директории logs: {e}")
    sys.exit(1)

# Настраиваем логгер
console = Console(force_terminal=True)

# Создаем форматтер для файла с явным указанием кодировки
file_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "%Y-%m-%d %H:%M:%S"
)

# Создаем обработчик для файла с явным указанием кодировки UTF-8
try:
    log_file = f"logs/bot_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(file_formatter)
    print(f"Файл лога создан: {log_file}")
except Exception as e:
    print(f"Ошибка при создании файла лога: {e}")
    sys.exit(1)

# Создаем обработчик для консоли с поддержкой Unicode
console_handler = RichHandler(
    console=console,
    rich_tracebacks=True,
    tracebacks_show_locals=True
)

# Настраиваем корневой логгер
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[console_handler, file_handler]
)

logger = logging.getLogger("bot_logger")
logger.info("Логгер инициализирован")

def log_user_action(user_id: int, action: str, details: str = None):
    """
    Логирование действий пользователя
    """
    message = f"User {user_id}: {action}"
    if details:
        message += f" - {details}"
    logger.info(message)

def log_error(error: Exception, context: str = None):
    """
    Логирование ошибок
    """
    message = f"Error: {str(error)}"
    if context:
        message = f"{context} - {message}"
    logger.error(message, exc_info=True)

def log_admin_action(admin_id: int, action: str, target_id: int = None):
    """
    Логирование действий администратора
    """
    message = f"Admin {admin_id}: {action}"
    if target_id:
        message += f" (target: {target_id})"
    logger.info(message)

def log_moderation(user_id: int, message: str, result: bool, reason: str = None):
    """
    Логирование результатов модерации
    """
    status = "BLOCKED" if result else "PASSED"
    log_message = f"Moderation {status} - User {user_id}: {message[:100]}"
    if reason:
        log_message += f" - Reason: {reason}"
    logger.info(log_message)

def log_moderation_details(user_id: int, model_name: str, check_type: str, content: str, result: dict):
    """
    Логирование деталей проверки модерации
    """
    log_message = f"Moderation Check - User {user_id} - Model: {model_name} - Type: {check_type}\n"
    log_message += f"Content checked: {content[:200]}...\n"
    log_message += f"Model response: {result}"
    logger.info(log_message)

def log_moderation_model(model_name: str, success: bool, error: Optional[str] = None):
    """
    Логирование работы моделей модерации
    """
    if success:
        logger.info(f"Модель {model_name} успешно обработала запрос")
    else:
        logger.warning(f"Ошибка модели {model_name}: {error if error else 'неизвестная ошибка'}")

def log_violation(user_id: int, violation_type: str, message: str, details: str = None):
    """
    Логирование нарушений
    """
    log_message = f"Violation by User {user_id} - Type: {violation_type} - Message: {message[:100]}"
    if details:
        log_message += f" - Details: {details}"
    logger.warning(log_message)

def log_ban(user_id: int, reason: str, admin_id: Optional[int] = None):
    """
    Логирование банов пользователей
    """
    log_message = f"User {user_id} banned - Reason: {reason}"
    if admin_id:
        log_message += f" - By Admin: {admin_id}"
    logger.warning(log_message) 