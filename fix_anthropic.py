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
            "            self.client = anthropic.Anthropic(api_key=api_key)\n"
            "        except TypeError:\n"
            "            # Более старая версия библиотеки может иметь другую сигнатуру\n"
            "            self.client = anthropic.Anthropic(api_key=api_key)\n"
            "            logger.info('Используется старая версия библиотеки Anthropic')"
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

if __name__ == "__main__":
    sys.exit(main()) 