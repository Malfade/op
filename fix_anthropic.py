#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import importlib.metadata
import platform
import time

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

def run_command(command):
    """Запуск команды и вывод результата"""
    print(f"\n> {command}")
    
    try:
        # Запуск команды и ожидание завершения
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        # Вывод стандартного вывода
        if result.stdout:
            print(result.stdout)
        
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        print_error(f"Ошибка при выполнении команды: {e}")
        if e.stderr:
            print(e.stderr)
        
        return False, e.stderr

def get_current_anthropic_version():
    """Получение текущей версии библиотеки anthropic"""
    try:
        return importlib.metadata.version('anthropic')
    except importlib.metadata.PackageNotFoundError:
        return None

def check_pip_version():
    """Проверка версии pip"""
    success, output = run_command("pip --version")
    if not success:
        print_error("Не удалось определить версию pip. Пожалуйста, убедитесь, что pip установлен.")
        return False
    
    print_success("Версия pip определена успешно.")
    return True

def fix_anthropic_api():
    """Исправление проблем с API Anthropic"""
    print_header("Исправление проблем с API Anthropic")
    
    # Проверка текущей версии
    current_version = get_current_anthropic_version()
    print_info(f"Текущая версия библиотеки anthropic: {current_version or 'Не установлена'}")
    
    # Проверка pip
    if not check_pip_version():
        return False
    
    # Установка правильной версии библиотеки
    print_info("Устанавливаем версию 0.19.0 для использования нового API (messages.create)...")
    success, _ = run_command("pip install anthropic==0.19.0")
    
    if not success:
        print_error("Не удалось установить библиотеку anthropic версии 0.19.0.")
        return False
    
    print_success("Библиотека anthropic версии 0.19.0 успешно установлена.")
    
    # Обновление requirements.txt
    print_info("Обновление файла requirements.txt...")
    
    try:
        with open("requirements.txt", "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        with open("requirements.txt", "w", encoding="utf-8") as f:
            for line in lines:
                if line.strip().startswith("anthropic=="):
                    f.write("anthropic==0.19.0  # Версия для нового API (messages.create)\n")
                elif line.strip().startswith("# anthropic==") and "0.5.0" in line:
                    f.write("# anthropic==0.5.0  # Версия для старого API (completion)\n")
                else:
                    f.write(line)
        
        print_success("Файл requirements.txt обновлен.")
    except Exception as e:
        print_error(f"Не удалось обновить файл requirements.txt: {e}")
    
    # Проверка установленной версии
    new_version = get_current_anthropic_version()
    print_info(f"Установленная версия библиотеки anthropic: {new_version}")
    
    if new_version == "0.19.0":
        print_success("Версия библиотеки успешно обновлена.")
    else:
        print_error(f"Версия библиотеки ({new_version}) не соответствует требуемой (0.19.0).")
    
    # Запуск проверки API
    print_info("Запуск проверки API...")
    run_command("python check_anthropic.py")
    
    print_header("Исправление завершено")
    print_info("Теперь вы можете запустить бота командой:")
    print("> python optimization_bot.py")
    
    # Предложение перезапустить сервис
    restart = input("\nПерезапустить бота сейчас? (y/n): ")
    if restart.lower() == 'y':
        print_info("Запуск бота...")
        run_command("python optimization_bot.py")
    
    return True

if __name__ == "__main__":
    fix_anthropic_api() 