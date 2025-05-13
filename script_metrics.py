import json
import os
import time
from datetime import datetime
from collections import defaultdict, Counter
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ScriptMetrics:
    """Класс для сбора и сохранения метрик качества скриптов"""
    
    def __init__(self, metrics_file="script_metrics.json"):
        """Инициализация класса метрик
        
        Args:
            metrics_file (str): Путь к файлу для сохранения метрик
        """
        self.metrics_file = metrics_file
        self.metrics = self._load_metrics()
    
    def _load_metrics(self):
        """Загрузка метрик из файла"""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self._create_initial_metrics()
        else:
            return self._create_initial_metrics()
    
    def _create_initial_metrics(self):
        """Создание начальной структуры метрик"""
        return {
            "total_scripts_generated": 0,
            "total_errors_found": 0,
            "total_errors_fixed": 0,
            "error_types": {},
            "error_trends": [],
            "model_performance": {},
            "last_updated": datetime.now().isoformat()
        }
    
    def _save_metrics(self):
        """Сохранение метрик в файл"""
        self.metrics["last_updated"] = datetime.now().isoformat()
        
        with open(self.metrics_file, 'w', encoding='utf-8') as f:
            json.dump(self.metrics, f, indent=4, ensure_ascii=False)
    
    def record_script_generation(self, data=None):
        """Записывает информацию о генерации скрипта
        
        Args:
            data (dict, optional): Данные о генерации. Если None, то просто увеличивает счетчик.
        """
        try:
            # Увеличиваем счетчик сгенерированных скриптов
            self.metrics["total_scripts_generated"] += 1
            
            # Если переданы данные для записи
            if isinstance(data, dict):
                # Проверяем наличие поля errors или validation_results
                if "errors" in data or "validation_results" in data:
                    # Сохраняем данные об ошибках, если они есть
                    validation_results = data.get("validation_results") or data.get("errors") or {}
                    
                    # Записываем результаты валидации
                    self.record_validation_results(validation_results)
                    
                    # Если переданы данные о количестве исправленных ошибок
                    if "fixed_count" in data:
                        self.metrics["total_errors_fixed"] += data["fixed_count"]
                        self.record_script_fix()
            
            # Сохраняем изменения
            self._save_metrics()
            
            return True
        except Exception as e:
            logger.error(f"Ошибка при записи информации о генерации скрипта: {e}")
            return False
    
    def record_validation_results(self, validation_results, model_name="unknown", fixed_count=0):
        """Запись результатов валидации скрипта
        
        Args:
            validation_results (dict): Результаты валидации скриптов
            model_name (str, optional): Название модели
            fixed_count (int, optional): Количество исправленных ошибок
        """
        # Подсчет ошибок
        error_count = 0
        error_types = Counter()
        
        for filename, issues in validation_results.items():
            error_count += len(issues)
            
            # Группировка ошибок по типу
            for issue in issues:
                # Извлекаем тип ошибки из сообщения (например, "ps_syntax", "bat_syntax", и т.д.)
                if "(" in issue and ")" in issue:
                    error_type = issue.split("(")[1].split(")")[0]
                    error_types[error_type] += 1
                else:
                    error_types["other"] += 1
        
        # Обновляем общее количество найденных ошибок
        self.metrics["total_errors_found"] += error_count
        
        # Обновляем типы ошибок
        for error_type, count in error_types.items():
            if error_type in self.metrics["error_types"]:
                self.metrics["error_types"][error_type] += count
            else:
                self.metrics["error_types"][error_type] = count
        
        # Добавляем запись в тренды
        trend_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": model_name,
            "errors_found": error_count,
            "errors_fixed": fixed_count,
            "error_types": dict(error_types)
        }
        self.metrics["error_trends"].append(trend_entry)
        
        # Обновляем статистику по модели
        if model_name not in self.metrics["model_performance"]:
            self.metrics["model_performance"][model_name] = {
                "total_scripts": 0,
                "total_errors": 0,
                "total_fixed": 0,
                "average_errors_per_script": 0
            }
        
        model_stats = self.metrics["model_performance"][model_name]
        model_stats["total_scripts"] += 1
        model_stats["total_errors"] += error_count
        model_stats["total_fixed"] += fixed_count
        model_stats["average_errors_per_script"] = (
            model_stats["total_errors"] / model_stats["total_scripts"]
        )
        
        # Сохраняем обновленные метрики
        self._save_metrics()
        
        return {
            "total_errors": error_count,
            "fixed_errors": fixed_count,
            "improvement_percentage": 
                (fixed_count / error_count * 100) if error_count > 0 else 0
        }
    
    def get_model_stats(self, model_name=None):
        """Получение статистики по модели
        
        Args:
            model_name (str, optional): Название модели для получения статистики
        
        Returns:
            dict: Статистика по модели или всем моделям
        """
        if model_name:
            if model_name in self.metrics["model_performance"]:
                return self.metrics["model_performance"][model_name]
            else:
                return None
        else:
            return self.metrics["model_performance"]
    
    def get_error_trends(self, days=30):
        """Получение трендов ошибок за указанный период
        
        Args:
            days (int, optional): Количество дней для анализа трендов
        
        Returns:
            dict: Тренды ошибок по дням
        """
        now = datetime.now()
        cutoff = now.timestamp() - (days * 24 * 60 * 60)
        
        # Фильтруем данные за указанный период
        recent_trends = [
            trend for trend in self.metrics["error_trends"]
            if datetime.fromisoformat(trend["timestamp"]).timestamp() > cutoff
        ]
        
        # Группируем данные по дням
        daily_trends = defaultdict(lambda: {"errors_found": 0, "errors_fixed": 0, "scripts": 0})
        
        for trend in recent_trends:
            day = trend["timestamp"][:10]  # Получаем только дату (YYYY-MM-DD)
            daily_trends[day]["errors_found"] += trend["errors_found"]
            daily_trends[day]["errors_fixed"] += trend["errors_fixed"]
            daily_trends[day]["scripts"] += 1
        
        return dict(daily_trends)
    
    def get_common_errors(self, limit=5):
        """Получение наиболее распространенных типов ошибок
        
        Args:
            limit (int): Ограничение по количеству возвращаемых ошибок
        
        Returns:
            list: Список кортежей (тип_ошибки, количество)
        """
        try:
            # Берем словарь с типами ошибок
            error_types = self.metrics.get("error_types", {})
            
            # Создаем счетчик
            counter = Counter(error_types)
            
            # Возвращаем наиболее распространенные ошибки
            return counter.most_common(limit)
        except Exception as e:
            logger.error(f"Ошибка при получении распространенных ошибок: {e}")
            return []
    
    def get_summary(self):
        """Получение общей сводки метрик
        
        Returns:
            dict: Сводка метрик
        """
        total_errors = self.metrics["total_errors_found"]
        total_fixed = self.metrics["total_errors_fixed"]
        
        return {
            "total_scripts": self.metrics["total_scripts_generated"],
            "total_errors": total_errors,
            "total_fixed": total_fixed,
            "fix_rate": (total_fixed / total_errors * 100) if total_errors > 0 else 0,
            "avg_errors_per_script": 
                total_errors / self.metrics["total_scripts_generated"] 
                if self.metrics["total_scripts_generated"] > 0 else 0,
            "common_errors": self.get_common_errors(5),
            "last_updated": self.metrics["last_updated"]
        }

# Пример использования:
# metrics = ScriptMetrics()
# metrics.record_script_generation("Claude-3-Sonnet", validation_results, fix_results)
# summary = metrics.get_summary()
# print(f"Всего скриптов: {summary['total_scripts']}")
# print(f"Всего ошибок: {summary['total_errors']}")
# print(f"Исправлено ошибок: {summary['total_fixed']} ({summary['fix_rate']:.1f}%)")
# print("Распространенные ошибки:")
# for error_type, count in summary["common_errors"]:
#     print(f"  - {error_type}: {count}") 