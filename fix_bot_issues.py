#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для исправления проблем в боте оптимизации:
1. Недопустимая escape-последовательность '\W' в файле шаблона
2. Конфликт запуска нескольких экземпляров бота
"""

import os
import sys
import re
import socket
import time
import atexit

def print_header(text):
    """Печать заголовка"""
    print("\n" + "=" * 60)
    print(f" {text} ".center(60))
    print("=" * 60)

def print_success(text):
    """Печать сообщения об успехе"""
    print(f"\n✅ {text}")

def print_error(text):
    """Печать сообщения об ошибке"""
    print(f"\n❌ {text}")

def print_info(text):
    """Печать информационного сообщения"""
    print(f"\nℹ️ {text}")

def fix_escape_sequences():
    """Исправление неправильных escape-последовательностей в шаблонах скриптов"""
    print_header("Исправление escape-последовательностей")
    
    # Проверяем наличие директории bot_optimixation
    if not os.path.exists('bot_optimixation'):
        print_error("Директория bot_optimixation не найдена!")
        return False
    
    # Путь к файлу бота
    bot_file = 'bot_optimixation/optimization_bot.py'
    if not os.path.exists(bot_file):
        print_error(f"Файл {bot_file} не найден!")
        return False
    
    print_info(f"Обрабатываю файл: {bot_file}")
    
    try:
        with open(bot_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Ищем неправильные escape-последовательности в шаблонах строк
        # Заменяем одиночные слеши перед W на двойные - проблема из лога
        modified_content = content.replace(r'\W', r'\\W')
        
        # Также проверяем и исправляем другие обычные escape-последовательности, 
        # которые могут быть неправильными в строках с тройными кавычками
        patterns_to_fix = [
            (r'\\\\', r'\\\\'),  # Уже правильные - оставляем как есть
            (r'([^\\])\\([^\\nrtbfv"\'])', r'\1\\\\\2'),  # Одиночные слеши перед обычными символами
            (r'\\\\n', r'\\n'),  # Исправляем случаи с двойным экранированием \n
            (r'\\\\r', r'\\r'),  # Исправляем случаи с двойным экранированием \r
            (r'\\\\t', r'\\t'),  # Исправляем случаи с двойным экранированием \t
        ]
        
        # Применяем паттерны только к строковым шаблонам в тройных кавычках
        # Это позволит избежать повреждения кода вне строковых литералов
        string_template_pattern = r'"""(.*?)"""'
        
        def fix_escapes_in_match(match):
            template_content = match.group(1)
            for pattern, replacement in patterns_to_fix:
                template_content = re.sub(pattern, replacement, template_content)
            return '"""' + template_content + '"""'
        
        # Применяем исправления ко всем строкам в тройных кавычках
        modified_content = re.sub(string_template_pattern, 
                                 fix_escapes_in_match, 
                                 modified_content, 
                                 flags=re.DOTALL)
        
        # Сохраняем изменения
        if modified_content != content:
            with open(bot_file, "w", encoding="utf-8") as f:
                f.write(modified_content)
            print_success(f"Исправлены escape-последовательности в файле {bot_file}")
        else:
            print_info(f"Не найдены escape-последовательности для исправления в {bot_file}")
            
        return True
    
    except Exception as e:
        print_error(f"Ошибка при обработке файла: {str(e)}")
        return False

def add_single_instance_check():
    """Добавление проверки на запуск единственного экземпляра бота"""
    print_header("Добавление проверки единственного экземпляра")
    
    # Путь к файлу бота
    bot_file = 'bot_optimixation/optimization_bot.py'
    if not os.path.exists(bot_file):
        print_error(f"Файл {bot_file} не найден!")
        return False
    
    print_info(f"Обрабатываю файл: {bot_file}")
    
    try:
        with open(bot_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Проверяем, есть ли уже функция для проверки единственного экземпляра
        if "def ensure_single_instance():" in content:
            print_info("Функция проверки единственного экземпляра уже существует")
        else:
            # Добавляем функцию проверки единственного экземпляра
            single_instance_code = '''
# Проверка на запуск только одного экземпляра бота
def ensure_single_instance():
    """
    Гарантирует запуск только одного экземпляра бота,
    используя блокировку сокета.
    """
    try:
        # Создаем глобальный сокет для проверки запуска
        global single_instance_socket
        single_instance_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Пытаемся связать сокет с портом
        # Если порт уже используется, значит уже запущен экземпляр бота
        try:
            single_instance_socket.bind(('localhost', 49152))
            logger.info("Бот запущен в единственном экземпляре")
            
            # Регистрируем функцию для закрытия сокета при завершении
            atexit.register(lambda: single_instance_socket.close())
            return True
        except socket.error:
            logger.error("Бот уже запущен! Завершаем работу.")
            return False
    except Exception as e:
        logger.error(f"Ошибка при проверке единственного экземпляра: {e}")
        return False
'''
            
            # Находим место для вставки функции - после импортов, но до определения класса
            import_pattern = r'(import\s+.*?\n\n)'
            modified_content = re.sub(import_pattern, r'\1' + single_instance_code + '\n', content, count=1, flags=re.DOTALL)
            
            # Проверяем, была ли вставка, если нет - добавляем в другое место
            if modified_content == content:
                # Вставляем перед функцией main
                main_pattern = r'(def main\(\):)'
                modified_content = re.sub(main_pattern, single_instance_code + '\n\n' + r'\1', content, count=1)
            
            # Импортируем необходимые модули, если их еще нет
            if "import socket" not in modified_content:
                modified_content = modified_content.replace("import os", "import os\nimport socket\nimport atexit")
            elif "import atexit" not in modified_content:
                modified_content = modified_content.replace("import socket", "import socket\nimport atexit")
            
            # Добавляем вызов функции в начало функции main
            if "def main():" in modified_content:
                # Вставляем проверку в функцию main
                main_function_pattern = r'def main\(\):\s*"""[^"]*"""\s*try:\s*'
                main_function_replacement = r'def main():\n    """Запуск бота"""\n    try:\n        # Проверяем, не запущен ли уже бот\n        if not ensure_single_instance():\n            logger.error("Завершаем работу из-за уже запущенного экземпляра")\n            return\n        \n        '
                
                modified_content = re.sub(main_function_pattern, main_function_replacement, modified_content)
            
            # Сохраняем изменения
            with open(bot_file, "w", encoding="utf-8") as f:
                f.write(modified_content)
            
            print_success("Добавлена проверка единственного экземпляра бота")
        
        return True
    
    except Exception as e:
        print_error(f"Ошибка при добавлении проверки единственного экземпляра: {str(e)}")
        return False

def main():
    """Основная функция"""
    print_header("Исправление проблем бота оптимизации")
    
    # Исправляем escape-последовательности
    escape_fixed = fix_escape_sequences()
    
    # Добавляем проверку единственного экземпляра
    instance_fixed = add_single_instance_check()
    
    if escape_fixed and instance_fixed:
        print_success("Все проблемы успешно исправлены!")
    else:
        print_error("Не удалось исправить все проблемы, проверьте логи выше.")
    
    print_info("Для запуска бота выполните:")
    print("> python -m bot_optimixation.optimization_bot")

if __name__ == "__main__":
    main() 