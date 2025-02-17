import logging
from datetime import datetime, timedelta
from pathlib import Path
from database import Database

class DatabaseCleaner:
    def __init__(self, db: Database):
        self.db = db
        self.logger = logging.getLogger("DatabaseCleaner")
        self._setup_logging()

    def _setup_logging(self):
        """Настройка логирования для очистки БД"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(log_dir / "db_cleaner.log"),
                logging.StreamHandler()
            ]
        )

    def clean_inactive_users(self, days: int = 180) -> int:
        """
        Очистка неактивных пользователей
        
        Args:
            days (int): Количество дней неактивности
            
        Returns:
            int: Количество удаленных записей
        """
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Получаем список неактивных пользователей
            cursor.execute('''
                SELECT user_id FROM users 
                WHERE last_activity < ? 
                AND api_key IS NULL
            ''', (cutoff_date,))
            
            inactive_users = cursor.fetchall()
            
            if not inactive_users:
                self.logger.info("Неактивных пользователей не найдено")
                return 0
            
            # Удаляем связанные записи
            for user_id in inactive_users:
                # Удаляем нарушения
                cursor.execute('DELETE FROM violations WHERE user_id = ?', user_id)
                # Удаляем отзывы
                cursor.execute('DELETE FROM feedback WHERE user_id = ?', user_id)
                # Удаляем пользователя
                cursor.execute('DELETE FROM users WHERE user_id = ?', user_id)
            
            conn.commit()
            count = len(inactive_users)
            self.logger.info(f"Удалено {count} неактивных пользователей")
            return count
            
        except Exception as e:
            self.logger.error(f"Ошибка при очистке неактивных пользователей: {str(e)}")
            return 0
        finally:
            conn.close()

    def clean_old_violations(self, days: int = 90) -> int:
        """
        Очистка старых нарушений
        
        Args:
            days (int): Возраст нарушений для удаления
            
        Returns:
            int: Количество удаленных записей
        """
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Удаляем старые нарушения
            cursor.execute('''
                DELETE FROM violations 
                WHERE violation_date < ?
            ''', (cutoff_date,))
            
            count = cursor.rowcount
            conn.commit()
            
            self.logger.info(f"Удалено {count} старых нарушений")
            return count
            
        except Exception as e:
            self.logger.error(f"Ошибка при очистке старых нарушений: {str(e)}")
            return 0
        finally:
            conn.close()

    def clean_read_feedback(self, days: int = 30) -> int:
        """
        Очистка прочитанных отзывов
        
        Args:
            days (int): Возраст отзывов для удаления
            
        Returns:
            int: Количество удаленных записей
        """
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            # Удаляем старые прочитанные отзывы
            cursor.execute('''
                DELETE FROM feedback 
                WHERE created_at < ? 
                AND is_read = 1
            ''', (cutoff_date,))
            
            count = cursor.rowcount
            conn.commit()
            
            self.logger.info(f"Удалено {count} старых прочитанных отзывов")
            return count
            
        except Exception as e:
            self.logger.error(f"Ошибка при очистке старых отзывов: {str(e)}")
            return 0
        finally:
            conn.close()

    def clean_all(self) -> dict:
        """
        Запуск всех процедур очистки
        
        Returns:
            dict: Статистика очистки
        """
        stats = {
            "inactive_users": self.clean_inactive_users(),
            "old_violations": self.clean_old_violations(),
            "read_feedback": self.clean_read_feedback()
        }
        
        self.logger.info(f"Очистка БД завершена. Статистика: {stats}")
        return stats


if __name__ == "__main__":
    db = Database()
    cleaner = DatabaseCleaner(db)
    stats = cleaner.clean_all()
    print("Статистика очистки:")
    print(f"- Удалено неактивных пользователей: {stats['inactive_users']}")
    print(f"- Удалено старых нарушений: {stats['old_violations']}")
    print(f"- Удалено прочитанных отзывов: {stats['read_feedback']}") 