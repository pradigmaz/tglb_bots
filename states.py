from aiogram.dispatcher.filters.state import State, StatesGroup

class FeedbackStates(StatesGroup):
    """Состояния для процесса отправки отзыва"""
    waiting_for_feedback = State()  # Ожидание текста отзыва