import sqlite3
import functools
from typing import Any, Callable
from logger import logger

def transaction(func: Callable) -> Callable:
    """
    Декоратор для выполнения функции внутри транзакции
    
    Args:
        func (Callable): Функция для выполнения в транзакции
        
    Returns:
        Callable: Обёрнутая функция
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Получаем соединение из первого аргумента (self)
        if not args or not hasattr(args[0], '_get_connection'):
            raise ValueError("Первым аргументом должен быть экземпляр Database")
        
        conn = args[0]._get_connection()
        try:
            # Начинаем транзакцию
            conn.execute('BEGIN TRANSACTION')
            
            # Выполняем функцию
            result = func(*args, **kwargs)
            
            # Фиксируем изменения
            conn.commit()
            return result
            
        except Exception as e:
            # В случае ошибки откатываем изменения
            conn.rollback()
            logger.error(f"Ошибка в транзакции {func.__name__}: {str(e)}")
            raise
        finally:
            conn.close()
    
    return wrapper

def add_indexes(conn: sqlite3.Connection) -> None:
    """
    Добавляет необходимые индексы в базу данных
    
    Args:
        conn (sqlite3.Connection): Соединение с базой данных
    """
    try:
        # Индекс для поиска по user_id в таблице users
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_user_id 
            ON users(user_id)
        ''')
        
        # Индекс для поиска по времени последней активности
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_last_activity 
            ON users(last_activity)
        ''')
        
        # Индекс для поиска забаненных пользователей
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_banned 
            ON users(is_banned, ban_until)
        ''')
        
        # Составной индекс для поиска нарушений пользователя
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_violations_user_date 
            ON violations(user_id, violation_date)
        ''')
        
        # Индекс для поиска отзывов по статусу
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_feedback_status 
            ON feedback(is_read)
        ''')
        
        conn.commit()
        logger.info("Индексы успешно добавлены")
        
    except sqlite3.Error as e:
        logger.error(f"Ошибка при создании индексов: {str(e)}")
        conn.rollback()
        raise

def optimize_database(conn: sqlite3.Connection) -> None:
    """
    Оптимизирует базу данных
    
    Args:
        conn (sqlite3.Connection): Соединение с базой данных
    """
    try:
        # Анализ индексов
        conn.execute('ANALYZE')
        
        # Очистка неиспользуемого пространства
        conn.execute('VACUUM')
        
        # Оптимизация индексов
        conn.execute('REINDEX')
        
        conn.commit()
        logger.info("База данных оптимизирована")
        
    except sqlite3.Error as e:
        logger.error(f"Ошибка при оптимизации базы данных: {str(e)}")
        raise

def cleanup_old_data(conn: sqlite3.Connection, days: int = 30) -> None:
    """
    Очищает устаревшие данные из базы
    
    Args:
        conn (sqlite3.Connection): Соединение с базой данных
        days (int): Количество дней, после которых данные считаются устаревшими
    """
    try:
        conn.execute('BEGIN TRANSACTION')
        
        # Удаляем старые логи нарушений
        conn.execute('''
            DELETE FROM violations 
            WHERE violation_date < datetime('now', ?)
        ''', (f'-{days} days',))
        
        # Удаляем прочитанные отзывы
        conn.execute('''
            DELETE FROM feedback 
            WHERE is_read = 1 
            AND created_at < datetime('now', ?)
        ''', (f'-{days} days',))
        
        # Архивируем неактивных пользователей
        conn.execute('''
            INSERT INTO users_archive 
            SELECT * FROM users 
            WHERE last_activity < datetime('now', ?)
        ''', (f'-{days} days',))
        
        conn.execute('''
            DELETE FROM users 
            WHERE last_activity < datetime('now', ?)
        ''', (f'-{days} days',))
        
        conn.commit()
        logger.info(f"Очищены данные старше {days} дней")
        
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Ошибка при очистке устаревших данных: {str(e)}")
        raise 