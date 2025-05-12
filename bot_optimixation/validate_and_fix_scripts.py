import re
import logging
import os
from script_validator import ScriptValidator

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def validate_and_fix_scripts(files):
    """
    Проверяет и исправляет скрипты оптимизации
    
    Args:
        files (dict): Словарь с файлами (имя файла -> содержимое)
        
    Returns:
        tuple: (исправленные файлы, результаты валидации, количество исправленных ошибок)
    """
    try:
        # Создаем экземпляр валидатора
        validator = ScriptValidator()
        
        # Проверяем файлы на наличие ошибок
        logger.info(f"Начинаю валидацию {len(files)} файлов")
        validation_results = validator.validate_files(files)
        
        # Считаем общее количество ошибок
        error_count = sum(len(issues) for issues in validation_results.values())
        logger.info(f"Всего найдено {error_count} ошибок в файлах")
        
        # Если ошибок слишком много, возможно, нужна повторная генерация
        if validator.should_regenerate_script(validation_results):
            logger.warning("Слишком много ошибок, возможно, требуется повторная генерация скрипта")
        
        # Исправляем скрипты с помощью валидатора
        fixed_files = validator.repair_common_issues(files)
        
        # Повторная проверка после исправления
        post_validation = validator.validate_files(fixed_files)
        remaining_errors = sum(len(issues) for issues in post_validation.values())
        
        # Количество исправленных ошибок
        fixed_count = error_count - remaining_errors if remaining_errors <= error_count else 0
        logger.info(f"Исправлено {fixed_count} ошибок из {error_count}")
        
        # Улучшаем скрипты
        enhanced_files = validator.enhance_scripts(fixed_files)
        
        return enhanced_files, validation_results, fixed_count
        
    except Exception as e:
        logger.error(f"Ошибка при валидации и исправлении скриптов: {e}")
        # В случае ошибки возвращаем исходные файлы
        return files, {filename: ["Ошибка валидации: " + str(e)] for filename in files}, 0 