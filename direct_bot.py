#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Прямой запуск бота оптимизации
"""

import sys
import os
import subprocess
import logging
import time
import requests
from urllib.parse import quote_plus

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def reset_bot_sessions():
    """
    Сбрасывает все активные сессии бота через Telegram API
    """
    try:
        # Получаем токен из переменных окружения
        token = os.environ.get('TELEGRAM_TOKEN')
        if not token:
            logger.error("Токен Telegram не найден в переменных окружения")
            return False
            
        # Формируем URL для сброса webhook
        base_url = f'https://api.telegram.org/bot{token}'
        delete_webhook_url = f'{base_url}/deleteWebhook?drop_pending_updates=true'
        
        # Отправляем запрос на сброс webhook
        logger.info("Сброс webhook и активных сессий...")
        response = requests.get(delete_webhook_url, timeout=30)
        
        if response.status_code == 200:
            logger.info("Webhook успешно сброшен")
            # Делаем паузу для полного завершения предыдущих сессий
            time.sleep(10)
            return True
        else:
            logger.error(f"Ошибка при сбросе webhook: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при сбросе сессий бота: {e}")
        return False

# Проверка наличия ключа API в переменных окружения 
api_key = os.environ.get('ANTHROPIC_API_KEY', '')
if not api_key:
    logger.warning("ВНИМАНИЕ: API ключ Anthropic (ANTHROPIC_API_KEY) не найден в переменных окружения!")
    logger.warning("Бот будет работать в режиме заглушек и не сможет генерировать оригинальные скрипты")
    logger.warning("Установите переменную окружения ANTHROPIC_API_KEY с вашим API ключом")
else:
    logger.info(f"API ключ Anthropic найден (длина: {len(api_key)} символов)")

def modify_bot_file():
    """
    Минимальная модификация файла бота для поддержки infinity_polling
    """
    try:
        bot_file_path = "optimization_bot.py"
        
        if not os.path.exists(bot_file_path):
            logger.error(f"Файл бота {bot_file_path} не найден")
            return False
        
        logger.info(f"Открываю файл бота {bot_file_path} для модификации")
        
        # Чтение содержимого файла
        with open(bot_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Добавляем только обработку ошибок при запуске polling
        if "bot.infinity_polling(" not in content and "bot.polling(none_stop=True)" in content:
            # Заменяем обычный polling на infinity_polling с таймаутами
            content = content.replace(
                "bot.polling(none_stop=True)", 
                "bot.infinity_polling(timeout=30, long_polling_timeout=15)"
            )
            logger.info("Заменен метод polling на infinity_polling для большей стабильности")
        
        # Сохраняем измененный файл
        with open(bot_file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        
        logger.info(f"Файл бота {bot_file_path} успешно модифицирован")
        return True
    except Exception as e:
        logger.error(f"Ошибка при модификации файла бота: {e}")
        return False

def main():
    """
    Основная функция запуска бота
    """
    try:
        # Сначала сбрасываем все активные сессии
        if not reset_bot_sessions():
            logger.warning("Не удалось сбросить активные сессии бота")
            # Делаем дополнительную паузу перед запуском
            time.sleep(15)
        
        # Запускаем бот оптимизации
        logger.info("Запуск бота оптимизации")
        
        # Модифицируем файл бота
        if os.path.exists("optimization_bot.py"):
            logger.info("Открываю файл бота optimization_bot.py для модификации")
            modified = modify_bot_file()
            logger.info(f"Результат модификации файла: {'успешно' if modified else 'неудачно'}")
        else:
            logger.warning("Файл optimization_bot.py не найден")
        
        # Небольшая пауза перед запуском для стабилизации системы
        logger.info("Ожидание 3 секунд перед запуском бота...")
        time.sleep(3)
        
        # Запускаем файл optimization_bot.py
        try:
            logger.info("Запуск optimization_bot.py")
            import optimization_bot
            logger.info("Файл optimization_bot.py успешно импортирован")
            
            # Явно вызываем функцию main из модуля optimization_bot
            if hasattr(optimization_bot, 'main'):
                logger.info("Запуск функции main() из модуля optimization_bot")
                optimization_bot.main()
            else:
                logger.error("Функция main() не найдена в модуле optimization_bot")
        except Exception as e:
            if "409" in str(e):
                logger.warning(f"Обнаружен конфликт сессий (409): {e}")
                # Пробуем сбросить сессии еще раз
                if reset_bot_sessions():
                    logger.info("Повторный запуск бота после сброса сессий")
                    # Запускаем через subprocess для чистого старта
                    subprocess.run([sys.executable, "optimization_bot.py"])
                else:
                    logger.error("Не удалось сбросить сессии после конфликта")
            else:
                logger.error(f"Ошибка при импорте или запуске файла optimization_bot.py: {e}")
                try:
                    # В случае ошибки запускаем как подпроцесс
                    logger.info("Запуск optimization_bot.py через subprocess")
                    subprocess.run([sys.executable, "optimization_bot.py"])
                except Exception as sub_e:
                    logger.error(f"Ошибка при запуске subprocess: {sub_e}")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main() 