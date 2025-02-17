import sqlite3
import os
from typing import Optional, Tuple, List
from datetime import datetime, timedelta
from logger import logger
from utils import encrypt_api_key, decrypt_api_key

class Database:
    """Класс для работы с базой данных SQLite"""
    
    def __init__(self, db_path: str = "bot.db"):
        self.db_path = db_path
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Получение соединения с базой данных
        
        Returns:
            sqlite3.Connection: Объект соединения с базой данных
        """
        return sqlite3.connect(self.db_path)
    
    def _init_database(self):
        """
        Инициализация базы данных: создание необходимых таблиц
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Создаем таблицу пользователей, если её нет
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    api_key TEXT,
                    is_banned INTEGER DEFAULT 0,
                    ban_reason TEXT,
                    ban_until TEXT,
                    last_activity TEXT,
                    violations_count INTEGER DEFAULT 0,
                    violations_expire_at TEXT
                )
            ''')
            
            # Создаем таблицу нарушений, если её нет
            c.execute('''
                CREATE TABLE IF NOT EXISTS violations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    violation_type TEXT,
                    violation_reason TEXT,
                    violation_date TEXT,
                    message_text TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            ''')
            
            # Проверяем существующую структуру таблицы feedback
            c.execute("PRAGMA table_info(feedback)")
            existing_columns = {column[1] for column in c.fetchall()}
            
            # Если таблицы нет, создаем её
            if not existing_columns:
                logger.info("Создание таблицы feedback...")
                c.execute('''
                    CREATE TABLE feedback (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        feedback_text TEXT,
                        created_at TEXT,
                        is_read INTEGER DEFAULT 0,
                        username TEXT,
                        first_name TEXT,
                        last_name TEXT,
                        FOREIGN KEY (user_id) REFERENCES users(user_id)
                    )
                ''')
            
            conn.commit()
            logger.info("Структура базы данных проверена и обновлена")
            
        except sqlite3.Error as e:
            logger.error(f"Ошибка при инициализации базы данных: {e}")
            raise
        finally:
            conn.close()
    
    def add_user(self, user_id: int, api_key: str) -> bool:
        """
        Добавление нового пользователя или обновление API-ключа
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Шифруем ключ перед сохранением
            encrypted_key = encrypt_api_key(api_key)
            if not encrypted_key:
                logger.error(f"Не удалось зашифровать API-ключ для пользователя {user_id}")
                return False
                
            c.execute(
                'INSERT OR REPLACE INTO users (user_id, api_key) VALUES (?, ?)',
                (user_id, encrypted_key)
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()
    
    def get_user(self, user_id: int) -> Optional[Tuple[str, bool, str]]:
        """
        Получение данных пользователя
        Возвращает кортеж (api_key, is_banned, ban_reason) или None
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute(
                'SELECT api_key, is_banned, ban_reason FROM users WHERE user_id = ?',
                (user_id,)
            )
            result = c.fetchone()
            if not result:
                return None
                
            encrypted_key, is_banned, ban_reason = result
            # Дешифруем ключ перед возвратом
            api_key = decrypt_api_key(encrypted_key) if encrypted_key else None
            return (api_key, bool(is_banned), ban_reason)
        finally:
            conn.close()
    
    def delete_user(self, user_id: int) -> bool:
        """
        Удаление API-ключа пользователя
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute(
                'UPDATE users SET api_key = NULL WHERE user_id = ?',
                (user_id,)
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()
    
    def ban_user(self, user_id: int, reason: str, minutes: int = 2) -> bool:
        """
        Бан пользователя на указанное количество минут
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Вычисляем время окончания бана
            ban_until = (datetime.now() + timedelta(minutes=minutes)).isoformat()
            
            c.execute(
                'UPDATE users SET is_banned = 1, ban_reason = ?, ban_until = ? WHERE user_id = ?',
                (reason, ban_until, user_id)
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()
    
    def unban_user(self, user_id: int) -> bool:
        """
        Разбан пользователя
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute(
                'UPDATE users SET is_banned = 0, ban_reason = NULL WHERE user_id = ?',
                (user_id,)
            )
            conn.commit()
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()
    
    def is_banned(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Проверка бана пользователя с учетом времени
        Возвращает кортеж (is_banned, reason)
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute(
                'SELECT is_banned, ban_reason, ban_until FROM users WHERE user_id = ?',
                (user_id,)
            )
            result = c.fetchone()
            
            if not result:
                return False, None
            
            is_banned, reason, ban_until = result
            
            # Если пользователь забанен и есть время окончания бана
            if is_banned and ban_until:
                ban_until_dt = datetime.fromisoformat(ban_until)
                # Если бан истек
                if datetime.now() > ban_until_dt:
                    # Разбаниваем пользователя
                    c.execute(
                        'UPDATE users SET is_banned = 0, ban_reason = NULL, ban_until = NULL WHERE user_id = ?',
                        (user_id,)
                    )
                    conn.commit()
                    return False, None
                
            return bool(is_banned), reason
        finally:
            conn.close()
    
    def update_last_activity(self, user_id: int) -> bool:
        """
        Обновление времени последней активности пользователя
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            now = datetime.now().isoformat()
            c.execute(
                'UPDATE users SET last_activity = ? WHERE user_id = ?',
                (now, user_id)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении времени активности: {e}")
            return False
        finally:
            conn.close()
    
    def get_last_activity(self, user_id: int) -> Optional[datetime]:
        """
        Получение времени последней активности пользователя
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('SELECT last_activity FROM users WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            if result and result[0]:
                return datetime.fromisoformat(result[0])
            return None
        finally:
            conn.close()
    
    def clear_expired_violations(self, user_id: int) -> bool:
        """
        Очистка устаревших нарушений пользователя
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            now = datetime.now()
            c.execute(
                'SELECT violations_count, violations_expire_at FROM users WHERE user_id = ?',
                (user_id,)
            )
            result = c.fetchone()
            
            if result and result[1]:  # если есть срок истечения нарушений
                expire_at = datetime.fromisoformat(result[1])
                if now > expire_at:  # если срок истек
                    c.execute(
                        'UPDATE users SET violations_count = 0, violations_expire_at = NULL WHERE user_id = ?',
                        (user_id,)
                    )
                    conn.commit()
                    logger.info(f"Нарушения пользователя {user_id} очищены по истечении срока")
                    return True
            return False
        except sqlite3.Error as e:
            logger.error(f"Ошибка при очистке устаревших нарушений: {e}")
            return False
        finally:
            conn.close()
    
    def get_ban_duration(self, violations_count: int) -> int:
        """
        Получение длительности бана в зависимости от количества нарушений
        """
        durations = {
            2: 5,    # 5 минут
            3: 10,   # 10 минут
            4: 30,   # 30 минут
            5: 60    # 60 минут
        }
        return durations.get(violations_count, 0)
    
    def add_violation(self, user_id: int, violation_type: str, reason: str, message: str) -> Tuple[bool, int]:
        """
        Добавление нового нарушения с установкой срока действия
        Возвращает (успех, количество активных нарушений)
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Начинаем транзакцию
            conn.execute("BEGIN")
            
            # Проверяем и очищаем устаревшие нарушения
            self.clear_expired_violations(user_id)
            
            # Добавляем нарушение
            now = datetime.now()
            c.execute(
                'INSERT INTO violations (user_id, violation_type, violation_reason, violation_date, message_text) VALUES (?, ?, ?, ?, ?)',
                (user_id, violation_type, reason, now.isoformat(), message)
            )
            
            # Обновляем счетчик нарушений и устанавливаем срок их действия
            expire_at = (now + timedelta(hours=24)).isoformat()  # нарушения сгорают через 24 часа
            c.execute(
                '''UPDATE users 
                   SET violations_count = COALESCE(violations_count, 0) + 1,
                       last_violation_date = ?,
                       violations_expire_at = ?
                   WHERE user_id = ?''',
                (now.isoformat(), expire_at, user_id)
            )
            
            # Если пользователя нет в таблице users, добавляем его
            if c.rowcount == 0:
                c.execute(
                    '''INSERT INTO users 
                       (user_id, violations_count, last_violation_date, violations_expire_at)
                       VALUES (?, 1, ?, ?)''',
                    (user_id, now.isoformat(), expire_at)
                )
            
            # Получаем обновленное количество нарушений
            c.execute('SELECT violations_count FROM users WHERE user_id = ?', (user_id,))
            violations_count = c.fetchone()[0]
            
            conn.commit()
            logger.info(f"Добавлено нарушение для пользователя {user_id}: {violation_type}")
            return True, violations_count
            
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Ошибка при добавлении нарушения: {e}")
            return False, 0
        finally:
            conn.close()
    
    def get_violations(self, user_id: int) -> List[Tuple[str, str, str, str]]:
        """
        Получение списка нарушений пользователя
        Возвращает список кортежей (тип, причина, дата, текст сообщения)
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute(
                'SELECT violation_type, violation_reason, violation_date, message_text FROM violations WHERE user_id = ? ORDER BY violation_date DESC',
                (user_id,)
            )
            return c.fetchall()
        finally:
            conn.close()
    
    def get_user_violations_count(self, user_id: int) -> int:
        """
        Получение количества нарушений пользователя
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('SELECT violations_count FROM users WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            return result[0] if result else 0
        finally:
            conn.close()
    
    def clear_violations(self, user_id: int) -> bool:
        """
        Очистка истории нарушений пользователя
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('DELETE FROM violations WHERE user_id = ?', (user_id,))
            c.execute('UPDATE users SET violations_count = 0, last_violation_date = NULL WHERE user_id = ?', (user_id,))
            conn.commit()
            logger.info(f"Очищена история нарушений пользователя {user_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при очистке нарушений: {e}")
            return False
        finally:
            conn.close()
    
    def add_feedback(self, user_id: int, feedback_text: str, username: str = None, first_name: str = None, last_name: str = None) -> bool:
        """
        Добавление нового отзыва
        """
        conn = self._get_connection()
        c = conn.cursor()
        
        try:
            now = datetime.now().isoformat()
            c.execute(
                'INSERT INTO feedback (user_id, feedback_text, created_at, username, first_name, last_name) VALUES (?, ?, ?, ?, ?, ?)',
                (user_id, feedback_text, now, username, first_name, last_name)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при добавлении отзыва: {e}")
            return False
        finally:
            conn.close()
    
    def get_feedback(self, filter_type: str = 'all', limit: int = 50, offset: int = 0) -> List[Tuple[int, int, str, str, str, str, str, bool]]:
        """
        Получение отзывов с фильтрацией
        
        Args:
            filter_type (str): Тип фильтрации ('all', 'read', 'unread')
            limit (int): Максимальное количество отзывов
            offset (int): Смещение для пагинации
            
        Returns:
            List[Tuple]: Список кортежей (id, user_id, feedback_text, created_at, username, first_name, last_name, is_read)
        """
        conn = self._get_connection()
        c = conn.cursor()
        
        try:
            query = '''
                SELECT id, user_id, feedback_text, created_at, username, first_name, last_name, is_read 
                FROM feedback
            '''
            
            if filter_type == 'unread':
                query += ' WHERE is_read = 0'
            elif filter_type == 'read':
                query += ' WHERE is_read = 1'
                
            query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
            
            c.execute(query, (limit, offset))
            return c.fetchall()
        finally:
            conn.close()
    
    def get_feedback_count(self, filter_type: str = 'all') -> int:
        """
        Получение количества отзывов определенного типа
        
        Args:
            filter_type (str): Тип фильтрации ('all', 'read', 'unread')
            
        Returns:
            int: Количество отзывов
        """
        conn = self._get_connection()
        c = conn.cursor()
        
        try:
            query = 'SELECT COUNT(*) FROM feedback'
            
            if filter_type == 'unread':
                query += ' WHERE is_read = 0'
            elif filter_type == 'read':
                query += ' WHERE is_read = 1'
                
            c.execute(query)
            return c.fetchone()[0]
        finally:
            conn.close()

    def get_unread_feedback(self) -> List[Tuple[int, int, str, str, str, str, str]]:
        """
        Получение непрочитанных отзывов (для обратной совместимости)
        """
        return [(f[0], f[1], f[2], f[3], f[4], f[5], f[6]) for f in self.get_feedback(filter_type='unread')]
    
    def mark_feedback_as_read(self, feedback_id: int) -> bool:
        """
        Отметить отзыв как прочитанный
        """
        conn = self._get_connection()
        c = conn.cursor()
        
        try:
            c.execute(
                'UPDATE feedback SET is_read = 1 WHERE id = ?',
                (feedback_id,)
            )
            conn.commit()
            return True
        except sqlite3.Error as e:
            logger.error(f"Ошибка при обновлении статуса отзыва: {e}")
            return False
        finally:
            conn.close()

# Создаем глобальный экземпляр базы данных
db = Database() 