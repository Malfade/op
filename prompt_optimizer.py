import os
import json
import logging
from script_metrics import ScriptMetrics
from collections import Counter

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PromptOptimizer:
    """Класс для оптимизации промптов на основе метрик ошибок"""
    
    def __init__(self, base_prompts_file="base_prompts.json"):
        """Инициализация оптимизатора промптов
        
        Args:
            base_prompts_file (str): Путь к файлу с базовыми промптами
        """
        self.base_prompts_file = base_prompts_file
        self.metrics = ScriptMetrics()
        self.base_prompts = self._load_base_prompts()
        
        # Сохраняем имеющиеся промпты для первого запуска
        if not os.path.exists(self.base_prompts_file):
            self._save_base_prompts()
    
    def _load_base_prompts(self):
        """Загрузка базовых промптов из файла или создание новых"""
        if os.path.exists(self.base_prompts_file):
            try:
                with open(self.base_prompts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self._create_default_prompts()
        else:
            return self._create_default_prompts()
    
    def _create_default_prompts(self):
        """Создание структуры с промптами по умолчанию"""
        # Импортируем шаблоны из основного файла
        try:
            from optimization_bot import OPTIMIZATION_PROMPT_TEMPLATE, ERROR_FIX_PROMPT_TEMPLATE
            
            return {
                "OPTIMIZATION_PROMPT_TEMPLATE": OPTIMIZATION_PROMPT_TEMPLATE,
                "ERROR_FIX_PROMPT_TEMPLATE": ERROR_FIX_PROMPT_TEMPLATE,
                "version": 1,
                "error_examples": {}
            }
        except ImportError:
            # Если не удалось импортировать, создаем пустую структуру
            logger.warning("Не удалось импортировать шаблоны из основного файла")
            return {
                "OPTIMIZATION_PROMPT_TEMPLATE": "",
                "ERROR_FIX_PROMPT_TEMPLATE": "",
                "version": 1,
                "error_examples": {}
            }
    
    def _save_base_prompts(self):
        """Сохранение обновленных промптов в файл"""
        with open(self.base_prompts_file, 'w', encoding='utf-8') as f:
            json.dump(self.base_prompts, f, indent=4, ensure_ascii=False)
    
    def update_prompts_based_on_metrics(self):
        """Обновление промптов на основе собранных метрик"""
        # Получаем метрики
        summary = self.metrics.get_summary()
        common_errors = self.metrics.get_common_errors(10)
        
        # Если недостаточно данных, пропускаем обновление
        if summary["total_scripts"] < 5:
            logger.info("Недостаточно данных для обновления промптов.")
            return False
        
        # Обновляем версию промптов
        self.base_prompts["version"] += 1
        
        # Обновляем примеры ошибок
        for error_type, count in common_errors:
            if error_type != "other" and count > 2:
                # Добавляем примеры ошибок в промпты
                self.base_prompts["error_examples"][error_type] = count
        
        # Обновляем оптимизационный промпт
        optimization_improvements = self._generate_optimization_improvements(common_errors)
        if optimization_improvements:
            current_prompt = self.base_prompts["OPTIMIZATION_PROMPT_TEMPLATE"]
            
            # Находим место для вставки улучшений (перед последним блоком)
            split_point = current_prompt.rfind("Предоставь три файла:")
            if split_point > 0:
                updated_prompt = (
                    current_prompt[:split_point] + 
                    "\nДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ НА ОСНОВЕ АНАЛИЗА ЧАСТЫХ ОШИБОК:\n" +
                    optimization_improvements +
                    "\n\n" +
                    current_prompt[split_point:]
                )
                self.base_prompts["OPTIMIZATION_PROMPT_TEMPLATE"] = updated_prompt
        
        # Обновляем промпт исправления ошибок
        error_fix_improvements = self._generate_error_fix_improvements(common_errors)
        if error_fix_improvements:
            current_prompt = self.base_prompts["ERROR_FIX_PROMPT_TEMPLATE"]
            
            # Находим место для вставки улучшений (перед последним блоком)
            split_point = current_prompt.rfind("Предоставь исправленные версии файлов:")
            if split_point > 0:
                updated_prompt = (
                    current_prompt[:split_point] + 
                    "\nДОПОЛНИТЕЛЬНЫЕ РЕКОМЕНДАЦИИ НА ОСНОВЕ АНАЛИЗА ЧАСТЫХ ОШИБОК:\n" +
                    error_fix_improvements +
                    "\n\n" +
                    current_prompt[split_point:]
                )
                self.base_prompts["ERROR_FIX_PROMPT_TEMPLATE"] = updated_prompt
        
        # Сохраняем обновленные промпты
        self._save_base_prompts()
        
        logger.info(f"Промпты успешно обновлены до версии {self.base_prompts['version']}.")
        return True
    
    def _generate_optimization_improvements(self, common_errors):
        """Генерация улучшений для промпта оптимизации на основе распространенных ошибок"""
        improvements = []
        
        error_types = [error_type for error_type, _ in common_errors]
        
        # Добавляем рекомендации в зависимости от типов ошибок
        if "ps_syntax" in error_types:
            improvements.append(
                "1. Обязательно проверяй синтаксис PowerShell скрипта на сбалансированность скобок "
                "и правильное использование конструкций."
            )
        
        if "bat_syntax" in error_types:
            improvements.append(
                "2. В batch файлах всегда добавляй перенаправление ошибок (>nul 2>&1) для команд, "
                "которые могут выводить ошибки в стандартный поток."
            )
        
        if "file_access" in error_types:
            improvements.append(
                "3. Перед каждым доступом к файлу обязательно проверь его существование через Test-Path "
                "и добавь параметры -Force для операций удаления."
            )
        
        if "security" in error_types:
            improvements.append(
                "4. Избегай потенциально опасных конструкций, таких как Invoke-Expression с переменными "
                "или неконтролируемое выполнение внешнего кода."
            )
        
        # Добавляем общие рекомендации
        improvements.append(
            "5. Оборачивай ALL операции в try-catch блоки, чтобы предотвратить аварийное завершение скрипта."
        )
        
        improvements.append(
            "6. Проверяй права администратора в НАЧАЛЕ скрипта и выходи с понятным сообщением пользователю."
        )
        
        improvements.append(
            "7. Всегда проверяй существование файлов и дескрипторов перед их использованием."
        )
        
        # Объединяем все рекомендации
        return "\n".join(improvements)
    
    def _generate_error_fix_improvements(self, common_errors):
        """Генерация улучшений для промпта исправления ошибок на основе распространенных ошибок"""
        improvements = []
        
        error_types = [error_type for error_type, _ in common_errors]
        
        # Добавляем рекомендации в зависимости от типов ошибок
        if "ps_syntax" in error_types:
            improvements.append(
                "1. Тщательно проверяй скобки в PowerShell скрипте - несбалансированные скобки "
                "являются одной из самых распространенных ошибок."
            )
        
        if "bat_syntax" in error_types:
            improvements.append(
                "2. Всегда добавляй exit /b с кодом возврата в batch файл, "
                "чтобы процесс корректно завершался с правильным статусом."
            )
        
        if "file_access" in error_types:
            improvements.append(
                "3. При работе с файлами используй специальную обработку для занятых файлов - "
                "добавь паузу и повторную попытку с ограниченным числом итераций."
            )
        
        # Добавляем общие рекомендации
        improvements.append(
            "4. Вместо общих try-catch блоков, используй специфические блоки для каждой "
            "потенциально опасной операции с точечной обработкой конкретных исключений."
        )
        
        improvements.append(
            "5. Добавляй проверку версии Windows, чтобы избежать проблем с отсутствующими "
            "компонентами в разных версиях системы."
        )
        
        improvements.append(
            "6. Для операций с файлами всегда сначала проверяй Test-Path, а затем используй "
            "параметры -Force и -ErrorAction SilentlyContinue для максимальной надежности."
        )
        
        # Объединяем все рекомендации
        return "\n".join(improvements)
    
    def get_optimized_prompts(self):
        """Получение оптимизированных промптов
        
        Returns:
            dict: Словарь с оптимизированными промптами
        """
        return {
            "OPTIMIZATION_PROMPT_TEMPLATE": self.base_prompts["OPTIMIZATION_PROMPT_TEMPLATE"],
            "ERROR_FIX_PROMPT_TEMPLATE": self.base_prompts["ERROR_FIX_PROMPT_TEMPLATE"],
            "version": self.base_prompts["version"]
        }

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