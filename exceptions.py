class ApiError(Exception):
    """Базовое исключение для ошибок API"""
    pass

class ValidationError(Exception):
    """Исключение для ошибок валидации"""
    pass

class RateLimitError(Exception):
    """Исключение для ошибок превышения лимита запросов"""
    def __init__(self, wait_time: int):
        self.wait_time = wait_time
        super().__init__(f"Rate limit exceeded. Wait {wait_time} seconds.")