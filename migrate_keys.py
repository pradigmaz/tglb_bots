import sqlite3
from utils import encrypt_api_key, decrypt_api_key
from logger import logger

def migrate_api_keys():
    """
    Миграция существующих API-ключей: шифрование всех незашифрованных ключей
    """
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    try:
        # Получаем все API-ключи
        cursor.execute('SELECT user_id, api_key FROM users WHERE api_key IS NOT NULL')
        users = cursor.fetchall()
        
        migrated = 0
        failed = 0
        
        for user_id, api_key in users:
            try:
                # Пробуем расшифровать ключ - если не получается, значит он не зашифрован
                if not api_key or decrypt_api_key(api_key):
                    continue
                    
                # Шифруем ключ
                encrypted_key = encrypt_api_key(api_key)
                if encrypted_key:
                    cursor.execute(
                        'UPDATE users SET api_key = ? WHERE user_id = ?',
                        (encrypted_key, user_id)
                    )
                    migrated += 1
                    logger.info(f"API-ключ пользователя {user_id} успешно зашифрован")
                else:
                    failed += 1
                    logger.error(f"Не удалось зашифровать API-ключ пользователя {user_id}")
            except Exception as e:
                failed += 1
                logger.error(f"Ошибка при миграции ключа пользователя {user_id}: {e}")
        
        conn.commit()
        logger.info(f"Миграция завершена. Успешно: {migrated}, Ошибок: {failed}")
        print(f"Миграция завершена. Успешно: {migrated}, Ошибок: {failed}")
        
    except Exception as e:
        logger.error(f"Ошибка при миграции ключей: {e}")
        print(f"Ошибка при миграции ключей: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    print("Начинаем миграцию API-ключей...")
    migrate_api_keys() 