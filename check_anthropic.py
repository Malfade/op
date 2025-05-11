#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import json
import anthropic
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Получение API ключа из .env
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

if not ANTHROPIC_API_KEY:
    print("Ошибка: API ключ Anthropic не найден в файле .env")
    print("Пожалуйста, добавьте ANTHROPIC_API_KEY в файл .env")
    sys.exit(1)

def check_anthropic_api():
    """Проверка работоспособности API Anthropic"""
    print("Проверка подключения к API Anthropic...")
    
    try:
        # Инициализация клиента
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        
        # Проверка версии библиотеки
        print(f"Используется версия библиотеки anthropic: {anthropic.__version__}")
        
        # Определяем, какие методы доступны в объекте client
        print("\nПроверка доступных методов API:")
        has_messages = hasattr(client, 'messages')
        has_completion = hasattr(client, 'completion')
        
        print(f"- client.messages: {'Доступен ✅' if has_messages else 'Недоступен ❌'}")
        print(f"- client.completion: {'Доступен ✅' if has_completion else 'Недоступен ❌'}")
        
        # Тестовый запрос с использованием доступного метода
        print("\nПопытка выполнить тестовый запрос...")
        
        if has_messages:
            # Пробуем новый метод messages.create
            print("Используем метод messages.create (новый API)")
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=100,
                messages=[
                    {
                        "role": "user",
                        "content": "Привет, это тестовый запрос. Пожалуйста, ответь коротко."
                    }
                ]
            )
            print("\nОтвет от API:")
            print(response.content[0].text)
            print("\nПодключение к API Anthropic работает корректно ✅")
            print("\nКонфигурация API верная. Бот настроен на использование НОВОГО API (messages.create).")
            print("Проверьте, что в файле optimization_bot.py используется messages.create, а не completion.")
            
        elif has_completion:
            # Пробуем старый метод completion
            print("Используем метод completion (старый API)")
            response = client.completion(
                prompt="Human: Привет, это тестовый запрос. Пожалуйста, ответь коротко.\n\nAssistant:",
                model="claude-3-5-sonnet-20240620",
                max_tokens_to_sample=100
            )
            print("\nОтвет от API:")
            print(response['completion'])
            print("\nПодключение к API Anthropic работает корректно ✅")
            print("\nВНИМАНИЕ: вы используете СТАРЫЙ API (completion), но код бота настроен на НОВЫЙ API (messages.create).")
            print("Установите anthropic==0.19.0 или измените код в файле optimization_bot.py для использования метода completion.")
            
        else:
            print("\nНе найдено подходящих методов для работы с API!")
            print("Ваша версия библиотеки anthropic может быть несовместима.")
            print(f"Текущая версия: {anthropic.__version__}")
            print("Рекомендуется обновить или понизить версию библиотеки:")
            print("  - Для нового API: pip install anthropic==0.19.0")
            print("  - Для старого API: pip install anthropic==0.5.0")
            
        return True
        
    except Exception as e:
        print(f"\nОшибка при подключении к API Anthropic: {str(e)}")
        print("\nПроверьте следующее:")
        print("1. Правильность API ключа в файле .env")
        print("2. Подключение к интернету")
        print("3. Несовместимость версии библиотеки anthropic:")
        print(f"   - Текущая версия: {anthropic.__version__}")
        print("   - Для старого API (метод completion): pip install anthropic==0.5.0")
        print("   - Для нового API (метод messages): pip install anthropic==0.19.0")
        print("4. Возможные ограничения сети или файрвола")
        
        print("\nДетали ошибки:")
        print(str(e))
        return False

if __name__ == "__main__":
    check_anthropic_api() 