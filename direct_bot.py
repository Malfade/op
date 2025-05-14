#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Прямой запуск бота оптимизации с патчем Anthropic
"""

import sys
import os
import subprocess
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def patch_anthropic_module():
    """
    Патч библиотеки Anthropic напрямую
    """
    logger.info("Применение патча к библиотеке Anthropic")
    
    try:
        # Импортируем модуль anthropic
        import anthropic
        
        # Получаем версию библиотеки
        version = getattr(anthropic, "__version__", "unknown")
        logger.info(f"Версия библиотеки anthropic: {version}")
        
        # Модифицируем модуль
        if not hasattr(anthropic, 'api_key'):
            anthropic.api_key = None
            logger.info("Добавлен атрибут api_key к модулю anthropic")
        
        # Патчим класс Anthropic, если он существует
        if hasattr(anthropic, 'Anthropic'):
            # Сохраняем оригинальный конструктор
            original_init = anthropic.Anthropic.__init__
            
            # Создаем патч для конструктора
            def patched_init(self, *args, **kwargs):
                # Удаляем проблемные аргументы
                if 'proxies' in kwargs:
                    del kwargs['proxies']
                    logger.info("Удален аргумент 'proxies' из конструктора Anthropic")
                
                # Вызываем оригинальный конструктор с отфильтрованными аргументами
                return original_init(self, *args, **kwargs)
            
            # Применяем патч
            anthropic.Anthropic.__init__ = patched_init
            logger.info("Успешно применен патч к конструктору Anthropic")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при патчинге модуля anthropic: {e}")
        return False

def modify_bot_file():
    """
    Изменение файла бота для использования патча
    """
    bot_file = "optimization_bot.py"
    logger.info(f"Модификация файла {bot_file}")
    
    try:
        # Проверяем существование файла
        if not os.path.exists(bot_file):
            logger.error(f"Файл {bot_file} не найден")
            return False
        
        # Читаем содержимое файла
        with open(bot_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Заменяем инициализацию клиента на защищенную версию
        if "self.client = anthropic.Anthropic(api_key=api_key)" in content:
            logger.info("Найден код инициализации клиента Anthropic")
            
            new_content = content.replace(
                "self.client = anthropic.Anthropic(api_key=api_key)",
                """# Патч для совместимости с разными версиями Anthropic
        try:
            self.client = anthropic
            self.client.api_key = api_key
            logger.info("Используется совместимая инициализация Anthropic")
        except Exception as e:
            logger.error(f"Ошибка при инициализации клиента Anthropic: {e}")
            raise"""
            )
            
            # Сохраняем изменения
            with open(bot_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            
            logger.info(f"Файл {bot_file} успешно модифицирован")
            return True
        else:
            logger.warning("Не найден код инициализации клиента Anthropic")
            return False
    
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
    
    # Модифицируем файл бота, если патчинг модуля не удался
    if not patch_success:
        file_mod_success = modify_bot_file()
        logger.info(f"Результат модификации файла: {'успешно' if file_mod_success else 'неудачно'}")
    
    # Запускаем основной скрипт бота
    logger.info("Непосредственный запуск optimization_bot.py")
    from optimization_bot import main as bot_main
    
    # Вызываем главную функцию бота
    bot_main()
    
    return 0

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1) 