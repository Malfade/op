import os
import subprocess
import sys
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def get_container_id():
    """Получает ID контейнера по имени"""
    try:
        cmd = "docker ps -qf name=optimization"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Ошибка при получении ID контейнера: {result.stderr}")
            return None
            
        container_id = result.stdout.strip()
        
        if not container_id:
            logger.error("Контейнер с именем optimization не найден")
            return None
            
        logger.info(f"Найден контейнер: {container_id}")
        return container_id
    except Exception as e:
        logger.error(f"Ошибка при получении ID контейнера: {e}")
        return None

def fix_container():
    """Исправляет файл в контейнере"""
    try:
        # Получаем ID контейнера
        container_id = get_container_id()
        if not container_id:
            return False
            
        # Копируем файл патча в контейнер
        logger.info("Копирую скрипт патча в контейнер...")
        copy_cmd = f"docker cp fix_anthropic_client.py {container_id}:/app/"
        result = subprocess.run(copy_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Ошибка при копировании файла: {result.stderr}")
            return False
            
        # Применяем патч в контейнере
        logger.info("Применяю патч в контейнере...")
        exec_cmd = f"docker exec {container_id} python /app/fix_anthropic_client.py"
        result = subprocess.run(exec_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Ошибка при выполнении патча: {result.stderr}")
            return False
            
        logger.info(f"Результат патча: {result.stdout}")
        
        # Перезапускаем бота
        logger.info("Перезапускаю бота...")
        restart_cmd = f"docker exec {container_id} pkill -f 'python direct_bot.py'"
        subprocess.run(restart_cmd, shell=True, capture_output=True, text=True)
        
        start_cmd = f"docker exec -d {container_id} python /app/direct_bot.py"
        result = subprocess.run(start_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error(f"Ошибка при перезапуске бота: {result.stderr}")
            return False
            
        logger.info("Бот успешно перезапущен")
        return True
    except Exception as e:
        logger.error(f"Ошибка при исправлении контейнера: {e}")
        return False

if __name__ == "__main__":
    if fix_container():
        logger.info("Контейнер успешно исправлен")
        sys.exit(0)
    else:
        logger.error("Ошибка при исправлении контейнера")
        sys.exit(1) 