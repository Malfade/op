#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для безопасной фиксации проблемы инициализации клиента Anthropic
"""

import os
import logging
import re

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_anthropic_initialization():
    try:
        # Проверяем существование файла
        if not os.path.exists('optimization_bot.py'):
            print("Ошибка: файл optimization_bot.py не найден")
            return False
            
        # Читаем содержимое файла
        with open('optimization_bot.py', 'r', encoding='utf-8') as f:
            content = f.read()
            print("Файл optimization_bot.py успешно прочитан")
            
        # Ищем строку инициализации клиента
        init_pattern = r'self\.client\s*=\s*anthropic\.Anthropic\(api_key=api_key\)'
        if not re.search(init_pattern, content):
            print("Ошибка: строка инициализации клиента не найдена")
            return False
            
        print("Найдена строка инициализации клиента Anthropic")
            
        # Заменяем строку на новую версию с проверкой
        new_init = '''try:
            if not api_key:
                raise ValueError("API ключ не может быть пустым")
            self.client = anthropic.Anthropic(api_key=api_key)
            logger.info("Клиент Anthropic успешно инициализирован")
        except Exception as e:
            logger.error(f"Ошибка при инициализации клиента Anthropic: {e}")
            raise'''
            
        # Выполняем замену с учетом отступов
        modified_content = re.sub(init_pattern, new_init.strip(), content)
            
        # Записываем обновленное содержимое
        with open('optimization_bot.py', 'w', encoding='utf-8') as f:
            f.write(modified_content)
            
        print("Файл optimization_bot.py успешно обновлен")
        return True
            
    except Exception as e:
        print(f"Произошла ошибка при обновлении файла: {e}")
        return False

if __name__ == '__main__':
    fix_anthropic_initialization() 