import sqlite3
from logger import logger

def migrate():
    """
    Создает таблицу архива пользователей и добавляет необходимые индексы
    """
    try:
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        # Создаем таблицу архива пользователей
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users_archive (
                user_id INTEGER PRIMARY KEY,
                api_key TEXT,
                is_banned INTEGER DEFAULT 0,
                ban_reason TEXT,
                ban_until TEXT,
                last_activity TEXT,
                violations_count INTEGER DEFAULT 0,
                violations_expire_at TEXT,
                archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Добавляем индекс для поиска по дате архивации
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_users_archive_date 
            ON users_archive(archived_at)
        ''')
        
        conn.commit()
        logger.info("Миграция успешно выполнена")
        
    except sqlite3.Error as e:
        logger.error(f"Ошибка при выполнении миграции: {str(e)}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate() 