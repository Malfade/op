#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Скрипт для исправления ошибки инициализации клиента Anthropic
с неизвестным параметром 'proxies'
"""

import os
import sys
import importlib.metadata

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

def get_current_anthropic_version():
    """Получение текущей версии библиотеки anthropic"""
    try:
        return importlib.metadata.version('anthropic')
    except importlib.metadata.PackageNotFoundError:
        return None

def fix_proxy_issue():
    """Исправление проблемы с прокси в клиенте Anthropic"""
    print_header("Исправление проблемы с прокси в клиенте Anthropic")
    
    # Проверка текущей версии
    current_version = get_current_anthropic_version()
    print_info(f"Текущая версия библиотеки anthropic: {current_version or 'Не установлена'}")
    
    # Проверяем наличие файлов
    bot_files = [
        "optimization_bot.py",
        "bot_optimixation/optimization_bot.py"
    ]
    
    found_files = []
    for file_path in bot_files:
        if os.path.exists(file_path):
            found_files.append(file_path)
    
    if not found_files:
        print_error("Не найдены файлы с кодом бота!")
        return False
    
    print_info(f"Найдены файлы: {', '.join(found_files)}")
    
    # Исправляем файлы
    for file_path in found_files:
        print_info(f"Обрабатываю файл: {file_path}")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Ищем строки с созданием клиента Anthropic
            if "anthropic.Anthropic(" in content and "proxies" in content:
                print_info("Найдена инициализация с параметром proxies")
                
                # Заменяем строки с proxies на правильную инициализацию
                modified_content = content.replace(
                    "anthropic.Anthropic(api_key=api_key, proxies=proxies)",
                    "anthropic.Anthropic(api_key=api_key)"
                )
                
                modified_content = modified_content.replace(
                    "anthropic.Anthropic(api_key=self.api_key, proxies=proxies)",
                    "anthropic.Anthropic(api_key=self.api_key)"
                )
                
                # Другие возможные варианты
                modified_content = modified_content.replace(
                    "anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, proxies=proxies)",
                    "anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)"
                )
                
                # Если контент был изменен, сохраняем его
                if modified_content != content:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(modified_content)
                    print_success(f"Файл {file_path} исправлен!")
                else:
                    print_info(f"В файле {file_path} не найдены строки для исправления")
            else:
                print_info(f"В файле {file_path} не найдены проблемные строки с proxies")
        
        except Exception as e:
            print_error(f"Ошибка при обработке файла {file_path}: {e}")
    
    print_header("Исправление завершено")
    print_info("Теперь вы можете запустить бота командой:")
    print("> python optimization_bot.py")
    
    return True

if __name__ == "__main__":
    fix_proxy_issue() 