import os
import sys
import subprocess
import logging
import re

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def fix_anthropic_in_container():
    """
    Обновляет библиотеку anthropic в контейнере
    и исправляет инициализацию клиента
    """
    try:
        # Шаг 1: Обновление библиотеки anthropic
        logger.info("Начинаю обновление библиотеки anthropic...")
        update_cmd = "pip install --upgrade anthropic"
        result = subprocess.run(update_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Библиотека anthropic успешно обновлена: {result.stdout}")
        else:
            logger.error(f"Ошибка при обновлении библиотеки: {result.stderr}")
            return False
            
        # Шаг 2: Проверка версии
        version_cmd = "pip show anthropic | grep Version"
        result = subprocess.run(version_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode == 0:
            logger.info(f"Текущая версия anthropic: {result.stdout.strip()}")
        else:
            logger.warning("Не удалось получить версию anthropic")
            
        # Шаг 3: Временный патч для библиотеки
        # Создаем специальный wrapper для Anthropic
        with open("anthropic_wrapper.py", "w") as f:
            f.write("""
import anthropic
import logging
from importlib import reload

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Сохраняем оригинальный класс
_original_anthropic = anthropic.Anthropic

class SafeAnthropicClient(anthropic.Anthropic):
    \"\"\"Безопасная обертка для клиента Anthropic, удаляющая проблемные аргументы\"\"\"
    
    def __init__(self, api_key, **kwargs):
        # Удаляем проблемные аргументы
        if 'proxies' in kwargs:
            del kwargs['proxies']
            logger.info("Удален аргумент 'proxies' из инициализации Anthropic")
            
        # Вызываем оригинальный инициализатор только с безопасными параметрами
        super().__init__(api_key=api_key, **kwargs)
        logger.info("SafeAnthropicClient успешно инициализирован")

def patch_anthropic():
    \"\"\"Патчит модуль anthropic, заменяя клиент на безопасную версию\"\"\"
    try:
        # Перезагрузка модуля для чистой инициализации
        reload(anthropic)
        
        # Заменяем оригинальный класс на безопасную обертку
        anthropic.Anthropic = SafeAnthropicClient
        
        logger.info("Модуль anthropic успешно пропатчен")
        return True
    except Exception as e:
        logger.error(f"Ошибка при патче модуля anthropic: {e}")
        return False

# Функция для создания безопасного клиента
def create_safe_client(api_key):
    \"\"\"
    Создает безопасную версию клиента Anthropic
    
    Args:
        api_key: API ключ для Anthropic
        
    Returns:
        SafeAnthropicClient: Безопасный клиент Anthropic
    \"\"\"
    try:
        # Патчим модуль anthropic
        if not patch_anthropic():
            raise Exception("Не удалось пропатчить модуль anthropic")
            
        # Создаем безопасный клиент
        client = anthropic.Anthropic(api_key=api_key)
        
        return client
    except Exception as e:
        logger.error(f"Ошибка при создании безопасного клиента: {e}")
        raise
""")
        logger.info("Файл антропик-обертки создан успешно")
        
        # Шаг 4: Исправление файла optimization_bot.py
        if os.path.exists("optimization_bot.py"):
            logger.info("Исправляю файл optimization_bot.py...")
            
            # Читаем файл
            with open("optimization_bot.py", "r", encoding="utf-8") as f:
                content = f.read()
                
            # Заменяем функцию create_safe_anthropic_client
            create_safe_pattern = r"def create_safe_anthropic_client\(api_key\):[\s\S]+?return client[\s\S]+?raise"
            new_safe_func = """def create_safe_anthropic_client(api_key):
    \"\"\"
    Создает клиент Anthropic с безопасными параметрами
    \"\"\"
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
            
            # Заменяем функцию
            modified_content = re.sub(create_safe_pattern, new_safe_func, content)
            
            # Записываем изменения
            with open("optimization_bot.py", "w", encoding="utf-8") as f:
                f.write(modified_content)
                
            logger.info("Файл optimization_bot.py успешно обновлен")
        else:
            logger.warning("Файл optimization_bot.py не найден")
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при фиксации anthropic: {e}")
        return False

if __name__ == "__main__":
    if fix_anthropic_in_container():
        logger.info("Библиотека anthropic успешно исправлена")
    else:
        logger.error("Не удалось исправить библиотеку anthropic") 