import os
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path

class LogManager:
    def __init__(self, log_dir="logs", max_age_days=7):
        self.log_dir = Path(log_dir)
        self.max_age_days = max_age_days
        self.logger = logging.getLogger("LogManager")

    def setup_logging(self):
        """Настройка логирования для самого менеджера логов"""
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[
                logging.FileHandler(self.log_dir / "log_manager.log"),
                logging.StreamHandler()
            ]
        )

    def clean_old_logs(self):
        """Очистка старых лог-файлов"""
        try:
            current_time = datetime.now()
            cleaned_count = 0
            total_size_freed = 0

            for log_file in self.log_dir.glob("**/*.log"):
                if log_file.name == "log_manager.log":
                    continue

                file_time = datetime.fromtimestamp(log_file.stat().st_mtime)
                age_days = (current_time - file_time).days

                if age_days > self.max_age_days:
                    file_size = log_file.stat().st_size
                    log_file.unlink()
                    cleaned_count += 1
                    total_size_freed += file_size
                    self.logger.info(f"Удален старый лог: {log_file}")

            self.logger.info(
                f"Очистка завершена: удалено {cleaned_count} файлов, "
                f"освобождено {total_size_freed / 1024 / 1024:.2f} МБ"
            )
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при очистке логов: {str(e)}")
            return False

    def archive_logs(self, archive_dir="logs/archive"):
        """Архивация старых логов"""
        try:
            archive_path = Path(archive_dir)
            archive_path.mkdir(parents=True, exist_ok=True)
            
            current_time = datetime.now()
            archive_date = current_time.strftime("%Y%m%d")
            archive_name = f"logs_archive_{archive_date}.zip"
            
            # Создаем архив
            shutil.make_archive(
                str(archive_path / archive_name.replace('.zip', '')),
                'zip',
                self.log_dir
            )
            
            self.logger.info(f"Логи успешно архивированы: {archive_name}")
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при архивации логов: {str(e)}")
            return False

    def rotate_logs(self):
        """Ротация текущих лог-файлов"""
        try:
            current_time = datetime.now()
            date_suffix = current_time.strftime("%Y%m%d")
            
            for log_file in self.log_dir.glob("*.log"):
                if log_file.stat().st_size > 10 * 1024 * 1024:  # 10MB
                    new_name = f"{log_file.stem}_{date_suffix}{log_file.suffix}"
                    log_file.rename(self.log_dir / new_name)
                    self.logger.info(f"Выполнена ротация файла: {log_file.name} -> {new_name}")
            
            return True

        except Exception as e:
            self.logger.error(f"Ошибка при ротации логов: {str(e)}")
            return False

if __name__ == "__main__":
    log_manager = LogManager()
    log_manager.setup_logging()
    log_manager.clean_old_logs()
    log_manager.rotate_logs()
    log_manager.archive_logs() 