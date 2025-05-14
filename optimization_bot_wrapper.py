#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Обертка для запуска бота оптимизации с обработкой ошибок Anthropic API
"""

import os
import sys
import time
import logging
import importlib
import subprocess

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def patch_anthropic():
    """
    Применение патча для библиотеки Anthropic
    """
    logger.info("Проверка и патч библиотеки Anthropic")
    
    try:
        # Запускаем скрипт исправления
        subprocess.run([sys.executable, "fix_anthropic.py"], 
                      check=True, stdout=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Ошибка при применении патча: {e}")
        return False

def monkey_patch_anthropic_module():
    """
    Применяет monkey patch к модулю anthropic напрямую
    """
    logger.info("Применение monkey patch к модулю anthropic")
    
    try:
        import anthropic
        
        # Проверяем версию библиотеки
        version = getattr(anthropic, "__version__", "unknown")
        logger.info(f"Версия библиотеки anthropic: {version}")
        
        if hasattr(anthropic, 'Anthropic'):
            # Сохраняем оригинальный класс
            original_anthropic = anthropic.Anthropic
            
            # Создаем патч для конструктора
            def patched_init(self, *args, **kwargs):
                # Удаляем проблемные аргументы
                if 'proxies' in kwargs:
                    del kwargs['proxies']
                    logger.info("Удален аргумент 'proxies' из инициализации Anthropic")
                
                # Вызываем оригинальный конструктор с отфильтрованными аргументами
                return original_anthropic.__init__(self, *args, **kwargs)
            
            # Применяем патч
            anthropic.Anthropic.__init__ = patched_init
            logger.info("Monkey patch успешно применен к конструктору Anthropic")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при применении monkey patch: {e}")
        return False

def main():
    """
    Основная функция запуска бота
    """
    logger.info("Запуск обертки для бота оптимизации")
    
    # Применяем патч к файлу бота
    patch_successful = patch_anthropic()
    if not patch_successful:
        logger.warning("Не удалось применить патч к файлу. Попытка monkey patching...")
        monkey_patch_successful = monkey_patch_anthropic_module()
        if not monkey_patch_successful:
            logger.error("Не удалось исправить библиотеку Anthropic. Продолжение с риском ошибки.")
    
    # Запускаем бота
    logger.info("Запуск бота оптимизации...")
    try:
        # Динамический импорт модуля бота
        spec = importlib.util.spec_from_file_location("optimization_bot", "optimization_bot.py")
        bot_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bot_module)
        
        # Запуск основной функции бота
        if hasattr(bot_module, 'main'):
            bot_module.main()
        else:
            logger.error("Функция main не найдена в модуле optimization_bot")
            return 1
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 