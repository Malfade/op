#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для исправления проблем в боте оптимизации для Railway:
1. Исправление всех недопустимых escape-последовательностей в файле шаблона
2. Реализация проверки единственного экземпляра на основе файловой блокировки
"""

import os
import sys
import re
import time
import atexit
import platform

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

def fix_all_escape_sequences():
    """Исправление всех неправильных escape-последовательностей в файлах проекта"""
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
        
        # Ищем конкретную строку с template_files и Run-Optimizer.ps1
        template_pattern = r'(template_files\["Run-Optimizer\.ps1"\]\s*=\s*""".*?""")'
        
        def fix_template_string(match):
            """Исправляет все escape-последовательности в строковом шаблоне"""
            template_str = match.group(1)
            # Исправляем все проблемные escape-последовательности
            fixed_str = template_str.replace(r'\\\W', r'\\\\W')
            fixed_str = fixed_str.replace(r'\A', r'\\A')
            fixed_str = fixed_str.replace(r'\B', r'\\B')
            fixed_str = fixed_str.replace(r'\D', r'\\D')
            fixed_str = fixed_str.replace(r'\S', r'\\S')
            fixed_str = fixed_str.replace(r'\Z', r'\\Z')
            fixed_str = fixed_str.replace(r'\$', r'\\$')
            # Исключаем правильные escape-последовательности
            return fixed_str
        
        # Применяем исправления к конкретному шаблону
        modified_content = re.sub(template_pattern, fix_template_string, content, flags=re.DOTALL)
        
        # Также исправляем все тройные кавычки в файле
        string_template_pattern = r'"""(.*?)"""'
        
        def fix_triple_quote_string(match):
            """Исправляет escape-последовательности в строках с тройными кавычками"""
            template_content = match.group(1)
            
            # Исправляем все проблемные escape-последовательности
            template_content = template_content.replace(r'\\\W', r'\\\\W')
            template_content = template_content.replace(r'\A', r'\\A')
            template_content = template_content.replace(r'\B', r'\\B')
            template_content = template_content.replace(r'\D', r'\\D')
            template_content = template_content.replace(r'\S', r'\\S')
            template_content = template_content.replace(r'\Z', r'\\Z')
            template_content = template_content.replace(r'\$', r'\\$')
            
            # Не трогаем правильные escape-последовательности
            # (исключаем \n, \t, \r, и т.д.)
            
            return '"""' + template_content + '"""'
        
        # Применяем исправления ко всем строкам в тройных кавычках
        modified_content = re.sub(string_template_pattern, 
                                 fix_triple_quote_string, 
                                 modified_content, 
                                 flags=re.DOTALL)
        
        # Исправляем проблему и в текущем скрипте
        current_script = os.path.basename(__file__)
        if os.path.exists(current_script):
            with open(current_script, "r", encoding="utf-8") as f:
                script_content = f.read()
            
            # Исправляем escape-последовательности в документации
            script_content = script_content.replace(r'\\\W', r'\\\\W')
            
            with open(current_script, "w", encoding="utf-8") as f:
                f.write(script_content)
            
            print_success(f"Исправлены escape-последовательности в текущем скрипте {current_script}")
        
        # Сохраняем изменения в файле бота
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

def implement_cross_platform_lock():
    """Добавление кросс-платформенной проверки на запуск единственного экземпляра бота"""
    print_header("Добавление проверки единственного экземпляра (кросс-платформенная)")
    
    # Путь к файлу бота
    bot_file = 'bot_optimixation/optimization_bot.py'
    if not os.path.exists(bot_file):
        print_error(f"Файл {bot_file} не найден!")
        return False
    
    print_info(f"Обрабатываю файл: {bot_file}")
    
    try:
        with open(bot_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Удаляем предыдущую реализацию socket или file-based блокировки, если она есть
        if "def ensure_single_instance():" in content:
            # Удаляем старую функцию
            old_function_pattern = r'# Проверка на запуск только одного экземпляра бота.*?def ensure_single_instance\(\):.*?return False\s*\}'
            content = re.sub(old_function_pattern, '', content, flags=re.DOTALL)
            print_info("Удалена предыдущая реализация проверки единственного экземпляра")
            
            # Удаляем импорт socket и fcntl, если они не используются в другом месте
            if "import socket" in content and "socket." not in content.replace("single_instance_socket", ""):
                content = content.replace("import socket\n", "")
            if "import fcntl" in content and "fcntl." not in content.replace("fcntl.flock", ""):
                content = content.replace("import fcntl\n", "")
            
        # Добавляем новую кросс-платформенную функцию проверки единственного экземпляра
        cross_platform_lock_code = '''
# Проверка на запуск только одного экземпляра бота - кросс-платформенная реализация
def ensure_single_instance():
    """
    Гарантирует запуск только одного экземпляра бота.
    Работает на Windows, Linux и MacOS.
    """
    try:
        # Определяем путь к файлу блокировки
        lock_dir = os.path.dirname(os.path.abspath(__file__))
        lock_file_path = os.path.join(lock_dir, "bot.lock")
        
        # Глобальный объект блокировки
        global lock_handle
        
        # Проверяем, существует ли файл блокировки
        if os.path.exists(lock_file_path):
            # Проверяем, жив ли процесс, который создал файл
            try:
                with open(lock_file_path, 'r') as f:
                    pid = int(f.read().strip())
                
                # Проверка существования процесса (кросс-платформенно)
                if platform.system() == 'Windows':
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    SYNCHRONIZE = 0x00100000
                    process = kernel32.OpenProcess(SYNCHRONIZE, False, pid)
                    if process:
                        kernel32.CloseHandle(process)
                        # Процесс существует, значит бот уже запущен
                        logger.error(f"Бот уже запущен (PID: {pid}). Завершаем работу.")
                        return False
                else:  # Linux/MacOS
                    import os
                    try:
                        # Отправляем сигнал 0 процессу - не убивает его,
                        # но генерирует ошибку, если процесс не существует
                        os.kill(pid, 0)
                        # Процесс существует, значит бот уже запущен
                        logger.error(f"Бот уже запущен (PID: {pid}). Завершаем работу.")
                        return False
                    except OSError:
                        # Процесс не существует
                        pass
            except (ValueError, IOError):
                # Некорректный PID или не удалось прочитать файл
                pass
            
            # Если мы здесь, значит процесс не существует или файл поврежден
            # Удаляем старый файл блокировки
            try:
                os.remove(lock_file_path)
                logger.info(f"Удален старый файл блокировки (PID не существует)")
            except OSError:
                pass
        
        # Создаем новый файл блокировки
        try:
            with open(lock_file_path, 'w') as f:
                f.write(str(os.getpid()))
            logger.info(f"Бот запущен в единственном экземпляре (PID: {os.getpid()})")
            
            # Регистрируем функцию для очистки при завершении
            def cleanup_lock():
                try:
                    if os.path.exists(lock_file_path):
                        os.remove(lock_file_path)
                        logger.info("Файл блокировки удален, бот завершает работу")
                except Exception as e:
                    logger.error(f"Ошибка при удалении файла блокировки: {e}")
            
            atexit.register(cleanup_lock)
            return True
        except Exception as e:
            logger.error(f"Не удалось создать файл блокировки: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при проверке единственного экземпляра: {e}")
        return False
'''
        
        # Находим место для вставки функции - после импортов, но до определения класса
        import_pattern = r'(import\s+.*?\n\n)'
        modified_content = re.sub(import_pattern, r'\1' + cross_platform_lock_code + '\n', content, count=1, flags=re.DOTALL)
        
        # Проверяем, была ли вставка, если нет - добавляем в другое место
        if modified_content == content:
            # Вставляем перед функцией main
            main_pattern = r'(def main\(\):)'
            modified_content = re.sub(main_pattern, cross_platform_lock_code + '\n\n' + r'\1', content, count=1)
        
        # Импортируем необходимые модули, если их еще нет
        if "import platform" not in modified_content:
            modified_content = modified_content.replace("import os", "import os\nimport platform")
        if "import atexit" not in modified_content:
            modified_content = modified_content.replace("import platform", "import platform\nimport atexit")
        
        # Добавляем инициализацию глобальных переменных
        if "lock_handle = None" not in modified_content:
            # Добавляем инициализацию после импортов
            init_code = "\n# Глобальная переменная для блокировки\nlock_handle = None\n"
            modified_content = re.sub(r'(import.*?\n\n)', r'\1' + init_code, modified_content, count=1, flags=re.DOTALL)
        
        # Добавляем вызов функции в начало функции main
        if "def main():" in modified_content:
            # Обновляем вызов в функции main
            main_function_pattern = r'def main\(\):\s*"""[^"]*"""\s*try:\s*'
            main_function_replacement = r'def main():\n    """Запуск бота"""\n    try:\n        # Проверяем, не запущен ли уже бот\n        if not ensure_single_instance():\n            logger.error("Завершаем работу из-за уже запущенного экземпляра")\n            return\n        \n        '
            
            modified_content = re.sub(main_function_pattern, main_function_replacement, modified_content)
        
        # Сохраняем изменения
        with open(bot_file, "w", encoding="utf-8") as f:
            f.write(modified_content)
        
        print_success("Добавлена кросс-платформенная проверка единственного экземпляра")
        
        return True
    
    except Exception as e:
        print_error(f"Ошибка при добавлении проверки единственного экземпляра: {str(e)}")
        return False

def main():
    """Основная функция"""
    print_header("Исправление проблем бота оптимизации для Railway")
    
    # Исправляем все escape-последовательности
    escape_fixed = fix_all_escape_sequences()
    
    # Добавляем кросс-платформенную проверку единственного экземпляра
    instance_fixed = implement_cross_platform_lock()
    
    if escape_fixed and instance_fixed:
        print_success("Все проблемы успешно исправлены!")
    else:
        print_error("Не удалось исправить все проблемы, проверьте логи выше.")
    
    print_info("Для запуска бота выполните:")
    print("> python -m bot_optimixation.optimization_bot")

if __name__ == "__main__":
    main() 