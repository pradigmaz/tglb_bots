import json
import os
from typing import Dict, List, Set, Tuple, Optional
from logger import logger

class ModerationRules:
    """Класс для управления правилами модерации"""
    
    def __init__(self, rules_file: str = "moderation_rules.json"):
        """
        Инициализация правил модерации
        
        Args:
            rules_file (str): Путь к файлу с правилами
        """
        self.rules_file = rules_file
        self.rules = self._load_rules()
        self._init_stop_words()
        
    def _load_rules(self) -> Dict:
        """Загрузка правил из файла"""
        try:
            if not os.path.exists(self.rules_file):
                logger.warning(f"Файл правил {self.rules_file} не найден")
                return {}
                
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                rules = json.load(f)
            logger.info(f"Правила модерации загружены из {self.rules_file}")
            return rules
        except Exception as e:
            logger.error(f"Ошибка при загрузке правил: {e}")
            return {}
            
    def _init_stop_words(self):
        """Инициализация множеств стоп-слов"""
        self.all_stop_words = set()
        for category, data in self.rules.get('stop_words', {}).items():
            words = set(data['words'])
            setattr(self, f"{category}_words", words)
            self.all_stop_words.update(words)
            
    def check_word(self, word: str) -> Tuple[bool, Optional[str]]:
        """
        Проверка слова на наличие в стоп-словах
        
        Args:
            word (str): Проверяемое слово
            
        Returns:
            Tuple[bool, Optional[str]]: (Найдено ли нарушение, категория)
        """
        word = word.lower()
        for category, data in self.rules.get('stop_words', {}).items():
            for stop_word in data['words']:
                if (stop_word in word or word in stop_word) and len(word) > 3:
                    return True, category
        return False, None
        
    def check_combination(self, message: str) -> Tuple[bool, Optional[Dict]]:
        """
        Проверка комбинаций стоп-слов в сообщении
        
        Args:
            message (str): Проверяемое сообщение
            
        Returns:
            Tuple[bool, Optional[Dict]]: (Найдено ли нарушение, информация о комбинации)
        """
        message = message.lower()
        for combo in self.rules.get('word_combinations', []):
            word1, word2 = combo['words']
            if word1 in message and word2 in message:
                return True, combo
        return False, None
        
    def get_spam_patterns(self) -> List[Dict]:
        """
        Получение списка спам-паттернов
        
        Returns:
            List[Dict]: Список паттернов с описаниями
        """
        return self.rules.get('spam_patterns', [])
        
    def save_rules(self):
        """Сохранение правил в файл"""
        try:
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=4)
            logger.info(f"Правила модерации сохранены в {self.rules_file}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении правил: {e}")
            
    def add_stop_word(self, word: str, category: str, severity: str = "medium"):
        """
        Добавление нового стоп-слова
        
        Args:
            word (str): Новое стоп-слово
            category (str): Категория слова
            severity (str): Важность (low/medium/high/critical)
        """
        if category not in self.rules.get('stop_words', {}):
            self.rules['stop_words'][category] = {
                'words': [],
                'severity': severity,
                'description': f"Категория {category}"
            }
        
        if word not in self.rules['stop_words'][category]['words']:
            self.rules['stop_words'][category]['words'].append(word)
            self._init_stop_words()
            self.save_rules()
            logger.info(f"Добавлено новое стоп-слово: {word} (категория: {category})")
            
    def add_word_combination(self, word1: str, word2: str, category: str, severity: str = "medium"):
        """
        Добавление новой комбинации стоп-слов
        
        Args:
            word1 (str): Первое слово
            word2 (str): Второе слово
            category (str): Категория комбинации
            severity (str): Важность (low/medium/high/critical)
        """
        new_combo = {
            "words": [word1, word2],
            "category": category,
            "severity": severity
        }
        
        if new_combo not in self.rules.get('word_combinations', []):
            if 'word_combinations' not in self.rules:
                self.rules['word_combinations'] = []
            self.rules['word_combinations'].append(new_combo)
            self.save_rules()
            logger.info(f"Добавлена новая комбинация слов: {word1} + {word2} (категория: {category})")

# Создаем глобальный экземпляр правил
moderation_rules = ModerationRules() 