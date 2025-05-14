#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Патч для исправления инициализации клиента Anthropic
"""

import sys
import os
import importlib.util
import logging
import subprocess
import re

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """
    Основная функция для исправления интеграции с Anthropic API
    """
    print("Исправление модуля Anthropic API...")
    
    # Получаем версию anthropic
    anthropic_version = get_current_anthropic_version()
    print(f"Текущая версия anthropic: {anthropic_version}")
    
    # Проверяем содержимое модуля optimization_bot.py
    bot_file = "optimization_bot.py"
    if not os.path.exists(bot_file):
        print(f"Ошибка: файл {bot_file} не найден")
        return 1
    
    with open(bot_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Заменяем инициализацию клиента
    if "self.client = anthropic.Anthropic(api_key=api_key)" in content:
        new_content = content.replace(
            "self.client = anthropic.Anthropic(api_key=api_key)",
            "# Исправленная инициализация для совместимости с разными версиями библиотеки\n"
            "        try:\n"
            "            import anthropic.resources\n"
            "            # Проверяем версию библиотеки\n"
            "            if hasattr(anthropic, '__version__') and anthropic.__version__.startswith('0.'):\n"
            "                # Используем совместимый способ для старых версий\n"
            "                self.client = anthropic\n"
            "                self.client.api_key = api_key\n"
            "                logger.info('Используется совместимая инициализация клиента Anthropic для версии < 1.0.0')\n"
            "            else:\n"
            "                self.client = anthropic.Anthropic(api_key=api_key)\n"
            "        except TypeError as e:\n"
            "            # Проверяем тип ошибки\n"
            "            if 'proxies' in str(e):\n"
            "                # Проблема с параметром proxies\n"
            "                self.client = anthropic\n"
            "                self.client.api_key = api_key\n"
            "                logger.info(f'Используется альтернативная инициализация Anthropic из-за ошибки: {e}')\n"
            "            else:\n"
            "                # Неизвестная ошибка - пробрасываем исключение\n"
            "                raise"
        )
        
        # Записываем изменения
        with open(bot_file, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Файл {bot_file} успешно модифицирован")
        return 0
    else:
        print(f"Не удалось найти строку инициализации клиента в файле {bot_file}")
        return 1

def get_current_anthropic_version():
    """
    Получение текущей версии библиотеки anthropic
    """
    try:
        import anthropic
        return anthropic.__version__
    except (ImportError, AttributeError):
        # Если не удалось импортировать модуль или получить версию
        try:
            result = subprocess.run([sys.executable, "-m", "pip", "show", "anthropic"], 
                                    capture_output=True, text=True, check=True)
            for line in result.stdout.split('\n'):
                if line.startswith('Version:'):
                    return line.split(':', 1)[1].strip()
            return "неизвестно"
        except subprocess.SubprocessError:
            return "неизвестно"

def fix_optimization_bot():
    """Исправляет инициализацию клиента Anthropic в файле optimization_bot.py"""
    try:
        bot_file = "optimization_bot.py"
        if not os.path.exists(bot_file):
            logger.error(f"Файл {bot_file} не найден")
            return False
        
        # Читаем содержимое файла
        with open(bot_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Ищем блок инициализации клиента
        pattern = r'def create_safe_anthropic_client\(api_key\):[\s\S]+?client = anthropic\.Anthropic\([^)]*\)[\s\S]+?return client[\s\S]+?raise'
        
        # Новая функция с безопасной инициализацией
        new_func = """def create_safe_anthropic_client(api_key):
    \"""
    Создает клиент Anthropic с безопасными параметрами
    \"""
    try:
        if not api_key:
            raise ValueError("API ключ не может быть пустым")
        
        # Импортируем антропик заново для чистой инициализации
        import importlib
        import sys
        
        # Удаляем модуль из sys.modules если он там есть
        if 'anthropic' in sys.modules:
            del sys.modules['anthropic']
        
        # Импортируем модуль заново
        anthropic = importlib.import_module('anthropic')
        
        # Создаем клиент только с безопасными параметрами
        client = anthropic.Anthropic(api_key=api_key)
        
        logger.info("Клиент Anthropic успешно инициализирован")
        return client
        
    except Exception as e:
        logger.error(f"Ошибка при инициализации клиента Anthropic: {e}")
        raise"""
        
        # Заменяем блок инициализации
        modified_content = re.sub(pattern, new_func, content, flags=re.DOTALL)
        
        # Если замена не произошла, выводим сообщение
        if modified_content == content:
            logger.warning("Блок инициализации клиента не найден")
            return False
        
        # Записываем изменения
        with open(bot_file, "w", encoding="utf-8") as f:
            f.write(modified_content)
        
        logger.info(f"Файл {bot_file} успешно обновлен")
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при обновлении файла: {e}")
        return False

if __name__ == "__main__":
    if fix_optimization_bot():
        logger.info("Патч успешно применен")
        sys.exit(0)
    else:
        logger.error("Ошибка при применении патча")
        sys.exit(1) 