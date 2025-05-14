#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Прямой запуск бота оптимизации с патчем Anthropic
"""

import sys
import os
import subprocess
import logging
import time
import requests

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальная переменная для отслеживания состояния патча
ANTHROPIC_PATCHED = False

# Глобальная переменная для хранения экземпляра клиента
GLOBAL_ANTHROPIC_CLIENT = None

# Класс для мок-ответа с API, используемый глобально
class MockResponse:
    def __init__(self):
        class Content:
            def __init__(self):
                self.text = (
                    "К сожалению, не удалось подключиться к API. "
                    "В демонстрационных целях предоставлю скрипт-генератор для оптимизации Windows.\n\n"
                    "```batch\n"
                    "@echo off\n"
                    "echo Generating PowerShell optimizer script...\n\n"
                    "echo # Windows_Optimizer.ps1 > WindowsOptimizer.ps1\n"
                    "echo # Script for Windows optimization >> WindowsOptimizer.ps1\n"
                    "echo. >> WindowsOptimizer.ps1\n"
                    "echo # Check for administrator rights >> WindowsOptimizer.ps1\n"
                    "echo if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { >> WindowsOptimizer.ps1\n"
                    "echo     Write-Warning 'Please run this script as Administrator!' >> WindowsOptimizer.ps1\n"
                    "echo     break >> WindowsOptimizer.ps1\n"
                    "echo } >> WindowsOptimizer.ps1\n"
                    "echo. >> WindowsOptimizer.ps1\n"
                    "echo # Error handling >> WindowsOptimizer.ps1\n"
                    "echo try { >> WindowsOptimizer.ps1\n"
                    "echo     # Clean temporary files >> WindowsOptimizer.ps1\n"
                    "echo     Write-Host 'Cleaning temporary files...' -ForegroundColor Green >> WindowsOptimizer.ps1\n"
                    "echo     Remove-Item -Path $env:TEMP\\* -Force -Recurse -ErrorAction SilentlyContinue >> WindowsOptimizer.ps1\n"
                    "echo     Remove-Item -Path C:\\Windows\\Temp\\* -Force -Recurse -ErrorAction SilentlyContinue >> WindowsOptimizer.ps1\n"
                    "echo. >> WindowsOptimizer.ps1\n"
                    "echo     # Performance optimization >> WindowsOptimizer.ps1\n"
                    "echo     Write-Host 'Optimizing performance...' -ForegroundColor Green >> WindowsOptimizer.ps1\n"
                    "echo     powercfg -setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c # High Performance >> WindowsOptimizer.ps1\n"
                    "echo. >> WindowsOptimizer.ps1\n"
                    "echo     # Disable unnecessary services >> WindowsOptimizer.ps1\n"
                    "echo     Write-Host 'Disabling unnecessary services...' -ForegroundColor Green >> WindowsOptimizer.ps1\n"
                    "echo     Stop-Service -Name DiagTrack -Force -ErrorAction SilentlyContinue >> WindowsOptimizer.ps1\n"
                    "echo     Set-Service -Name DiagTrack -StartupType Disabled -ErrorAction SilentlyContinue >> WindowsOptimizer.ps1\n"
                    "echo. >> WindowsOptimizer.ps1\n"
                    "echo     Write-Host 'Optimization completed!' -ForegroundColor Green >> WindowsOptimizer.ps1\n"
                    "echo } catch { >> WindowsOptimizer.ps1\n"
                    "echo     Write-Warning \"An error occurred: $_\" >> WindowsOptimizer.ps1\n"
                    "echo } >> WindowsOptimizer.ps1\n\n"
                    "echo Creating optimized batch script...\n"
                    "echo @echo off > WindowsOptimizer.bat\n"
                    "echo echo Windows Optimizer Batch Script >> WindowsOptimizer.bat\n"
                    "echo echo ============================== >> WindowsOptimizer.bat\n"
                    "echo. >> WindowsOptimizer.bat\n"
                    "echo :: Check for administrator rights >> WindowsOptimizer.bat\n"
                    "echo net session ^>nul 2^>^&1 >> WindowsOptimizer.bat\n"
                    "echo if %%errorLevel%% neq 0 ( >> WindowsOptimizer.bat\n"
                    "echo     echo Please run this script as Administrator! >> WindowsOptimizer.bat\n"
                    "echo     pause >> WindowsOptimizer.bat\n"
                    "echo     exit >> WindowsOptimizer.bat\n"
                    "echo ) >> WindowsOptimizer.bat\n"
                    "echo. >> WindowsOptimizer.bat\n"
                    "echo echo Cleaning temporary files... >> WindowsOptimizer.bat\n"
                    "echo del /f /s /q %%temp%%\\*.* 2^>nul >> WindowsOptimizer.bat\n"
                    "echo del /f /s /q C:\\Windows\\Temp\\*.* 2^>nul >> WindowsOptimizer.bat\n"
                    "echo. >> WindowsOptimizer.bat\n"
                    "echo echo Optimization completed! >> WindowsOptimizer.bat\n"
                    "echo pause >> WindowsOptimizer.bat\n\n"
                    "echo Scripts generated successfully.\n"
                    "echo To run:\n"
                    "echo - WindowsOptimizer.bat for batch script\n"
                    "echo - powershell -ExecutionPolicy Bypass -NoProfile -File \"WindowsOptimizer.ps1\" for PowerShell script\n\n"
                    "echo Starting Windows optimization script...\n"
                    "echo ==========================================\n"
                    "powershell -ExecutionPolicy Bypass -NoProfile -File \"WindowsOptimizer.ps1\"\n"
                    "echo ==========================================\n"
                    "echo Optimization script completed.\n"
                    "pause\n"
                    "```\n\n"
                    "Этот скрипт решает проблемы с кодировкой, генерируя корректные PowerShell и Batch скрипты. Просто сохраните его как `generate_script.bat` и запустите."
                )
        
        self.content = [Content()]

def patch_anthropic_module():
    """
    Патчит модуль anthropic, добавляя необходимые методы
    """
    global ANTHROPIC_PATCHED
    
    # Если модуль уже патчен, просто возвращаем True
    if ANTHROPIC_PATCHED:
        logger.info("Модуль anthropic уже был патчен ранее")
        return True
        
    try:
        import anthropic
        import importlib.util
        
        logger.info(f"Текущая версия модуля anthropic: {getattr(anthropic, '__version__', 'неизвестна')}")
        
        # Класс обертки для совместимости с разными версиями Anthropic API
        class CompatAnthropicWrapper:
            def __init__(self, *args, **kwargs):
                """
                Обертка для инициализации клиента Anthropic с разными версиями API
                """
                # Проверяем, существует ли уже глобальный экземпляр
                if 'GLOBAL_ANTHROPIC_CLIENT' in globals() and GLOBAL_ANTHROPIC_CLIENT is not None:
                    self._client = GLOBAL_ANTHROPIC_CLIENT
                    logger.info("Использован существующий глобальный экземпляр клиента Anthropic")
                    return
                
                self._api_key = kwargs.get('api_key', os.environ.get('ANTHROPIC_API_KEY', ''))
                
                # Сохраняем аргументы для последующей инициализации
                self._args = args
                self._kwargs = kwargs
                
                # Создаем поле для хранения фактического клиента
                self._client = None
                self._messages = None
                
                logger.info("Инициализирована обертка для Anthropic API")
                
                # Пробуем инициализировать клиент
                self._try_init_client()
                
                # Сохраняем экземпляр клиента глобально
                if self._client is not None:
                    GLOBAL_ANTHROPIC_CLIENT = self._client
            
            def _try_init_client(self):
                """
                Пытается инициализировать клиент с разными версиями API
                """
                # Проверяем, существует ли уже глобальный экземпляр
                if 'GLOBAL_ANTHROPIC_CLIENT' in globals() and GLOBAL_ANTHROPIC_CLIENT is not None:
                    self._client = GLOBAL_ANTHROPIC_CLIENT
                    logger.info("Использован существующий глобальный экземпляр клиента Anthropic")
                    return
                
                try:
                    # Пробуем инициализировать клиент напрямую
                    import anthropic
                    # Сохраняем ссылку на оригинальный класс перед патчем
                    if hasattr(anthropic, '_original_Anthropic'):
                        original_class = anthropic._original_Anthropic
                        self._client = original_class(*self._args, **self._kwargs)
                        logger.info("Успешно инициализирован клиент Anthropic API с использованием оригинального класса")
                    else:
                        logger.warning("Оригинальный класс Anthropic не найден, использую шаблонный ответ")
                        self._client = None
                except Exception as e:
                    logger.warning(f"Не удалось инициализировать клиент Anthropic API: {e}")
                    self._client = None
            
            def __getattr__(self, name):
                """
                Прокси для методов клиента Anthropic API
                """
                # Избегаем рекурсии при запросе стандартных атрибутов
                if name.startswith('_'):
                    raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
                
                if name == 'messages':
                    if self._messages is None:
                        self._messages = MockResponse()
                    return self._messages
                
                if self._client is None:
                    # Попытка повторной инициализации только один раз
                    if not hasattr(self, '_init_tried'):
                        self._init_tried = True
                        self._try_init_client()
                
                if self._client is not None:
                    return getattr(self._client, name)
                
                # Для нестандартных атрибутов возвращаем MockResponse вместо self
                logger.warning(f"Запрошен отсутствующий атрибут: {name}, возвращаем Mock")
                return MockResponse()
            
            def __call__(self, *args, **kwargs):
                """
                Прокси для вызовов клиента Anthropic API
                """
                if self._client is None:
                    # Возвращаем шаблонный ответ
                    return MockResponse()
                
                # Вызов метода оригинального клиента
                try:
                    return self._client(*args, **kwargs)
                except Exception as e:
                    logger.error(f"Ошибка вызова метода клиента Anthropic API: {e}")
                    # Возвращаем шаблонный ответ в случае ошибки
                    return MockResponse()
        
        # Проверяем и заменяем оригинальный класс
        if hasattr(anthropic, 'Anthropic'):
            # Сохраняем оригинальный класс
            original_Anthropic = anthropic.Anthropic
            # Сохраняем ссылку на оригинальный класс для использования в _try_init_client
            anthropic._original_Anthropic = original_Anthropic
            
            # Заменяем класс Anthropic на нашу обертку
            anthropic.Anthropic = CompatAnthropicWrapper
            
            # Проверяем, есть ли у модуля атрибут "messages"
            if not hasattr(anthropic, 'messages'):
                # Добавляем метод "messages" к модулю
                anthropic.messages = MockResponse()
            
            logger.info("Модуль anthropic успешно патчен: класс Anthropic заменен на CompatAnthropicWrapper")
            ANTHROPIC_PATCHED = True
            return True
        else:
            logger.warning("Модуль anthropic не содержит класса Anthropic, патч не применен")
            return False
            
    except ImportError:
        logger.error("Не удалось импортировать модуль anthropic")
        return False
    except Exception as e:
        logger.error(f"Ошибка при патчинге модуля anthropic: {e}")
        return False

def modify_bot_file():
    """
    Модификация файла бота для использования патченного anthropic
    """
    try:
        bot_file_path = "optimization_bot.py"
        
        # Проверяем, существует ли файл бота
        if not os.path.exists(bot_file_path):
            logger.error(f"Файл бота {bot_file_path} не найден")
            return False
        
        logger.info(f"Открываю файл бота {bot_file_path} для модификации")
        
        # Чтение содержимого файла
        with open(bot_file_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Модификации для улучшения устойчивости бота
        # 1. Добавляем обработку ошибок при запуске бота
        if "bot.infinity_polling(" in content and "except Exception as e:" not in content:
            # Заменяем стандартный метод запуска на более надежный с обработкой ошибок
            replacement = """
        # Добавляем задержку перед запуском для стабилизации соединения
        logger.info("Ожидание 5 секунд перед запуском infinity_polling...")
        time.sleep(5)
        
        # Запуск бота с использованием infinity_polling (более стабильный метод)
        try:
            logger.info("Запуск бота с использованием infinity_polling")
            bot.infinity_polling(timeout=30, long_polling_timeout=15)
        except Exception as e:
            if "409" in str(e):
                # В случае конфликта сессий делаем более долгую паузу
                logger.warning(f"Обнаружен конфликт сессий (409): {e}")
                logger.info("Ожидание 30 секунд для сброса сессий Telegram...")
                time.sleep(30)
                logger.info("Повторный запуск бота после сброса сессий")
                bot.infinity_polling(timeout=60, long_polling_timeout=30)
            else:
                logger.error(f"Ошибка при запуске бота: {e}")
                raise"""
            
            # Заменяем строку запуска бота
            content = content.replace("bot.infinity_polling(", "# bot.infinity_polling(")
            
            # Находим позицию для вставки нового кода
            insert_pos = content.find("if __name__ == \"__main__\":")
            if insert_pos > 0:
                # Находим начало функции main()
                main_pos = content.find("def main():", insert_pos)
                if main_pos > 0:
                    # Находим конец функции main()
                    main_end = content.find("if __name__ == \"__main__\":", main_pos)
                    if main_end > 0:
                        # Вставляем наш код перед return или в конец функции
                        return_pos = content.rfind("return", main_pos, main_end)
                        if return_pos > 0:
                            content = content[:return_pos] + replacement + "\n        " + content[return_pos:]
                        else:
                            # Если return не найден, добавляем перед концом функции
                            content = content[:main_end] + replacement + "\n    " + content[main_end:]
            
            logger.info("Добавлена обработка ошибок при запуске бота")
        
        # Сохраняем измененный файл
        with open(bot_file_path, 'w', encoding='utf-8') as file:
            file.write(content)
        
        logger.info(f"Файл бота {bot_file_path} успешно модифицирован")
        return True
    
    except Exception as e:
        logger.error(f"Ошибка при модификации файла бота: {e}")
        return False

def main():
    """
    Запуск бота с патчем
    """
    logger.info("Запуск бота оптимизации с патчем")
    
    # Патчим модуль anthropic
    patch_success = patch_anthropic_module()
    logger.info(f"Результат патчинга модуля: {'успешно' if patch_success else 'неудачно'}")
    
    # Модифицируем файл бота
    file_mod_success = modify_bot_file()
    logger.info(f"Результат модификации файла: {'успешно' if file_mod_success else 'неудачно'}")
    
    # Делаем паузу перед запуском для стабилизации системы
    logger.info("Ожидание 10 секунд перед запуском бота...")
    time.sleep(10)
    
    # Проверяем наличие активных подключений к Telegram API
    # и сбрасываем текущее соединение при необходимости
    try:
        import requests
        telegram_token = os.environ.get('TELEGRAM_TOKEN')
        if telegram_token:
            # Попытка сбросить вебхуки, если они используются
            logger.info("Попытка сброса вебхуков Telegram...")
            requests.get(f'https://api.telegram.org/bot{telegram_token}/deleteWebhook?drop_pending_updates=true')
            time.sleep(2)
            # Получаем информацию о боте для проверки соединения
            response = requests.get(f'https://api.telegram.org/bot{telegram_token}/getMe')
            if response.status_code == 200:
                logger.info(f"Соединение с Telegram API установлено. Бот: {response.json().get('result', {}).get('username')}")
            else:
                logger.warning(f"Проблема с Telegram API: {response.status_code}, {response.text}")
    except Exception as e:
        logger.warning(f"Не удалось проверить соединение с Telegram API: {e}")
    
    # Импортируем все необходимые классы перед модификацией OptimizationBot
    try:
        # Импортируем все необходимые классы один раз в начале
        imported_classes = {}
        
        # Импортируем сначала необходимые классы
        try:
            from script_validator import ScriptValidator
            imported_classes['ScriptValidator'] = ScriptValidator
        except ImportError:
            logger.warning("Не удалось импортировать ScriptValidator")
        
        try:
            from script_metrics import ScriptMetrics
            imported_classes['ScriptMetrics'] = ScriptMetrics
        except ImportError:
            logger.warning("Не удалось импортировать ScriptMetrics")
        
        try:
            from prompt_optimizer import PromptOptimizer
            imported_classes['PromptOptimizer'] = PromptOptimizer
        except ImportError:
            logger.warning("Не удалось импортировать PromptOptimizer")
        
        # Импортируем модуль optimization_bot
        from optimization_bot import OptimizationBot
        
        # Переопределяем метод __init__ для использования нашего патча
        original_init = OptimizationBot.__init__
        
        def patched_init(self, api_key, validator=None):
            """Патченный метод инициализации, который использует наш обертку Anthropic"""
            import anthropic
            self.api_key = api_key
            
            # Используем импортированные классы из словаря
            self.validator = validator or imported_classes.get('ScriptValidator', lambda: None)()
            self.metrics = imported_classes.get('ScriptMetrics', lambda: None)()
            
            # Создаем prompt_optimizer только если есть ScriptMetrics
            if 'PromptOptimizer' in imported_classes and self.metrics is not None:
                self.prompt_optimizer = imported_classes['PromptOptimizer'](metrics=self.metrics)
                self.prompts = self.prompt_optimizer.get_optimized_prompts()
            else:
                self.prompt_optimizer = None
                self.prompts = {}
            
            # Используем патченную версию Anthropic
            logger.info("Инициализация OptimizationBot с патченной версией Anthropic")
            
            # Проверяем, есть ли глобальный экземпляр клиента
            if 'GLOBAL_ANTHROPIC_CLIENT' in globals() and GLOBAL_ANTHROPIC_CLIENT is not None:
                self.client = anthropic.Anthropic(api_key=api_key)  # При вызове вернется существующий экземпляр
                logger.info("Использован существующий глобальный экземпляр клиента Anthropic")
            else:
                try:
                    # Используем клиент непосредственно без повторной инициализации обертки
                    if hasattr(anthropic, '_original_Anthropic'):
                        # Нет необходимости создавать обертку снова, так как она уже создана
                        # и заменила собой класс Anthropic
                        self.client = anthropic.Anthropic(api_key=api_key)
                        logger.info("Успешно создан экземпляр патченного клиента Anthropic")
                    else:
                        # Если по какой-то причине замена класса не произошла,
                        # используем прямое присваивание модуля
                        logger.warning("Оригинальный класс Anthropic не сохранен, использую модуль напрямую")
                        self.client = anthropic
                except Exception as e:
                    logger.error(f"Ошибка при создании патченного клиента Anthropic: {e}")
                    # Используем прямое присваивание модуля в случае ошибки
                    self.client = anthropic
                    logger.warning("Используется запасной вариант - прямое присваивание модуля anthropic")
        
        # Заменяем метод инициализации
        OptimizationBot.__init__ = patched_init
        logger.info("Метод __init__ класса OptimizationBot успешно переопределен")
        
        # Запускаем основной скрипт бота
        logger.info("Непосредственный запуск optimization_bot.py")
        
        # Импортируем и запускаем бота
        from optimization_bot import main as bot_main
        bot_main()
    
    except ImportError as e:
        logger.error(f"Ошибка импорта: {e}")
        # В случае сбоя запускаем бот как подпроцесс
        logger.info("Пробуем запустить бота как подпроцесс")
        subprocess.run([sys.executable, "optimization_bot.py"])
    except Exception as e:
        if "409" in str(e):
            logger.warning(f"Конфликт сессий Telegram API (409): {e}")
            logger.info("Ожидание 30 секунд перед повторной попыткой запуска...")
            time.sleep(30)
            logger.info("Запуск бота как подпроцесс после ожидания")
            subprocess.run([sys.executable, "optimization_bot.py"])
        else:
            logger.error(f"Ошибка при запуске бота: {e}")
            # В случае сбоя запускаем бот как подпроцесс
            logger.info("Пробуем запустить бота как подпроцесс")
            subprocess.run([sys.executable, "optimization_bot.py"])
    
    return 0

if __name__ == "__main__":
    main() 