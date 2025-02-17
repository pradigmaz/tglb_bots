"""
Инициализация пакета
"""
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from formatting import format_message, format_error, safe_format_message
from database import Database
from api_client import OpenRouterClient
from moderator import Moderator
from cache import Cache
from hints import HintSystem
from states import FeedbackStates

# Инициализация компонентов
storage = MemoryStorage()
db = Database()
cache = Cache()
hint_system = HintSystem()

# Создаем экземпляр бота
bot = Bot(token='YOUR_BOT_TOKEN')
dp = Dispatcher(bot, storage=storage)

# Инициализируем API клиент
api_client = OpenRouterClient()

# Инициализируем модератора
moderator = Moderator()