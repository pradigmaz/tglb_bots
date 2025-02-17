import schedule
import time
import logging
from pathlib import Path
from log_manager import LogManager
from db_cleaner import DatabaseCleaner
from database import Database

class TaskScheduler:
    def __init__(self):
        self.log_manager = LogManager()
        self.db = Database()
        self.db_cleaner = DatabaseCleaner(self.db)
        self.logger = logging.getLogger("TaskScheduler")
        self._setup_logging()

    def _setup_logging(self):
        """Настройка логирования для планировщика"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(log_dir / "scheduler.log"),
                logging.StreamHandler()
            ]
        )

    def schedule_log_maintenance(self):
        """Планирование задач обслуживания логов"""
        # Ежедневная ротация логов в полночь
        schedule.every().day.at("00:00").do(self.log_manager.rotate_logs)
        
        # Еженедельная очистка старых логов в воскресенье
        schedule.every().sunday.at("01:00").do(self.log_manager.clean_old_logs)
        
        # Ежемесячная архивация логов
        schedule.every().month.at("02:00").do(self.log_manager.archive_logs)
        
        self.logger.info("Задачи обслуживания логов запланированы")

    def schedule_db_maintenance(self):
        """Планирование задач обслуживания БД"""
        # Еженедельная очистка БД в воскресенье
        schedule.every().sunday.at("03:00").do(self.db_cleaner.clean_all)
        
        self.logger.info("Задачи обслуживания БД запланированы")

    def run(self):
        """Запуск планировщика"""
        self.schedule_log_maintenance()
        self.schedule_db_maintenance()
        
        while True:
            try:
                schedule.run_pending()
                time.sleep(60)
            except Exception as e:
                self.logger.error(f"Ошибка в планировщике: {str(e)}")
                time.sleep(300)  # Пауза 5 минут при ошибке

if __name__ == "__main__":
    scheduler = TaskScheduler()
    scheduler.run() 