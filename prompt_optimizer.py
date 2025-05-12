import os
import json
import logging
from script_metrics import ScriptMetrics
from collections import Counter
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PromptOptimizer:
    """Класс для оптимизации промптов на основе накопленных метрик"""
    
    def __init__(self, base_prompts_file="base_prompts.json", optimized_prompts_file="optimized_prompts.json", metrics=None):
        self.base_prompts_file = base_prompts_file
        self.optimized_prompts_file = optimized_prompts_file
        self.metrics = metrics
        self.base_prompts = self._load_base_prompts()
        self.optimized_prompts = self._load_optimized_prompts()
        # Метрики для анализа производительности промптов
        self.prompt_metrics = {
            "successful_generations": 0,
            "with_errors": 0,
            "empty_responses": 0,
            "errors": 0,
            "regeneration_required": 0,
            "regenerations_successful": 0,
            "error_detection": 0,
            "last_updated": datetime.now().isoformat()
        }
    
    def _load_base_prompts(self):
        """Загружает базовые промпты из файла"""
        try:
            if os.path.exists(self.base_prompts_file):
                with open(self.base_prompts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Создаем файл с дефолтными промптами
                default_prompts = {
                    "script_generation": "Создай скрипт PowerShell для оптимизации Windows, используя указанную информацию о системе.",
                    "error_fixing": "Исправь ошибки в скрипте PowerShell для оптимизации Windows.",
                    "windows_version_prefix": "Для Windows версии",
                    "error_description_prefix": "Ошибка скрипта:",
                    "last_updated": datetime.now().isoformat()
                }
                with open(self.base_prompts_file, 'w', encoding='utf-8') as f:
                    json.dump(default_prompts, f, ensure_ascii=False, indent=4)
                return default_prompts
        except Exception as e:
            logger.error(f"Ошибка при загрузке базовых промптов: {e}")
            return {
                "script_generation": "Создай скрипт PowerShell для оптимизации Windows, используя указанную информацию о системе.",
                "error_fixing": "Исправь ошибки в скрипте PowerShell для оптимизации Windows.",
                "windows_version_prefix": "Для Windows версии",
                "error_description_prefix": "Ошибка скрипта:",
                "last_updated": datetime.now().isoformat()
            }
    
    def _load_optimized_prompts(self):
        """Загружает оптимизированные промпты из файла или создает копию базовых"""
        try:
            if os.path.exists(self.optimized_prompts_file):
                with open(self.optimized_prompts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # Создаем файл с оптимизированными промптами на основе базовых
                optimized_prompts = self.base_prompts.copy()
                optimized_prompts["last_updated"] = datetime.now().isoformat()
                with open(self.optimized_prompts_file, 'w', encoding='utf-8') as f:
                    json.dump(optimized_prompts, f, ensure_ascii=False, indent=4)
                return optimized_prompts
        except Exception as e:
            logger.error(f"Ошибка при загрузке оптимизированных промптов: {e}")
            return self.base_prompts.copy()
    
    def get_optimized_prompts(self):
        """Возвращает текущие оптимизированные промпты"""
        return self.optimized_prompts
    
    def _save_optimized_prompts(self):
        """Сохраняет оптимизированные промпты в файл"""
        try:
            self.optimized_prompts["last_updated"] = datetime.now().isoformat()
            with open(self.optimized_prompts_file, 'w', encoding='utf-8') as f:
                json.dump(self.optimized_prompts, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logger.error(f"Ошибка при сохранении оптимизированных промптов: {e}")
            return False
    
    def update_metrics(self, metric_name, value=1):
        """Обновляет метрику производительности промпта"""
        if metric_name in self.prompt_metrics:
            self.prompt_metrics[metric_name] += value
            return True
        return False
    
    def update_prompts_based_on_metrics(self):
        """Обновляет промпты на основе собранных метрик"""
        # Проверяем наличие достаточного количества данных
        if self.prompt_metrics["successful_generations"] + self.prompt_metrics["with_errors"] < 10:
            logger.info("Недостаточно данных для обновления промптов.")
            return False
            
        # Если метрики переданы извне, используем их
        if self.metrics:
            try:
                error_stats = self.metrics.get_error_stats()
                common_errors = self.metrics.get_common_errors()
                
                # Проверяем, что есть достаточно данных
                if error_stats["total"] < 10:
                    logger.info("Недостаточно данных для оптимизации промптов (менее 10 ошибок)")
                    return False
                
                logger.info(f"Обновление промптов на основе {error_stats['total']} ошибок")
                
                # Обновляем промпты на основе статистики ошибок
                self._update_prompts_with_error_stats(error_stats, common_errors)
                return True
            except Exception as e:
                logger.error(f"Ошибка при обновлении промптов на основе внешних метрик: {e}")
        
        # Если внешние метрики недоступны, используем внутренние
        if self.prompt_metrics["error_detection"] > 0 and self.prompt_metrics["with_errors"] > 0:
            try:
                self._update_prompts_with_internal_metrics()
                return True
            except Exception as e:
                logger.error(f"Ошибка при обновлении промптов на основе внутренних метрик: {e}")
        
        return False
    
    def _update_prompts_with_error_stats(self, error_stats, common_errors):
        """Обновляет промпты на основе статистики ошибок"""
        # Обновляем промпт для генерации скриптов
        script_gen_prompt = self.base_prompts["script_generation"]
        
        # Добавляем инструкции по наиболее частым ошибкам
        if common_errors:
            error_instructions = []
            for error_type, count in common_errors:
                if error_type == "admin_check_missing":
                    error_instructions.append("Обязательно добавь проверку прав администратора")
                elif error_type == "error_handling_missing":
                    error_instructions.append("Включи обработку ошибок (try-catch блоки)")
                elif error_type == "utf8_encoding_missing":
                    error_instructions.append("Установи кодировку UTF-8 для корректного отображения русских символов")
                elif error_type == "unbalanced_braces":
                    error_instructions.append("Проверяй баланс открывающих и закрывающих скобок")
                elif error_type == "execution_policy_missing":
                    error_instructions.append("Для BAT файлов используй параметр -ExecutionPolicy Bypass")
            
            # Добавляем инструкции к базовому промпту
            if error_instructions:
                script_gen_prompt += " " + " ".join(error_instructions) + "."
        
        # Добавляем рекомендации по обязательным функциям
        script_gen_prompt += " Включи функции Backup-Settings (для бэкапа настроек), Optimize-Performance (для оптимизации производительности), Clean-System (для очистки системы) и Disable-Services (для отключения лишних служб)."
        
        # Обновляем промпт для исправления ошибок
        error_fix_prompt = self.base_prompts["error_fixing"]
        error_fix_prompt += " Проверь и исправь следующие распространенные проблемы: баланс скобок, корректное использование try-catch, установку кодировки UTF-8, проверку прав администратора."
        
        # Обновляем оптимизированные промпты
        self.optimized_prompts["script_generation"] = script_gen_prompt
        self.optimized_prompts["error_fixing"] = error_fix_prompt
        
        # Сохраняем обновленные промпты
        return self._save_optimized_prompts()
    
    def _update_prompts_with_internal_metrics(self):
        """Обновляет промпты на основе внутренних метрик"""
        # Определяем общие проблемы на основе внутренней статистики
        if self.prompt_metrics["regeneration_required"] > 0:
            # Добавляем улучшения к промптам для предотвращения регенерации
            script_gen_prompt = self.base_prompts["script_generation"]
            script_gen_prompt += " Обрати особое внимание на обработку ошибок и проверку параметров."
            script_gen_prompt += " Убедись, что все блоки try-catch правильно закрыты."
            script_gen_prompt += " Добавь проверку прав администратора в начале скрипта."
            script_gen_prompt += " Используй параметр -ErrorAction SilentlyContinue для операций, которые могут вызвать ошибки."
            
            # Обновляем промпт исправления ошибок
            error_fix_prompt = self.base_prompts["error_fixing"]
            error_fix_prompt += " Обрати внимание на частые проблемы: несбалансированные скобки, отсутствие проверок существования файлов, отсутствие обработки ошибок, проблемы с кодировкой."
            
            # Обновляем оптимизированные промпты
            self.optimized_prompts["script_generation"] = script_gen_prompt
            self.optimized_prompts["error_fixing"] = error_fix_prompt
            
            # Сохраняем обновленные промпты
            return self._save_optimized_prompts()
        
        return False
    
    def reset_to_base_prompts(self):
        """Сбрасывает оптимизированные промпты к базовым значениям"""
        self.optimized_prompts = self.base_prompts.copy()
        self.optimized_prompts["last_updated"] = datetime.now().isoformat()
        success = self._save_optimized_prompts()
        
        if success:
            logger.info("Промпты сброшены к базовым значениям")
            return True
        else:
            logger.error("Не удалось сбросить промпты к базовым значениям")
            return False

# Пример использования:
# if __name__ == "__main__":
#     optimizer = PromptOptimizer()
#     updated = optimizer.update_prompts_based_on_metrics()
#     
#     if updated:
#         optimized_prompts = optimizer.get_optimized_prompts()
#         print(f"Промпты обновлены до версии {optimized_prompts['version']}")
#     else:
#         print("Промпты не были обновлены.") 