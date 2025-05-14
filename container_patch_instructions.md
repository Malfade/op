# Инструкции по исправлению ошибки в контейнере

## Проблема
В контейнере возникает ошибка при инициализации клиента Anthropic:
```
TypeError: __init__() got an unexpected keyword argument 'proxies'
```

## Решение
Необходимо исправить функцию `create_safe_anthropic_client` в файле `optimization_bot.py`.

### Шаг 1: Создайте файл патча
Создайте файл `fix_anthropic.py` со следующим содержимым:

```python
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
        bot_file = "/app/optimization_bot.py"
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
```

### Шаг 2: Копируйте файл в контейнер
```bash
docker cp fix_anthropic.py CONTAINER_ID:/app/
```
Замените `CONTAINER_ID` на реальный ID вашего контейнера.

### Шаг 3: Выполните скрипт в контейнере
```bash
docker exec CONTAINER_ID python /app/fix_anthropic.py
```

### Шаг 4: Перезапустите бота
```bash
docker exec CONTAINER_ID pkill -f "python direct_bot.py"
docker exec -d CONTAINER_ID python /app/direct_bot.py
```

## Альтернативное решение
Если у вас нет возможности использовать Docker команды, можно отредактировать файл `optimization_bot.py` непосредственно в контейнере:

1. Зайдите в контейнер с помощью команды:
```bash
docker exec -it CONTAINER_ID bash
```

2. Установите текстовый редактор (если его нет):
```bash
apt-get update && apt-get install -y nano
```

3. Откройте файл на редактирование:
```bash
nano /app/optimization_bot.py
```

4. Найдите функцию `create_safe_anthropic_client` и замените ее на:
```python
def create_safe_anthropic_client(api_key):
    """
    Создает клиент Anthropic с безопасными параметрами
    """
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
        raise
```

5. Сохраните файл (в nano: Ctrl+O, затем Enter, затем Ctrl+X)

6. Перезапустите бота:
```bash
pkill -f "python direct_bot.py"
python /app/direct_bot.py &
``` 