#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для безопасной фиксации проблемы инициализации клиента Anthropic
"""

import os
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_optimization_bot():
    """
    Модифицирует файл optimization_bot.py для предотвращения рекурсии 
    при инициализации клиента Anthropic
    """
    try:
        bot_file_path = "optimization_bot.py"
        
        if not os.path.exists(bot_file_path):
            logger.error(f"Файл {bot_file_path} не найден")
            return False
        
        logger.info(f"Чтение файла {bot_file_path}")
        
        # Чтение содержимого файла
        with open(bot_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Ищем строку инициализации клиента
        target_line = "self.client = anthropic.Anthropic(api_key=api_key)"
        if target_line in content:
            # Меняем строку на безопасную инициализацию
            new_content = content.replace(
                target_line,
                "try:\n"
                "                self.client = anthropic.Anthropic(api_key=api_key)\n"
                "            except Exception as e:\n"
                "                logger.warning(f\"Ошибка при стандартной инициализации Anthropic: {e}\")\n"
                "                # Импортируем антропик заново, чтобы избежать рекурсии\n"
                "                import importlib\n"
                "                anthropic_module = importlib.import_module('anthropic')\n"
                "                # Создаем экземпляр напрямую, минуя патченный метод\n"
                "                self.client = anthropic_module._original_Anthropic(api_key=api_key)"
            )
            
            # Сохраняем модифицированный файл
            with open(bot_file_path, 'w', encoding='utf-8') as file:
                file.write(new_content)
            
            logger.info(f"Файл {bot_file_path} успешно модифицирован")
            return True
        else:
            logger.warning(f"Строка инициализации клиента не найдена в файле {bot_file_path}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при модификации файла: {e}")
        return False

if __name__ == "__main__":
    fix_optimization_bot() 