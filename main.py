import os
import sys
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from handlers import register_handlers
from logger import logger
from middlewares import RateLimitMiddleware, ValidationMiddleware

try:
    print("Запуск бота...")
    
    # Загружаем переменные окружения
    load_dotenv()
    print("Переменные окружения загружены")
    
    # Проверяем наличие токена
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        print("Не найден BOT_TOKEN в переменных окружения")
        sys.exit(1)
    print("BOT_TOKEN получен")
    
    # Инициализируем бота и диспетчер
    try:
        bot = Bot(token=bot_token)
        storage = MemoryStorage()  # Хранилище для FSM
        dp = Dispatcher(bot, storage=storage)
        print("Бот и диспетчер инициализированы")
        
        # Подключаем middleware
        dp.middleware.setup(RateLimitMiddleware())
        dp.middleware.setup(ValidationMiddleware())
        print("Middleware подключены")
        
    except Exception as e:
        print(f"Ошибка при инициализации бота: {e}")
        sys.exit(1)
    
    # Регистрируем обработчики
    try:
        register_handlers(dp)
        print("Обработчики зарегистрированы")
    except Exception as e:
        print(f"Ошибка при регистрации обработчиков: {e}")
        sys.exit(1)
    
    if __name__ == '__main__':
        print("Запуск поллинга...")
        try:
            executor.start_polling(dp, skip_updates=True)
        except Exception as e:
            print(f"Ошибка при запуске поллинга: {e}")
            sys.exit(1)
except Exception as e:
    print(f"Критическая ошибка: {e}")
    sys.exit(1)
