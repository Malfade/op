import os
import re
import sys
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def fix_optimization_bot():
    """Исправляет инициализацию клиента Anthropic в файле optimization_bot.py"""
    try:
        # Определяем путь к файлу в зависимости от среды
        bot_file = "/app/optimization_bot.py" if os.path.exists("/app") else "optimization_bot.py"
        
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