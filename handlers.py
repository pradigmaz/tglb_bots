from aiogram import types
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.utils import executor
from aiogram.dispatcher.filters import Command
from logger import logger, log_moderation, log_violation, log_ban
from database import db
from api_client import OpenRouterClient
from api_reconnector import APIReconnector
from moderator import Moderator
from utils import (is_valid_api_key, format_error_message, format_moderation_message, 
                  is_admin, safe_reply)
from datetime import datetime, timedelta
from cache import Cache
from hints import hint_system  # Добавляем импорт системы подсказок
from states import FeedbackStates
from validators import validator, format_markdown_message  # Добавляем импорт
from exceptions import ApiError, ValidationError, RateLimitError  # Добавляем импорт исключений
from formatting import (
    format_message, format_code, format_error,
    format_section, format_list, safe_format_message
)



# Константа с текстом помощи для админов
ADMIN_HELP_TEXT = """
🔑 *Команды администратора*

📊 *Управление пользователями:*
• /admin_users \\- Список пользователей бота
• /admin_logs \[user_id\] \[days\] \\- Логи взаимодействия

📝 *Модерация:*
• /view_feedback \\- Просмотр отзывов
"""

# Константа с общим текстом помощи
HELP_TEXT = """
🤖 *Основные команды:*

• /start \\- Начать работу с ботом
• /help \\- Показать это сообщение
• /reset \\- Сбросить API\\-ключ
• /restart \\- Сбросить историю диалога
• /rules \\- Показать правила
• /examples \\- Показать примеры вопросов
• /feedback \\- Отправить отзыв

📝 *Как задавать вопросы:*
• Пишите вопрос четко и понятно
• Указывайте контекст проблемы
• Прикладывайте код, если нужно

⚠️ *Система нарушений:*
• 1\\-е нарушение: Предупреждение
• 2\\-е нарушение: Бан на 5 минут
• 3\\-е нарушение: Бан на 10 минут
• 4\\-е нарушение: Бан на 30 минут
• 5\\-е нарушение: Бан на 60 минут

ℹ️ Нарушения автоматически сбрасываются через 24 часа
"""

# Создаем экземпляр модератора
moderator = Moderator()

# Создаем экземпляр кэша
cache = Cache(max_size=1000, ttl=3600)  # 1000 записей, TTL 1 час

# Здесь будут обработчики команд

async def cmd_start(message: types.Message):
    """
    Обработчик команды /start
    """
    user_id = message.from_user.id
    logger.info(f"Получена команда /start от пользователя {user_id}")
    
    # Проверяем, есть ли у пользователя API-ключ
    user_data = db.get_user(user_id)
    
    if user_data and user_data[0]:  # api_key is first in tuple
        # У пользователя уже есть API-ключ
        await message.reply(
            "👋 С возвращением! Я готов помочь тебе в обучении.\n\n"
            "🤔 Просто задай свой вопрос, и я постараюсь объяснить материал.\n\n"
            "📚 Помни, что я здесь, чтобы помочь тебе *понять* материал, "
            "а не сделать работу за тебя.\n\n"
            "❓ Если нужна помощь по командам, используй /help",
            parse_mode=types.ParseMode.MARKDOWN
        )
    else:
        # У пользователя нет API-ключа
        await message.reply(
            "👋 Привет! Я бот-учитель, который поможет тебе в обучении.\n\n"
            "🔑 Для начала работы мне нужен твой API-ключ от OpenRouter.\n"
            "Его можно получить на сайте: https://openrouter.ai/keys\n\n"
            "✉️ Пожалуйста, отправь мне свой ключ.",
            parse_mode=types.ParseMode.MARKDOWN
        )

async def cmd_help(message: types.Message):
    """
    Обработчик команды /help
    """
    user_id = message.from_user.id
    logger.info(f"Получена команда /help от пользователя {user_id}")
    
    try:
        help_text = HELP_TEXT
        
        # Добавляем секцию для админов
        if is_admin(user_id):
            admin_section = "\n\n🔑 *Для администраторов:*\n• Используйте /admin\_help для просмотра списка команд администратора"
            help_text += admin_section
        
        await message.reply(help_text, parse_mode=types.ParseMode.MARKDOWN_V2)
    except Exception as e:
        logger.error(f"Ошибка при отправке справки: {str(e)}")
        await safe_reply(message, "❌ Произошла ошибка при отправке справки. Попробуйте позже.")

async def cmd_reset(message: types.Message):
    """
    Обработчик команды /reset
    """
    user_id = message.from_user.id
    logger.info(f"Получена команда /reset от пользователя {user_id}")
    
    if db.delete_user(user_id):
        logger.info(f"API-ключ пользователя {user_id} удален")
        await message.reply(
            "Твой API-ключ был удален. "
            "Пожалуйста, отправь мне новый ключ для продолжения работы."
        )
    else:
        logger.error(f"Ошибка при удалении API-ключа пользователя {user_id}")
        await message.reply("Произошла ошибка при удалении ключа. Попробуйте позже.")

async def process_api_key(message: types.Message):
    """
    Обработка API-ключа
    """
    user_id = message.from_user.id
    api_key = message.text.strip()
    
    logger.info(f"Получен API-ключ от пользователя {user_id}")
    
    # Проверяем формат ключа
    if not is_valid_api_key(api_key):
        logger.warning(f"Неверный формат API-ключа от пользователя {user_id}")
        await message.reply(
            "Неверный формат API-ключа. "
            "Ключ должен начинаться с 'sk-'. Пожалуйста, проверьте ключ и отправьте его снова."
        )
        return
    
    # Проверяем ключ через API
    try:
        client = APIReconnector(api_key)
        if await client.client.check_api_key():
            # Сохраняем ключ в базу
            if db.add_user(user_id, api_key):
                logger.info(f"API-ключ пользователя {user_id} успешно сохранен")
                await message.reply(
                    "API-ключ успешно сохранен! "
                    "Теперь ты можешь задавать мне вопросы, и я постараюсь помочь тебе разобраться с ними."
                )
            else:
                logger.error(f"Ошибка при сохранении API-ключа пользователя {user_id}")
                await message.reply("Произошла ошибка при сохранении ключа. Попробуйте позже.")
        else:
            logger.warning(f"Недействительный API-ключ от пользователя {user_id}")
            await message.reply(
                "Недействительный API-ключ. "
                "Пожалуйста, проверьте ключ и попробуйте снова."
            )
    except Exception as e:
        logger.error(f"Ошибка при проверке API-ключа пользователя {user_id}: {e}")
        await message.reply(format_error(str(e), "Попробуйте повторить действие позже"))

async def process_message(message: types.Message):
    """
    Обработка обычных сообщений (вопросов)
    """
    user_id = message.from_user.id
    
    # Пропускаем команды
    if message.text.startswith('/'):
        return
    
    # Если это админ и сообщение начинается с '/', пропускаем проверку API-ключа
    if is_admin(user_id) and message.text.startswith('/'):
        return
        
    logger.info(f"Получено сообщение от пользователя {user_id}: {message.text[:100]}")
    
    # Проверяем время последней активности и показываем подсказку при необходимости
    last_activity = db.get_last_activity(user_id)
    if last_activity:
        if hint_system.should_show_hint(user_id, last_activity):
            hint = hint_system.get_hint(user_id, 'inactive')
            if hint:
                await safe_reply(message, hint)
    
    # Обновляем время последней активности
    db.update_last_activity(user_id)
    
    # Проверяем, есть ли у пользователя API-ключ
    user_data = db.get_user(user_id)
    if not user_data or not user_data[0]:  # api_key is first in tuple
        await safe_reply(message,
            "🔑 Для начала работы мне нужен твой API-ключ от OpenRouter.\n"
            "Его можно получить на сайте: https://openrouter.ai/keys\n\n"
            "✉️ Пожалуйста, отправь мне свой ключ."
        )
        return
    
    # Проверяем бан
    is_banned, reason = db.is_banned(user_id)
    if is_banned:
        await safe_reply(message,
            f"⛔️ *Вы заблокированы*\n\n"
            f"Причина: {reason}"
        )
        return
    
    # Проверяем кэш перед обращением к API
    cached_response = cache.get(message.text)
    if cached_response:
        logger.info(f"Найден кэшированный ответ для пользователя {user_id}")
        try:
            formatted_response = format_message(cached_response)
            await message.reply(formatted_response, parse_mode=types.ParseMode.MARKDOWN_V2)
        except Exception as e:
            logger.error(f"Ошибка при отправке кэшированного ответа: {str(e)}")
            await safe_reply(message, cached_response)
        return
    
    try:
        # Создаем клиента API с автоматическим переподключением
        api_client = APIReconnector(user_data[0])  # api_key
        
        # Для админов пропускаем модерацию
        if is_admin(user_id):
            logger.info(f"Админ {user_id} обошел модерацию: {message.text[:100]}")
        else:
            # Проверяем сообщение через модератор
            is_violation, violation_reason = await moderator.moderate_message(message.text, api_client)
            
            if is_violation:
                # Логируем нарушение
                log_violation(user_id, "content_policy", message.text, violation_reason)
                
                # Добавляем нарушение в базу
                success, violations_count = db.add_violation(user_id, "content_policy", violation_reason, message.text)
                if not success:
                    logger.error(f"Не удалось добавить нарушение в базу для пользователя {user_id}")
                    await safe_reply(message,
                        "⚠️ *Произошла ошибка при обработке нарушения*\n"
                        "Пожалуйста, попробуйте позже."
                    )
                    return
                
                # Определяем действие в зависимости от количества нарушений
                if violations_count == 1:
                    # Первое нарушение - предупреждение
                    await safe_reply(message,
                        "⚠️ *Предупреждение*\n\n"
                        f"Причина: {violation_reason}\n\n"
                        "Пожалуйста, ознакомьтесь с правилами использования бота. "
                        "Следующее нарушение приведет к временной блокировке."
                    )
                else:
                    # Получаем длительность бана
                    ban_duration = db.get_ban_duration(violations_count)
                    if ban_duration > 0:
                        if db.ban_user(user_id, violation_reason, minutes=ban_duration):
                            log_ban(user_id, f"Нарушение #{violations_count}: {violation_reason}")
                            await safe_reply(message,
                                f"🚫 *Вы заблокированы на {ban_duration} минут*\n\n"
                                f"Причина: {violation_reason}\n\n"
                                "Бот автоматически разблокирует вас по истечении срока.\n"
                                "Пожалуйста, используйте это время, чтобы ознакомиться с правилами."
                            )
                        else:
                            logger.error(f"Не удалось забанить пользователя {user_id}")
                return
        
        # Если сообщение прошло модерацию или отправитель - админ
        await message.bot.send_chat_action(message.chat.id, types.ChatActions.TYPING)
        
        # Получаем ответ от LearnLM
        response = await api_client.get_learnlm_response(message.text)
        
        try:
            # Форматируем ответ с помощью нового форматтера
            formatted_response = format_message(response)
            
            # Отправляем ответ
            await message.reply(formatted_response, parse_mode=types.ParseMode.MARKDOWN_V2)
            
            # Сохраняем в кэш
            cache.set(message.text, response)
            
        except Exception as e:
            logger.error(f"Ошибка при форматировании ответа: {str(e)}")
            # В случае ошибки форматирования отправляем без форматирования
            await safe_reply(message, response)
            
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения от пользователя {user_id}: {e}")
        await safe_reply(message, format_error(str(e), "Попробуйте повторить действие позже"))

async def cmd_admin_users(message: types.Message):
    """
    Обработчик команды /admin_users - показывает список пользователей бота
    """
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply("⛔️ У вас нет прав для выполнения этой команды.")
        return

    logger.info(f"Запрос списка пользователей от администратора {user_id}")
    
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        
        # Получаем список пользователей с основной информацией
        cursor.execute('''
            SELECT 
                u.user_id, 
                COUNT(v.id) as violations_count,
                u.is_banned,
                (SELECT MAX(violation_date) FROM violations WHERE user_id = u.user_id) as last_violation_date,
                u.last_activity
            FROM users u
            LEFT JOIN violations v ON u.user_id = v.user_id
            GROUP BY u.user_id
            ORDER BY u.last_activity DESC NULLS LAST
        ''')
        
        users = cursor.fetchall()
        
        if not users:
            await message.reply("📊 Пользователей пока нет.")
            return
            
        response = "📊 *Список пользователей бота:*\n\n"
        for user in users:
            user_id, violations, is_banned, last_violation, last_activity = user
            status = "🚫 Забанен" if is_banned else "✅ Активен"
            
            # Обработка последней активности
            last_active_str = "Нет активности"
            if last_activity:
                try:
                    last_active = datetime.fromisoformat(last_activity)
                    last_active_str = last_active.strftime("%d.%m.%Y %H:%M")
                except (ValueError, TypeError):
                    last_active_str = "Некорректная дата"
            
            # Обработка последнего нарушения
            last_violation_str = "Нет нарушений"
            if last_violation:
                try:
                    last_violation_date = datetime.fromisoformat(last_violation)
                    last_violation_str = last_violation_date.strftime("%d.%m.%Y %H:%M")
                except (ValueError, TypeError):
                    last_violation_str = "Некорректная дата"
            
            response += (f"👤 *ID:* `{user_id}`\n"
                        f"📅 Последняя активность: {last_active_str}\n"
                        f"⚠️ Нарушений: {violations}\n"
                        f"🕒 Последнее нарушение: {last_violation_str}\n"
                        f"📌 Статус: {status}\n\n")
            
        await message.reply(response, parse_mode=types.ParseMode.MARKDOWN)
        
    except Exception as e:
        logger.error(f"Ошибка при получении списка пользователей: {e}")
        await message.reply("❌ Произошла ошибка при получении списка пользователей.")
    finally:
        cursor.close()
        conn.close()

async def cmd_admin_logs(message: types.Message):
    """
    Обработчик команды /admin_logs - показывает логи взаимодействия пользователей с ботом
    """
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply("⛔️ У вас нет прав для выполнения этой команды.")
        return
    
    # Получаем ID пользователя из аргументов команды, если есть
    args = message.get_args().split()
    target_user_id = int(args[0]) if args and args[0].isdigit() else None
    days = int(args[1]) if len(args) > 1 and args[1].isdigit() else 7  # По умолчанию за 7 дней
    
    logger.info(f"Запрос логов от администратора {user_id}" + 
               (f" для пользователя {target_user_id}" if target_user_id else ""))
    
    try:
        conn = db._get_connection()
        cursor = conn.cursor()
        
        # Формируем базовый запрос
        query = '''
            SELECT v.user_id,
                   v.violation_date,
                   v.message_text,
                   v.violation_type,
                   v.violation_reason
            FROM violations v
            WHERE v.violation_date >= ?
        '''
        params = [(datetime.now() - timedelta(days=days)).isoformat()]
        
        if target_user_id:
            query += " AND v.user_id = ?"
            params.append(target_user_id)
            
        query += " ORDER BY v.violation_date DESC LIMIT 50"  # Ограничиваем количество записей
        
        cursor.execute(query, params)
        logs = cursor.fetchall()
        
        if not logs:
            await message.reply(
                "📊 *Логи взаимодействия с ботом*\n\n"
                f"За последние {days} дней "
                f"{('для пользователя ' + str(target_user_id)) if target_user_id else ''}"
                " логов не найдено.",
                parse_mode=types.ParseMode.MARKDOWN
            )
            return
            
        response = [f"📊 *Логи взаимодействия с ботом*\n"
                   f"За последние {days} дней "
                   f"{('для пользователя ' + str(target_user_id)) if target_user_id else ''}\n\n"]
                  
        for log in logs:
            user_id, date, text, type_, reason = log
            date_str = datetime.fromisoformat(date).strftime("%d.%m.%Y %H:%M")
            
            log_entry = (f"👤 *ID:* `{user_id}`\n"
                        f"📅 *Дата:* {date_str}\n"
                        f"💬 *Сообщение:* `{text[:100]}`{'...' if len(text) > 100 else ''}\n"
                        f"📌 *Тип:* `{type_}`\n"
                        f"❗️ *Причина:* `{reason}`\n\n")
            
            # Если текущий ответ станет слишком длинным, начинаем новый
            if len(response[-1] + log_entry) > 3500:
                response.append(log_entry)
            else:
                response[-1] += log_entry
        
        # Отправляем все части сообщения
        for part in response:
            await message.reply(part, parse_mode=types.ParseMode.MARKDOWN)
            
    except Exception as e:
        logger.error(f"Ошибка при получении логов: {e}")
        await message.reply("❌ Произошла ошибка при получении логов.")
    finally:
        cursor.close()
        conn.close()

async def cmd_admin_help(message: types.Message):
    """
    Обработчик команды /admin_help - показывает справку по админ-командам
    """
    user_id = message.from_user.id
    if not is_admin(user_id):
        await message.reply(format_error("У вас нет прав для выполнения этой команды."))
        return
        
    try:
        help_text = format_section(
            "🔑 Команды администратора",
            format_section(
                "📊 Управление пользователями:",
                format_list([
                    "/admin\\_users \\- Список пользователей бота",
                    "/admin\\_logs \\[user\\_id\\] \\[days\\] \\- Логи взаимодействия"
                ])
            ),
            format_section(
                "📝 Модерация:",
                format_list([
                    "/view\\_feedback \\- Просмотр отзывов\\:",
                    "  • /view\\_feedback \\- непрочитанные отзывы",
                    "  • /view\\_feedback all \\- все отзывы",
                    "  • /view\\_feedback read \\- прочитанные отзывы",
                    "  • /view\\_feedback unread \\- непрочитанные отзывы",
                    "  • Добавьте номер страницы: /view\\_feedback all 2"
                ])
            )
        )
        
        await message.reply(help_text, parse_mode=types.ParseMode.MARKDOWN_V2)
    except Exception as e:
        logger.error(f"Ошибка при отправке справки админа: {str(e)}")
        # В случае ошибки пробуем отправить без форматирования
        await safe_reply(message, "Команды администратора:\n\n/admin_users - Список пользователей\n/admin_logs - Логи\n/view_feedback - Отзывы")

async def cmd_rules(message: types.Message):
    """
    Обработчик команды /rules - показывает правила использования бота
    """
    logger.info(f"Получена команда /rules от пользователя {message.from_user.id}")
    
    rules_text = """
    📋 *Правила использования бота*

    1️⃣ *Основные правила:*
    • Задавайте конкретные вопросы по учебному материалу
    • Описывайте, что именно вы не понимаете
    • Прикладывайте контекст (условие задачи, код и т.д.)
    
    2️⃣ *Запрещено:*
    • ❌ Просить готовые решения задач
    • ❌ Спамить и отправлять рекламу
    • ❌ Использовать нецензурную лексику
    • ❌ Оскорблять других пользователей
    
    3️⃣ *Система предупреждений:*
    • Первое нарушение: Предупреждение
    • Второе нарушение: Последнее предупреждение
    • Третье нарушение: Бан на 2 минуты
    • Четвертое нарушение: Постоянный бан
    
    4️⃣ *Примеры правильных запросов:*
    • ✅ "Объясни, как работает сортировка пузырьком"
    • ✅ "Помоги понять принцип работы рекурсии"
    • ✅ "В чём разница между списком и кортежем в Python?"
    
    5️⃣ *Примеры неправильных запросов:*
    • ❌ "Реши эту задачу за меня"
    • ❌ "Напиши готовое решение"
    • ❌ "Сделай мою домашку"
    
    💡 *Помните:* Бот создан, чтобы помочь вам *понять* материал, а не сделать работу за вас.
    """
    
    await message.reply(rules_text, parse_mode=types.ParseMode.MARKDOWN)

async def cmd_violations(message: types.Message):
    """
    Обработчик команды /violations - показывает информацию о нарушениях пользователя
    """
    user_id = message.from_user.id
    logger.info(f"Получена команда /violations от пользователя {user_id}")
    
    try:
        # Очищаем устаревшие нарушения
        logger.info(f"Очистка устаревших нарушений для пользователя {user_id}")
        db.clear_expired_violations(user_id)
        
        # Получаем количество активных нарушений
        violations_count = db.get_user_violations_count(user_id)
        logger.info(f"Количество активных нарушений пользователя {user_id}: {violations_count}")
        
        if violations_count == 0:
            logger.info(f"У пользователя {user_id} нет активных нарушений")
            await safe_reply(message,
                "✅ *У вас нет активных нарушений*\n\n"
                "Продолжайте соблюдать правила использования бота!"
            )
            return
        
        # Получаем историю нарушений
        violations = db.get_violations(user_id)
        if not violations:
            logger.warning(f"Не удалось получить историю нарушений пользователя {user_id}")
            await safe_reply(message,
                "❓ *Странно...*\n\n"
                "Произошла ошибка при получении информации о нарушениях.\n"
                "Пожалуйста, попробуйте позже или обратитесь к администратору."
            )
            return
        
        # Формируем сообщение
        response = [f"📊 *Информация о ваших нарушениях*\n\n"
                   f"Активных нарушений: {violations_count}\n"]
        
        # Добавляем информацию о сроке действия нарушений
        c = db._get_connection().cursor()
        try:
            c.execute('SELECT violations_expire_at FROM users WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            if result and result[0]:
                expire_at = datetime.fromisoformat(result[0])
                time_left = expire_at - datetime.now()
                if time_left.total_seconds() > 0:
                    hours = int(time_left.total_seconds() // 3600)
                    minutes = int((time_left.total_seconds() % 3600) // 60)
                    response.append(f"Нарушения будут сброшены через: {hours}ч {minutes}м\n")
                    logger.info(f"Нарушения пользователя {user_id} будут сброшены через {hours}ч {minutes}м")
        finally:
            c.close()
        
        response.append("\n*Последние нарушения:*\n")
        
        # Добавляем последние 5 нарушений
        for i, (type_, reason, date, _) in enumerate(violations[:5], 1):
            violation_date = datetime.fromisoformat(date)
            response.append(
                f"{i}. *{violation_date.strftime('%d.%m.%Y %H:%M')}*\n"
                f"Тип: {type_}\n"
                f"Причина: {reason}\n"
            )
        
        logger.info(f"Отправка информации о нарушениях пользователю {user_id}")
        await safe_reply(message, "".join(response))
        
    except Exception as e:
        logger.error(f"Ошибка при получении информации о нарушениях пользователя {user_id}: {e}")
        await safe_reply(message,
            "❌ *Произошла ошибка*\n\n"
            "Не удалось получить информацию о нарушениях.\n"
            "Пожалуйста, попробуйте позже или обратитесь к администратору."
        )

async def cmd_feedback(message: types.Message, state: FSMContext):
    """
    Обработчик команды /feedback
    """
    user_id = message.from_user.id
    logger.info(f"Получена команда /feedback от пользователя {user_id}")
    
    # Устанавливаем состояние ожидания отзыва
    await FeedbackStates.waiting_for_feedback.set()
    
    await message.reply(
        "📝 Пожалуйста, напишите ваш отзыв о работе бота в следующем сообщении.\n"
        "Вы можете описать, что вам нравится или не нравится, "
        "какие функции хотелось бы добавить или улучшить.\n\n"
        "Для отмены напишите /cancel",
        parse_mode=types.ParseMode.MARKDOWN
    )

async def cmd_cancel(message: types.Message, state: FSMContext):
    """
    Обработчик команды /cancel
    """
    current_state = await state.get_state()
    if current_state is not None:
        await state.finish()
        await message.reply("❌ Действие отменено")
        logger.info(f"Пользователь {message.from_user.id} отменил действие")
    else:
        await message.reply("🤔 Нечего отменять")

async def process_feedback(message: types.Message, state: FSMContext):
    """
    Обработка отзыва от пользователя
    """
    user_id = message.from_user.id
    feedback_text = message.text.strip()
    
    # Получаем информацию о пользователе
    username = message.from_user.username
    first_name = message.from_user.first_name
    last_name = message.from_user.last_name
    
    # Сохраняем отзыв
    if db.add_feedback(user_id, feedback_text, username, first_name, last_name):
        logger.info(f"Сохранен отзыв от пользователя {user_id}")
        await message.reply(
            "✅ Спасибо за ваш отзыв! Мы обязательно учтем его при улучшении бота.",
            parse_mode=types.ParseMode.MARKDOWN
        )
    else:
        logger.error(f"Ошибка при сохранении отзыва от пользователя {user_id}")
        await message.reply(
            "❌ Произошла ошибка при сохранении отзыва. Пожалуйста, попробуйте позже.",
            parse_mode=types.ParseMode.MARKDOWN
        )
    
    # Сбрасываем состояние
    await state.finish()

async def cmd_view_feedback(message: types.Message):
    """
    Обработчик команды /view_feedback (только для админов)
    Использование:
    /view_feedback - показать непрочитанные отзывы
    /view_feedback all - показать все отзывы
    /view_feedback read - показать прочитанные отзывы
    /view_feedback unread - показать непрочитанные отзывы
    Можно добавить номер страницы: /view_feedback all 2
    """
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await message.reply("⛔️ У вас нет прав для выполнения этой команды")
        return
    
    # Разбор параметров команды
    args = message.get_args().split()
    filter_type = args[0] if args else 'unread'  # По умолчанию показываем непрочитанные
    page = int(args[1]) if len(args) > 1 and args[1].isdigit() else 1
    
    if filter_type not in ['all', 'read', 'unread']:
        filter_type = 'unread'
    
    # Получаем общее количество отзывов
    total_count = db.get_feedback_count(filter_type)
    
    if total_count == 0:
        status_text = {
            'all': 'отзывов',
            'read': 'прочитанных отзывов',
            'unread': 'непрочитанных отзывов'
        }
        await message.reply(f"📝 Нет {status_text[filter_type]}")
        return
    
    # Настройки пагинации
    items_per_page = 10
    total_pages = (total_count + items_per_page - 1) // items_per_page
    page = min(max(1, page), total_pages)  # Убеждаемся, что страница в допустимых пределах
    offset = (page - 1) * items_per_page
    
    # Получаем отзывы
    feedback_list = db.get_feedback(filter_type, items_per_page, offset)
    
    # Формируем заголовок сообщения
    header_text = {
        'all': 'Все отзывы',
        'read': 'Прочитанные отзывы',
        'unread': 'Непрочитанные отзывы'
    }
    feedback_text = f"📋 *{header_text[filter_type]}*\n"
    feedback_text += f"Страница {page} из {total_pages}\n\n"
    
    # Формируем список отзывов
    for feedback_id, user_id, text, created_at, username, first_name, last_name, is_read in feedback_list:
        feedback_text += f"*ID:* {feedback_id}\n"
        
        # Формируем информацию о пользователе
        user_info = []
        if username:
            user_info.append(f"@{username}")
        if first_name:
            user_info.append(first_name)
        if last_name:
            user_info.append(last_name)
        
        user_display = " ".join(user_info) if user_info else str(user_id)
        feedback_text += f"*От:* {user_display} (ID: {user_id})\n"
        feedback_text += f"*Дата:* {created_at}\n"
        feedback_text += f"*Статус:* {'Прочитано' if is_read else 'Не прочитано'}\n"
        feedback_text += f"*Текст:* {text}\n"
        feedback_text += "-" * 30 + "\n"
        
        # Отмечаем отзыв как прочитанный, если он непрочитанный
        if not is_read:
            db.mark_feedback_as_read(feedback_id)
    
    # Добавляем инструкции по навигации
    feedback_text += "\n💡 *Навигация:*\n"
    feedback_text += f"• Текущий фильтр: {filter_type}\n"
    feedback_text += f"• Страница {page} из {total_pages}\n"
    feedback_text += "• Используйте /view_feedback [all|read|unread] [страница]\n"
    
    # Отправляем сообщение частями, если оно слишком длинное
    if len(feedback_text) > 4000:
        parts = [feedback_text[i:i+4000] for i in range(0, len(feedback_text), 4000)]
        for part in parts:
            await message.reply(part, parse_mode=types.ParseMode.MARKDOWN)
    else:
        await message.reply(feedback_text, parse_mode=types.ParseMode.MARKDOWN)

async def cmd_clear_cache(message: types.Message):
    """
    Обработчик команды /clear_cache (только для админов)
    """
    user_id = message.from_user.id
    
    if not is_admin(user_id):
        await safe_reply(message, "⛔️ У вас нет прав для выполнения этой команды.")
        return
    
    # Очищаем устаревшие записи
    cache.clear_expired()
    
    # Получаем статистику кэша
    stats = cache.get_stats()
    
    await safe_reply(message,
        f"🗑 *Кэш очищен*\n\n"
        f"📊 *Статистика:*\n"
        f"• Записей в кэше: {stats['total_entries']}\n"
        f"• Максимальный размер: {stats['max_size']}\n"
        f"• Время жизни записи: {stats['ttl']} сек\n"
        f"• Использование памяти: {stats['memory_usage']} байт",
        parse_mode=types.ParseMode.MARKDOWN
    )

async def cmd_examples(message: types.Message):
    """
    Обработчик команды /examples - показывает примеры правильных вопросов
    """
    user_id = message.from_user.id
    logger.info(f"Получена команда /examples от пользователя {user_id}")
    
    examples_text = (
        "📝 *Примеры вопросов*\n\n"
        "*HTML:*\n"
        f"{hint_system.get_example('html')}\n\n"
        "*CSS:*\n"
        f"{hint_system.get_example('css')}\n\n"
        "*Вёрстка и макеты:*\n"
        f"{hint_system.get_example('layout')}\n\n"
        "💡 Помните: чем конкретнее вопрос, тем полезнее будет ответ!\n\n"
        "🔍 Полезные советы:\n"
        "• Всегда показывайте ваш текущий код\n"
        "• Описывайте желаемый результат\n"
        "• Указывайте, что вы уже пробовали\n"
        "• Сообщайте о требованиях к браузерам\n"
        "• Упоминайте особенности адаптивности"
    )
    
    await safe_reply(message, examples_text, parse_mode=types.ParseMode.MARKDOWN_V2)

async def cmd_restart(message: types.Message):
    """
    Обработчик команды /restart - сброс диалога с ботом
    """
    user_id = message.from_user.id
    logger.info(f"Получена команда /restart от пользователя {user_id}")
    
    # Очищаем историю диалога для пользователя
    cache.clear_user_history(user_id)
    
    await message.reply(
        "🔄 Диалог сброшен.\n"
        "Теперь вы можете начать новую беседу.\n\n"
        "💡 Используйте /help, чтобы увидеть список доступных команд.",
        parse_mode=types.ParseMode.MARKDOWN
    )

async def handle_error(update: types.Update, exception: Exception) -> None:
    """Обработчик ошибок"""
    try:
        if isinstance(exception, ApiError):
            message = format_error(str(exception), "Проверьте правильность введенных данных")
        elif isinstance(exception, ValidationError):
            message = format_error(str(exception), "Убедитесь, что ваш запрос соответствует требованиям")
        elif isinstance(exception, RateLimitError):
            message = format_error(
                f"Превышен лимит запросов. Попробуйте снова через {exception.wait_time} секунд",
                "Подождите некоторое время перед следующим запросом"
            )
        else:
            message = format_error(str(exception), "Попробуйте повторить действие позже")
        
        await update.message.reply(message, parse_mode=types.ParseMode.MARKDOWN_V2)
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике ошибок: {str(e)}")
        await update.message.reply(
            format_error("Произошла непредвиденная ошибка. Попробуйте позже."),
            parse_mode=types.ParseMode.MARKDOWN_V2
        )

def register_handlers(dp: Dispatcher):
    """
    Регистрация всех обработчиков
    """
    logger.info("Регистрация обработчиков команд...")
    
    # Основные команды
    dp.register_message_handler(cmd_start, commands=['start'])
    dp.register_message_handler(cmd_help, commands=['help'])
    dp.register_message_handler(cmd_reset, commands=['reset'])
    dp.register_message_handler(cmd_rules, commands=['rules'])
    dp.register_message_handler(cmd_violations, commands=['violations'])
    dp.register_message_handler(cmd_examples, commands=['examples'])
    dp.register_message_handler(cmd_restart, commands=['restart'])  # Добавляем новый обработчик
    
    # Админ-команды
    dp.register_message_handler(cmd_admin_users, commands=['admin_users', 'adminusers'])
    dp.register_message_handler(cmd_admin_logs, commands=['admin_logs', 'adminlogs'])
    dp.register_message_handler(cmd_admin_help, commands=['admin_help', 'adminhelp'])
    
    # Обработка API-ключа
    dp.register_message_handler(
        process_api_key,
        lambda message: message.text.startswith('sk-')
    )
    
    # Обработка отзывов
    dp.register_message_handler(cmd_feedback, commands=['feedback'], state=None)
    dp.register_message_handler(cmd_cancel, commands=['cancel'], state='*')
    dp.register_message_handler(process_feedback, state=FeedbackStates.waiting_for_feedback)
    dp.register_message_handler(cmd_view_feedback, commands=['view_feedback', 'viewfeedback'])
    
    # Новая команда
    dp.register_message_handler(cmd_clear_cache, commands=['clear_cache'])
    
    # Обработка всех остальных сообщений (должна быть последней)
    dp.register_message_handler(process_message)
    
    # Обработка ошибок
    dp.register_message_handler(handle_error)
    
    logger.info("Обработчики команд зарегистрированы") 