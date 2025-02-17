from openai import OpenAI
import requests
from typing import Optional, Dict, Any
import json

class OpenRouterClient:
    """Клиент для работы с OpenRouter API"""
    
    BASE_URL = "https://openrouter.ai/api/v1"
    
    def __init__(self, api_key: str):
        """
        Инициализация клиента OpenRouter
        """
        self.client = OpenAI(
            base_url=self.BASE_URL,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/your-username/your-repo",
                "X-Title": "Teacher Bot"
            }
        )
    
    async def check_api_key(self) -> bool:
        """
        Проверка валидности API-ключа
        """
        try:
            # Пробуем сделать тестовый запрос
            completion = self.client.chat.completions.create(
                model="google/learnlm-1.5-pro-experimental:free",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return True
        except Exception as e:
            print(f"Error checking API key: {e}")  # Для отладки
            return False
    
    async def get_learnlm_response(self, message: str) -> Optional[str]:
        """
        Получение ответа от модели LearnLM
        """
        try:
            completion = self.client.chat.completions.create(
                model="google/learnlm-1.5-pro-experimental:free",
                messages=[
                    {
                        "role": "system",
                        "content": """Ты - опытный и внимательный учитель, который помогает студентам разобраться в материале. 

Твои основные характеристики:
1. Педагогический подход:
   - Объясняешь сложные темы простым и понятным языком
   - Используешь аналогии и примеры из реальной жизни
   - Разбиваешь сложные концепции на простые составляющие
   - Проверяешь понимание материала через наводящие вопросы

2. Стиль общения:
   - Доброжелательный и терпеливый
   - Поддерживающий и мотивирующий
   - Профессиональный, но не сухой
   - Используешь понятную терминологию

3. Принципы работы:
   - Помогаешь понять материал, но не делаешь работу за студента
   - Направляешь к правильному решению через подсказки
   - Поощряешь самостоятельное мышление
   - Указываешь на ошибки конструктивно, без критики

4. Методика обучения:
   - Начинаешь с базовых концепций
   - Постепенно усложняешь материал
   - Связываешь новые знания с уже известными
   - Даёшь практические советы по применению знаний

Важно: ты не должен:
- Решать задачи за студентов
- Давать готовые ответы без объяснений
- Поощрять списывание
- Использовать сложный технический жаргон без необходимости"""
                    },
                    {"role": "user", "content": message}
                ]
            )
            return completion.choices[0].message.content
        except Exception as e:
            print(f"Error getting LearnLM response: {e}")  # Для отладки
            return None
    
    async def get_gemini_response(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Получение ответа от модели Gemini (модерация)
        """
        try:
            completion = self.client.chat.completions.create(
                model="google/gemini-2.0-flash-thinking-exp:free",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты - модератор, который проверяет сообщения на наличие нарушений. "
                                 "Проверь следующее сообщение и верни JSON с полями:\n"
                                 "- is_violation (bool): есть ли нарушение\n"
                                 "- reason (str): причина нарушения, если есть\n"
                                 "Нарушениями считаются: ненормативная лексика, оскорбления, спам, "
                                 "попытки получить готовое решение задачи."
                    },
                    {"role": "user", "content": message}
                ]
            )
            try:
                result = json.loads(completion.choices[0].message.content)
                return result
            except json.JSONDecodeError:
                return {"is_violation": False, "reason": None}
        except Exception:
            return None
    
    async def get_deepseek_response(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Получение ответа от модели DeepSeek (резервная модерация)
        """
        try:
            completion = self.client.chat.completions.create(
                model="deepseek/deepseek-r1-distill-llama-70b:free",
                messages=[
                    {
                        "role": "system",
                        "content": "Ты - модератор, который проверяет сообщения на наличие нарушений. "
                                 "Проверь следующее сообщение и верни JSON с полями:\n"
                                 "- is_violation (bool): есть ли нарушение\n"
                                 "- reason (str): причина нарушения, если есть\n"
                                 "Нарушениями считаются: ненормативная лексика, оскорбления, спам, "
                                 "попытки получить готовое решение задачи."
                    },
                    {"role": "user", "content": message}
                ]
            )
            try:
                result = json.loads(completion.choices[0].message.content)
                return result
            except json.JSONDecodeError:
                return {"is_violation": False, "reason": None}
        except Exception:
            return None