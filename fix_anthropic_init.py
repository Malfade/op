import os
import re
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_anthropic_initialization():
    """
    Исправляет инициализацию клиента Anthropic в файле optimization_bot.py
    """
    try:
        # Проверяем существование файла
        if not os.path.exists('optimization_bot.py'):
            logger.error("Файл optimization_bot.py не найден")
            return False
            
        # Читаем содержимое файла
        with open('optimization_bot.py', 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info("Файл optimization_bot.py успешно прочитан")
            
        # Ищем блок инициализации клиента
        init_pattern = r'try:\s*if not api_key:[^}]+self\.client = anthropic\.Anthropic\(api_key=api_key\)[^}]+except Exception as e:'
        
        if not re.search(init_pattern, content, re.DOTALL):
            logger.error("Блок инициализации клиента не найден")
            return False
            
        logger.info("Найден блок инициализации клиента")
        
        # Новый код инициализации
        new_init = '''try:
            if not api_key:
                raise ValueError("API ключ не может быть пустым")
            # Импортируем антропик заново для чистой инициализации
            import importlib
            anthropic = importlib.import_module('anthropic')
            # Создаем клиента только с необходимым параметром
            self.client = anthropic.Anthropic(api_key=api_key)
            logger.info("Клиент Anthropic успешно инициализирован")
        except Exception as e:'''
        
        # Заменяем блок инициализации
        modified_content = re.sub(init_pattern, new_init, content, flags=re.DOTALL)
        
        # Записываем обновленное содержимое
        with open('optimization_bot.py', 'w', encoding='utf-8') as f:
            f.write(modified_content)
            
        logger.info("Файл optimization_bot.py успешно обновлен")
        return True
        
    except Exception as e:
        logger.error(f"Произошла ошибка при обновлении файла: {e}")
        return False

if __name__ == '__main__':
    fix_anthropic_initialization() 