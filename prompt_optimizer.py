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
    """Класс для оптимизации промптов на основе накопленных метрик"""
    
    def __init__(self, base_prompts_file='base_prompts.json', 
                 optimized_prompts_file='optimized_prompts.json',
                 metrics=None):
        """
        Инициализация оптимизатора промптов.
        
        :param base_prompts_file: Путь к файлу с базовыми промптами
        :param optimized_prompts_file: Путь к файлу с оптимизированными промптами
        :param metrics: Объект ScriptMetrics для получения статистики (опционально)
        """
        self.base_prompts_file = base_prompts_file
        self.optimized_prompts_file = optimized_prompts_file
        self.metrics = metrics
        
        # Загружаем базовые и оптимизированные промпты
        self.base_prompts = self._load_base_prompts()
        self.optimized_prompts = self._load_optimized_prompts()
        
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
        """
        Обновляет промпты на основе собранных метрик
        
        :return: True если промпты были обновлены, False в противном случае
        """
        # Проверяем наличие объекта метрик
        if self.metrics is None:
            return False
            
        try:
            # Получаем статистику ошибок
            error_stats = self.metrics.get_error_stats()
            common_errors = self.metrics.get_common_errors(5)
            
            if not error_stats or not common_errors:
                return False
            
            # Обновляем промпты на основе частых ошибок
            updated = False
            
            # Обновляем промпт для генерации скриптов
            script_gen_prompt = self.optimized_prompts.get("OPTIMIZATION_PROMPT_TEMPLATE", 
                                                            self.base_prompts.get("OPTIMIZATION_PROMPT_TEMPLATE", ""))
            
            # Добавляем инструкции для предотвращения частых ошибок
            new_instructions = []
            
            for error_type, _ in common_errors:
                if "admin rights" in error_type.lower() and "Обязательно проверяйте права администратора" not in script_gen_prompt:
                    new_instructions.append("- Обязательно проверяйте права администратора в начале скрипта")
                    
                if "error handling" in error_type.lower() and "Добавляйте обработку ошибок" not in script_gen_prompt:
                    new_instructions.append("- Добавляйте обработку ошибок для каждой важной операции")
                    
                if "encoding" in error_type.lower() and "используйте кодировку UTF-8" not in script_gen_prompt:
                    new_instructions.append("- Для PowerShell скриптов используйте кодировку UTF-8")
                
                # Дополнительные инструкции в зависимости от типов ошибок
            
            if new_instructions:
                if "ВАЖНЫЕ ИНСТРУКЦИИ:" not in script_gen_prompt:
                    script_gen_prompt += "\n\nВАЖНЫЕ ИНСТРУКЦИИ:\n"
                
                for instr in new_instructions:
                    if instr not in script_gen_prompt:
                        script_gen_prompt += instr + "\n"
                        updated = True
            
            if updated:
                self.optimized_prompts["OPTIMIZATION_PROMPT_TEMPLATE"] = script_gen_prompt
            
            # Аналогично обновляем промпт для исправления ошибок
            error_fix_prompt = self.optimized_prompts.get("ERROR_FIX_PROMPT_TEMPLATE", 
                                                          self.base_prompts.get("ERROR_FIX_PROMPT_TEMPLATE", ""))
            
            # Добавляем инструкции для проверки частых ошибок
            fix_instructions = []
            
            for error_type, _ in common_errors:
                if "admin rights" in error_type.lower() and "проверку прав администратора" not in error_fix_prompt:
                    fix_instructions.append("- Проверьте наличие проверки прав администратора")
                    
                if "error handling" in error_type.lower() and "обработку ошибок" not in error_fix_prompt:
                    fix_instructions.append("- Проверьте наличие и корректность блоков обработки ошибок")
                    
                if "encoding" in error_type.lower() and "кодировку UTF-8" not in error_fix_prompt:
                    fix_instructions.append("- Проверьте и установите кодировку UTF-8 для PowerShell скриптов")
            
            if fix_instructions:
                if "ОБЯЗАТЕЛЬНО ПРОВЕРЬТЕ:" not in error_fix_prompt:
                    error_fix_prompt += "\n\nОБЯЗАТЕЛЬНО ПРОВЕРЬТЕ:\n"
                
                for instr in fix_instructions:
                    if instr not in error_fix_prompt:
                        error_fix_prompt += instr + "\n"
                        updated = True
            
            if updated:
                self.optimized_prompts["ERROR_FIX_PROMPT_TEMPLATE"] = error_fix_prompt
                self._save_optimized_prompts()
                return True
                
            return False
            
        except Exception as e:
            print(f"Ошибка при обновлении промптов: {e}")
            return False
    
    def _load_optimized_prompts(self):
        """Загрузка оптимизированных промптов из файла или создание новых"""
        if os.path.exists(self.optimized_prompts_file):
            try:
                with open(self.optimized_prompts_file, 'r', encoding='utf-8') as f:
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
    
    def _save_optimized_prompts(self):
        """Сохранение обновленных оптимизированных промптов в файл"""
        with open(self.optimized_prompts_file, 'w', encoding='utf-8') as f:
            json.dump(self.optimized_prompts, f, indent=4, ensure_ascii=False)
    
    def get_optimized_prompts(self):
        """Получение оптимизированных промптов
        
        Returns:
            dict: Словарь с оптимизированными промптами
        """
        return {
            "OPTIMIZATION_PROMPT_TEMPLATE": self.optimized_prompts["OPTIMIZATION_PROMPT_TEMPLATE"],
            "ERROR_FIX_PROMPT_TEMPLATE": self.optimized_prompts["ERROR_FIX_PROMPT_TEMPLATE"],
            "version": self.optimized_prompts["version"]
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