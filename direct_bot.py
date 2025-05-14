#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Прямой запуск бота оптимизации с патчем Anthropic
"""

import sys
import os
import subprocess
import logging
import time
import requests

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Проверка наличия ключа API в переменных окружения 
api_key = os.environ.get('ANTHROPIC_API_KEY', '')
if not api_key:
    logger.warning("ВНИМАНИЕ: API ключ Anthropic (ANTHROPIC_API_KEY) не найден в переменных окружения!")
    logger.warning("Бот будет работать в режиме заглушек и не сможет генерировать оригинальные скрипты")
    logger.warning("Установите переменную окружения ANTHROPIC_API_KEY с вашим API ключом")
else:
    logger.info(f"API ключ Anthropic найден (длина: {len(api_key)} символов)")

# Функция для патчинга модуля anthropic
def patch_anthropic_module():
    """
    Патчит модуль anthropic для обеспечения совместимости с API Claude
    """
    try:
        import anthropic
        logger.info(f"Текущая версия модуля anthropic: {getattr(anthropic, '__version__', 'неизвестна')}")
        
        # Патчим класс Anthropic, если он существует
        if hasattr(anthropic, 'Anthropic'):
            # Сохраняем оригинальный класс для последующего использования
            anthropic._original_Anthropic = anthropic.Anthropic
            logger.info("Сохранен оригинальный класс Anthropic")
            
            # Сохраняем оригинальный метод __init__
            original_init = anthropic.Anthropic.__init__
            
            # Создаем простую обертку для исключения проблемных параметров
            def patched_anthropic_init(self, *args, **kwargs):
                # Удаляем проблемные параметры
                if 'proxies' in kwargs:
                    logger.info("Удален параметр 'proxies' при инициализации Anthropic")
                    kwargs_clean = kwargs.copy()
                    del kwargs_clean['proxies']
                else:
                    kwargs_clean = kwargs
                
                # Вызываем оригинальный метод инициализации
                return original_init(self, *args, **kwargs_clean)
            
            # Патчим метод __init__
            anthropic.Anthropic.__init__ = patched_anthropic_init
            logger.info("Метод __init__ класса Anthropic успешно патчен")
            
        return True
    except ImportError:
        logger.error("Ошибка импорта модуля anthropic")
        return False
    except Exception as e:
        logger.error(f"Ошибка при патчинге модуля anthropic: {e}")
        return False

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
    # Запускаем бот оптимизации с патчем
    logger.info("Запуск бота оптимизации с патчем")
    
    # Патчим модуль anthropic
    patch_result = patch_anthropic_module()
    logger.info(f"Результат патчинга модуля: {'успешно' if patch_result else 'неудачно'}")
    
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
        logger.error(f"Ошибка при импорте или запуске файла optimization_bot.py: {e}")
        try:
            # В случае ошибки запускаем как подпроцесс
            logger.info("Запуск optimization_bot.py через subprocess")
            subprocess.run([sys.executable, "optimization_bot.py"])
        except Exception as sub_e:
            logger.error(f"Ошибка при запуске subprocess: {sub_e}")

if __name__ == "__main__":
    main() 