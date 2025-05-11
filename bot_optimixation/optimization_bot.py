import os
import logging
import json
import base64
import subprocess
from io import BytesIO
from datetime import datetime
import zipfile
import asyncio
import anthropic
import requests
from dotenv import load_dotenv
import telebot
from telebot import types
from telebot.async_telebot import AsyncTeleBot

# Создаем заглушки для удаленных модулей
class ScriptValidator:
    """Заглушка для класса валидатора скриптов"""
    
    def __init__(self):
        self.required_code_blocks = {
            "ps1": {
                "error_handling": r"try|catch",
                "admin_check": r"if\s*\(\s*\-not\s*\(\s*\[bool\]\s*\(\s*\[System\.Security\.Principal\.WindowsIdentity\]::GetCurrent\(\)\.Groups\s*\-match\s*['\"]S-1-5-32-544['\"]\s*\)\s*\)\s*\)"
            },
            "bat": {
                "admin_check": r"NET FILE"
            }
        }
    
    def validate_scripts(self, files):
        """Заглушка для валидации скриптов"""
        logger.info("Используется заглушка для валидации скриптов")
        return {name: [] for name in files}
    
    def repair_common_issues(self, files):
        """Заглушка для исправления распространенных проблем"""
        logger.info("Используется заглушка для исправления проблем в скриптах")
        return files
    
    def enhance_scripts(self, files):
        """Заглушка для улучшения скриптов"""
        logger.info("Используется заглушка для улучшения скриптов")
        return files

class ScriptMetrics:
    """Заглушка для класса метрик скриптов"""
    
    def __init__(self):
        pass
    
    def record_script_generation(self, data):
        """Заглушка для записи метрик генерации скриптов"""
        logger.info(f"Запись метрик скрипта (заглушка): {data['timestamp']}")
        return True
    
    def get_summary(self):
        """Заглушка для получения сводки по метрикам"""
        return {"total_scripts": 0, "total_errors": 0}
    
    def get_common_errors(self, limit=10):
        """Заглушка для получения распространенных ошибок"""
        return []

class PromptOptimizer:
    """Заглушка для оптимизатора промптов"""
    
    def __init__(self, base_prompts_file="base_prompts.json"):
        pass
    
    def get_optimized_prompts(self):
        """Заглушка для получения оптимизированных промптов"""
        return {
            "OPTIMIZATION_PROMPT_TEMPLATE": OPTIMIZATION_PROMPT_TEMPLATE,
            "ERROR_FIX_PROMPT_TEMPLATE": ERROR_FIX_PROMPT_TEMPLATE,
            "version": 1
        }
    
    def update_prompts_based_on_metrics(self):
        """Заглушка для обновления промптов на основе метрик"""
        logger.info("Обновление промптов (заглушка)")
        return False

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация бота
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')

# Создаем экземпляр бота
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Словари для хранения состояний пользователей
user_states = {}  # Хранение состояний пользователей
user_files = {}   # Хранение файлов пользователей
user_messages = {}  # Хранение текста сообщений

# Статистика по генерации скриптов и ошибкам
script_gen_count = 0
error_stats = {
    "total_errors": 0,
    "ps_syntax": 0,
    "bat_syntax": 0,
    "file_access": 0,
    "security": 0,
    "missing_blocks": 0,
    "other": 0
}

# Шаблон промпта для оптимизации системы
OPTIMIZATION_PROMPT_TEMPLATE = r"""
Ты - эксперт по системному администрированию Windows и PowerShell. Необходимо создать скрипты для оптимизации Windows на основе предоставленного изображения.

ТРЕБОВАНИЯ К СКРИПТАМ:
1. Создай два файла: основной PowerShell скрипт (WindowsOptimizer.ps1) и вспомогательный BAT-файл для запуска (Start-Optimizer.bat).
2. В BAT-файле должен быть запуск PowerShell скрипта с параметром -ExecutionPolicy Bypass и проверка прав администратора.
3. PowerShell скрипт должен включать:
   - Функции резервного копирования параметров перед изменением (обязательно!)
   - Проверку наличия прав администратора
   - Оптимизацию производительности на основе данных из изображения
   - Отключение ненужных служб и компонентов
   - Очистку временных файлов и оптимизацию диска
   - Проверки наличия файлов перед их модификацией
   - Логирование всех действий с указанием времени
   - Обработку ошибок (все операции должны быть в try-catch блоках)
   - Подробные комментарии о выполняемых действиях

СТРУКТУРА POWERSHELL СКРИПТА:
- В начале скрипта должна быть функция резервного копирования (Backup-Settings)
- Затем проверка прав администратора с выходом, если прав недостаточно
- Функции для выполнения оптимизации (отдельно для каждой категории)
- Основная часть скрипта, вызывающая функции оптимизации
- Вывод информации о выполненных оптимизациях в конце

ВАЖНЫЕ ПРАВИЛА:
- ВСЕГДА проверяй существование файлов и служб перед их изменением (Test-Path, Get-Service)
- Используй параметр -Force для операций с файлами
- Добавляй параметр -ErrorAction SilentlyContinue для критичных операций
- Обеспечь полную совместимость с Windows 10/11
- Не используй опасные операции, которые могут сломать систему (не отключай критичные службы)
- Создавай резервные копии всех изменяемых параметров
- Документируй код подробными комментариями

Проанализируй изображение и создай скрипты оптимизации, которые учитывают информацию о системе из скриншота. Если на изображении системные характеристики или состояние компьютера, используй эту информацию для создания более эффективной оптимизации.

Предоставь три файла:
1. WindowsOptimizer.ps1 (основной PowerShell скрипт оптимизации)
2. Start-Optimizer.bat (вспомогательный BAT-файл для запуска)
3. README.md (краткое описание и инструкции)
"""

# Шаблон промпта для исправления ошибок
ERROR_FIX_PROMPT_TEMPLATE = r"""
Ты - эксперт по PowerShell и Windows. Необходимо исправить ошибки в скрипте оптимизации Windows, которые видны на прикрепленном изображении.

ЗАДАЧА:
1. Проанализируй ошибки на скриншоте
2. Определи, что именно вызывает проблемы
3. Создай исправленные версии скриптов

ТИПИЧНЫЕ ПРОБЛЕМЫ, КОТОРЫЕ МОГУТ БЫТЬ НА СКРИНШОТЕ:
1. Синтаксические ошибки в PowerShell или BAT
2. Проблемы с правами доступа
3. Несбалансированные скобки или кавычки
4. Отсутствующие зависимости или компоненты
5. Ошибки при доступе к файлам или реестру
6. Проблемы с кодировкой
7. Несуществующие команды или параметры

ТРЕБОВАНИЯ К ИСПРАВЛЕННЫМ СКРИПТАМ:
- Добавь дополнительные проверки для предотвращения подобных ошибок в будущем
- Улучши обработку ошибок (try-catch блоки)
- Добавь логирование для отладки
- Для операций с файлами всегда добавляй проверку существования (Test-Path)
- Все изменения должны сохраняться в резервные копии
- Операции удаления должны использовать параметр -Force
- Для PowerShell добавь проверку прав администратора
- Для Batch файлов добавь корректный запуск с параметром -ExecutionPolicy Bypass

СТРУКТУРА СКРИПТОВ:
1. WindowsOptimizer.ps1 - основной скрипт оптимизации
2. Start-Optimizer.bat - вспомогательный скрипт запуска с правами администратора

При анализе изображения и исправлении ошибок обрати особое внимание на контекст выполнения, сообщения об ошибках и синтаксические проблемы, которые можно увидеть на скриншоте.

Предоставь исправленные версии файлов:
1. WindowsOptimizer.ps1 (исправленный PowerShell скрипт)
2. Start-Optimizer.bat (исправленный BAT-файл для запуска)
"""

import re

class OptimizationBot:
    """Класс для управления ботом оптимизации Windows"""
    
    def __init__(self, api_key, validator=None):
        """Инициализация бота с заданными токенами"""
        self.api_key = api_key
        self.client = anthropic.Anthropic(api_key=api_key)
        self.validator = validator or ScriptValidator()
        self.metrics = ScriptMetrics()
        self.prompt_optimizer = PromptOptimizer()
        
        # Метрики качества
        self.total_scripts_generated = 0
        self.total_errors = 0
        self.error_types = {}
        
        # Получение оптимизированных промптов
        prompts = self.prompt_optimizer.get_optimized_prompts()
        self.optimization_prompt = prompts.get("OPTIMIZATION_PROMPT_TEMPLATE", OPTIMIZATION_PROMPT_TEMPLATE)
        self.error_fix_prompt = prompts.get("ERROR_FIX_PROMPT_TEMPLATE", ERROR_FIX_PROMPT_TEMPLATE)
    
    async def generate_new_script(self, message):
        """Генерация нового скрипта оптимизации на основе скриншота системы"""
        global script_gen_count
        
        try:
            logger.info(f"Начинаю генерацию скрипта для пользователя {message.chat.id}")
            
            # Проверяем наличие фото
            if not message.photo:
                return "Не найдено изображение. Пожалуйста, отправьте скриншот системной информации."
            
            # Получаем файл фото
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"
            
            # Загружаем изображение
            img_data = requests.get(file_url).content
            
            # Кодируем изображение в base64
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # Формируем сообщение для API
            user_message = user_messages.get(message.chat.id, "Создай скрипт оптимизации Windows")
            
            # Используем оптимизированный промпт, если он доступен
            prompt = self.optimization_prompt
            
            messages = [
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": prompt + "\n\n" + user_message},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_base64}}
                    ]
                }
            ]
            
            logger.info("Отправляю запрос к Claude API...")
            
            # Отправляем запрос к Claude
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-opus-20240229",
                max_tokens=4000,
                messages=messages
            )
            
            # Обрабатываем ответ
            response_text = response.content[0].text
            
            logger.info(f"Получен ответ от Claude API, длина: {len(response_text)} символов")
            
            # Извлекаем файлы из ответа
            files = self.extract_files(response_text)
            
            if not files:
                logger.warning("Не удалось извлечь файлы из ответа API")
                return "Не удалось создать скрипты оптимизации. Пожалуйста, попробуйте еще раз или отправьте другое изображение."
            
            # Валидация и улучшение скриптов
            validation_results = self.validator.validate_scripts(files)
            
            # Подсчитываем количество ошибок
            error_count = 0
            for filename, issues in validation_results.items():
                error_count += len(issues)
            
            # Обновляем статистику ошибок
            self.update_error_stats(validation_results)
            
            # Исправляем распространенные ошибки
            if error_count > 0:
                logger.info(f"Найдено {error_count} ошибок, применяю автоматические исправления")
                files = self.validator.repair_common_issues(files)
                
                # Повторная валидация после исправлений
                validation_results = self.validator.validate_scripts(files)
                
                # Снова считаем ошибки
                fixed_error_count = 0
                for filename, issues in validation_results.items():
                    fixed_error_count += len(issues)
                
                logger.info(f"После исправлений осталось {fixed_error_count} ошибок")
            
            # Улучшаем скрипты (добавляем документацию, логирование и т.д.)
            files = self.validator.enhance_scripts(files)
            
            # Обновляем счетчик сгенерированных скриптов
            script_gen_count += 1
            self.total_scripts_generated += 1
            
            # Обновляем статистику
            self.metrics.record_script_generation({
                "timestamp": datetime.now().isoformat(),
                "errors": validation_results,
                "error_count": error_count,
                "fixed_count": error_count - fixed_error_count if 'fixed_error_count' in locals() else 0,
                "model": "claude-3-opus-20240229"
            })
            
            # Сохраняем файлы для последующей отправки
            user_files[message.chat.id] = files
            
            return files
        
        except Exception as e:
            logger.error(f"Ошибка при генерации скрипта: {e}", exc_info=True)
            return f"Произошла ошибка при создании скрипта: {str(e)}"
    
    def extract_files(self, response_text):
        """Извлечение файлов из ответа Claude"""
        files = {}
        
        try:
            # Ищем блоки с файлами
            file_pattern = r"```(\w+)\s+(.+?)\s+filename:\s+(.+?)\s+([\s\S]+?)```"
            matches = [(ext, desc, name, content) for ext, desc, name, content in re.findall(file_pattern, response_text)]
            
            if not matches:
                # Альтернативный способ поиска файлов
                file_pattern = r"```(\w+)\s+(.+?)\s*\n([\s\S]+?)```"
                alternative_matches = re.findall(file_pattern, response_text)
                
                for ext, desc, content in alternative_matches:
                    if ext.lower() in ["powershell", "ps1", "batch", "bat", "cmd", "markdown", "md"]:
                        # Определяем имя файла из расширения
                        if ext.lower() in ["powershell", "ps1"]:
                            filename = "WindowsOptimizer.ps1"
                        elif ext.lower() in ["batch", "bat", "cmd"]:
                            filename = "Start-Optimizer.bat"
                        elif ext.lower() in ["markdown", "md"]:
                            filename = "README.md"
                        else:
                            filename = f"file.{ext}"
                        
                        files[filename] = content
            else:
                # Обработка найденных файлов
                for ext, desc, name, content in matches:
                    # Нормализуем имя файла
                    if not name or name.strip() == "":
                        # Определяем имя файла из расширения
                        if ext.lower() in ["powershell", "ps1"]:
                            name = "WindowsOptimizer.ps1"
                        elif ext.lower() in ["batch", "bat", "cmd"]:
                            name = "Start-Optimizer.bat"
                        elif ext.lower() in ["markdown", "md"]:
                            name = "README.md"
                        else:
                            name = f"file.{ext}"
                    
                    # Добавляем расширение, если его нет
                    if not name.endswith(f".{ext}") and ext.lower() in ["ps1", "bat", "md"]:
                        name = f"{name}.{ext}"
                    
                    files[name] = content
            
            logger.info(f"Извлечено {len(files)} файлов из ответа")
            return files
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении файлов: {e}", exc_info=True)
            return {}
    
    async def send_script_files_to_user(self, chat_id, files):
        """Отправляет сгенерированные файлы пользователю в виде архива"""
        try:
            if not files:
                bot.send_message(chat_id, "Не удалось создать файлы скриптов.")
                return False
            
            # Создаем ZIP-архив в памяти
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for filename, content in files.items():
                    # Записываем файлы в архив (с правильной кодировкой)
                    zip_file.writestr(filename, content)
                
                # Добавляем инструкции в архив
                instructions = """# Инструкция по использованию скриптов оптимизации

1. Распакуйте все файлы из архива в отдельную папку на вашем компьютере.
2. Для запуска оптимизации просто запустите файл Start-Optimizer.bat от имени администратора.
3. Следуйте инструкциям, которые появятся в консоли.

## Важно:
- Перед запуском создайте точку восстановления системы.
- Скрипты создают резервные копии измененных параметров в папке WindowsOptimizer_Backups.
- Все действия скриптов записываются в лог-файл в папке WindowsOptimizer_Logs.

Если у вас возникнут проблемы, используйте команду /help для получения справки."""
                
                zip_file.writestr("КАК_ИСПОЛЬЗОВАТЬ.txt", instructions)
            
            # Сбрасываем указатель буфера на начало
            zip_buffer.seek(0)
            
            # Отправляем архив пользователю
            bot.send_document(
                chat_id=chat_id,
                document=zip_buffer,
                caption="✅ Скрипты оптимизации созданы! Распакуйте архив и запустите Start-Optimizer.bat от имени администратора.",
                visible_file_name="WindowsOptimizer.zip"
            )
            
            # Отправляем дополнительное сообщение с инструкциями
            bot.send_message(
                chat_id=chat_id,
                text="📝 *Инструкция по использованию:*\n\n"
                     "1. Распакуйте все файлы из архива в отдельную папку\n"
                     "2. Запустите файл Start-Optimizer.bat от имени администратора\n"
                     "3. Дождитесь завершения работы скрипта\n\n"
                     "ℹ️ Если возникнут ошибки при запуске скрипта, отправьте мне скриншот с ошибкой.",
                parse_mode="Markdown"
            )
            
            # Обновляем состояние пользователя
            user_states[chat_id] = "main_menu"
            
            return True
        
        except Exception as e:
            logger.error(f"Ошибка при отправке файлов пользователю: {e}", exc_info=True)
            bot.send_message(
                chat_id=chat_id, 
                text=f"❌ Произошла ошибка при отправке файлов: {str(e)}"
            )
            return False

    async def fix_script_errors(self, message):
        """Генерация скриптов с улучшенным промптом после обнаружения ошибок"""
        try:
            logger.info(f"Начинаю исправление ошибок в скрипте для пользователя {message.chat.id}")
            
            # Проверяем наличие фото
            if not message.photo:
                return "Не найдено изображение с ошибкой. Пожалуйста, отправьте скриншот ошибки."
            
            # Получаем файл фото
            file_id = message.photo[-1].file_id
            file_info = bot.get_file(file_id)
            file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}"
            
            # Загружаем изображение
            img_data = requests.get(file_url).content
            
            # Кодируем изображение в base64
            img_base64 = base64.b64encode(img_data).decode('utf-8')
            
            # Формируем сообщение для API
            user_message = user_messages.get(message.chat.id, "Исправь ошибки в скрипте, показанные на скриншоте")
            
            # Используем оптимизированный промпт исправления ошибок
            prompt = self.error_fix_prompt
            
            messages = [
                {
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": prompt + "\n\n" + user_message},
                        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": img_base64}}
                    ]
                }
            ]
            
            logger.info("Отправляю запрос к Claude API для исправления ошибок...")
            
            # Отправляем запрос к Claude
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-3-opus-20240229",
                max_tokens=4000,
                messages=messages
            )
            
            # Обрабатываем ответ
            response_text = response.content[0].text
            
            logger.info(f"Получен ответ от Claude API, длина: {len(response_text)} символов")
            
            # Извлекаем файлы из ответа
            files = self.extract_files(response_text)
            
            if not files:
                logger.warning("Не удалось извлечь исправленные файлы из ответа API")
                return "Не удалось исправить ошибки в скриптах. Пожалуйста, попробуйте еще раз или отправьте другое изображение."
            
            # Валидация и улучшение скриптов
            validation_results = self.validator.validate_scripts(files)
            
            # Подсчитываем количество ошибок
            error_count = 0
            for filename, issues in validation_results.items():
                error_count += len(issues)
            
            # Обновляем статистику ошибок
            self.update_error_stats(validation_results)
            
            # Если остались ошибки, пытаемся их исправить
            if error_count > 0:
                logger.info(f"После исправления APIом осталось {error_count} ошибок, применяю автоматические исправления")
                files = self.validator.repair_common_issues(files)
                
                # Повторная валидация после исправлений
                validation_results = self.validator.validate_scripts(files)
                
                # Снова считаем ошибки
                fixed_error_count = 0
                for filename, issues in validation_results.items():
                    fixed_error_count += len(issues)
                
                logger.info(f"После исправлений осталось {fixed_error_count} ошибок")
            
            # Улучшаем скрипты (добавляем документацию, логирование и т.д.)
            files = self.validator.enhance_scripts(files)
            
            # Обновляем счетчик исправленных скриптов
            script_gen_count += 1
            
            # Обновляем статистику
            self.metrics.record_script_generation({
                "timestamp": datetime.now().isoformat(),
                "errors": validation_results,
                "error_count": error_count,
                "fixed_count": error_count - fixed_error_count if 'fixed_error_count' in locals() else 0,
                "model": "claude-3-opus-20240229",
                "is_error_fix": True
            })
            
            # Сохраняем файлы для последующей отправки
            user_files[message.chat.id] = files
            
            return files
        
        except Exception as e:
            logger.error(f"Ошибка при исправлении скрипта: {e}", exc_info=True)
            return f"Произошла ошибка при исправлении скрипта: {str(e)}"
    
    def update_error_stats(self, validation_results):
        """Обновляет статистику ошибок для оптимизации промптов"""
        global error_stats
        
        error_count = 0
        for filename, issues in validation_results.items():
            for issue in issues:
                error_count += 1
                
                # Определяем тип ошибки
                if "PowerShell" in issue and any(syntax in issue for syntax in ["синтаксис", "скобки", "незакрытые"]):
                    error_stats["ps_syntax"] += 1
                    self.error_types.setdefault("ps_syntax", 0)
                    self.error_types["ps_syntax"] += 1
                    
                elif "Batch" in issue and "синтаксис" in issue:
                    error_stats["bat_syntax"] += 1
                    self.error_types.setdefault("bat_syntax", 0)
                    self.error_types["bat_syntax"] += 1
                    
                elif any(access in issue for access in ["файл", "доступ", "Test-Path"]):
                    error_stats["file_access"] += 1
                    self.error_types.setdefault("file_access", 0)
                    self.error_types["file_access"] += 1
                    
                elif any(security in issue for security in ["безопасность", "права"]):
                    error_stats["security"] += 1
                    self.error_types.setdefault("security", 0)
                    self.error_types["security"] += 1
                    
                elif "обязательный блок" in issue:
                    error_stats["missing_blocks"] += 1
                    self.error_types.setdefault("missing_blocks", 0)
                    self.error_types["missing_blocks"] += 1
                    
                else:
                    error_stats["other"] += 1
                    self.error_types.setdefault("other", 0)
                    self.error_types["other"] += 1
        
        # Обновляем общий счетчик ошибок
        error_stats["total_errors"] += error_count
        self.total_errors += error_count 

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def cmd_start(message):
    """Начало взаимодействия с ботом"""
    try:
        # Сбрасываем все предыдущие состояния пользователя
        user_states[message.chat.id] = "main_menu"
        
        # Создаем клавиатуру для выбора режима
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        btn1 = types.KeyboardButton("🔧 Создать скрипт оптимизации")
        btn2 = types.KeyboardButton("🔨 Исправить ошибки в скрипте")
        markup.add(btn1, btn2)
        
        # Приветственное сообщение
        bot.send_message(
            message.chat.id,
            f"👋 Привет, {message.from_user.first_name}!\n\n"
            "Я бот для создания скриптов оптимизации Windows.\n\n"
            "Что вы хотите сделать?",
            reply_markup=markup
        )
        
        logger.info(f"Пользователь {message.chat.id} запустил бота")
    except Exception as e:
        logger.error(f"Ошибка в обработчике команды /start: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при запуске бота. Пожалуйста, попробуйте снова.")

# Обработчик для выбора пользователя
@bot.message_handler(func=lambda message: user_states.get(message.chat.id) == "main_menu")
def handle_user_choice(message):
    try:
        if "создать скрипт" in message.text.lower():
            # Переходим к созданию скрипта
            user_states[message.chat.id] = "waiting_for_screenshot"
            
            # Сохраняем текст сообщения для последующего определения режима
            user_messages[message.chat.id] = "Создай скрипт оптимизации Windows на основе этого скриншота"
            
            # Запрашиваем скриншот
            bot.send_message(
                message.chat.id,
                "📸 Отправьте скриншот с информацией о вашей системе (например, из приложения 'Сведения о системе' или 'Диспетчер задач').",
                reply_markup=types.ReplyKeyboardRemove()
            )
            
            logger.info(f"Пользователь {message.chat.id} выбрал создание скрипта оптимизации")
            
        elif "исправить ошибки" in message.text.lower():
            # Переходим к исправлению ошибок
            user_states[message.chat.id] = "waiting_for_error_screenshot"
            
            # Сохраняем текст сообщения для последующего определения режима
            user_messages[message.chat.id] = "Исправь ошибки в скрипте, показанные на этом скриншоте"
            
            # Запрашиваем скриншот с ошибкой
            bot.send_message(
                message.chat.id,
                "📸 Отправьте скриншот с ошибкой, которую нужно исправить.",
                reply_markup=types.ReplyKeyboardRemove()
            )
            
            logger.info(f"Пользователь {message.chat.id} выбрал исправление ошибок в скрипте")
            
        else:
            bot.send_message(
                message.chat.id,
                "Пожалуйста, выберите один из вариантов на клавиатуре.",
            )
    except Exception as e:
        logger.error(f"Ошибка в обработчике выбора пользователя: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, попробуйте снова.")

# Обработчик команды /help
@bot.message_handler(commands=['help'])
def cmd_help(message):
    """Отправка справочной информации"""
    try:
        help_text = """
📚 *Как использовать бота для оптимизации Windows*

*Для создания скриптов оптимизации:*
1. Нажмите на кнопку "🔧 Создать скрипт оптимизации"
2. Отправьте скриншот со сведениями о вашей системе
3. Дождитесь генерации скриптов
4. Скачайте ZIP-архив с готовыми скриптами
5. Запустите Start-Optimizer.bat от имени администратора

*Для исправления ошибок в скрипте:*
1. Нажмите на кнопку "🔨 Исправить ошибки в скрипте"
2. Отправьте скриншот с ошибкой
3. Дождитесь исправления скриптов
4. Скачайте ZIP-архив с исправленными скриптами

*Дополнительные команды:*
/start - начать работу с ботом
/help - показать эту справку
/stats - показать статистику по скриптам
/update_prompts - обновить шаблоны промптов
/cancel - отменить текущую операцию

*Важно:* Перед запуском скриптов оптимизации рекомендуется создать точку восстановления системы.
"""
        bot.send_message(message.chat.id, help_text, parse_mode="Markdown")
        logger.info(f"Пользователь {message.chat.id} запросил справку")
    except Exception as e:
        logger.error(f"Ошибка в обработчике команды /help: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при отправке справки. Пожалуйста, попробуйте снова.")

# Обработчик команды /cancel
@bot.message_handler(commands=['cancel'])
def cmd_cancel(message):
    """Отмена текущей операции"""
    try:
        # Сбрасываем состояние пользователя
        user_states[message.chat.id] = "main_menu"
        
        # Возвращаем главное меню
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        btn1 = types.KeyboardButton("🔧 Создать скрипт оптимизации")
        btn2 = types.KeyboardButton("🔨 Исправить ошибки в скрипте")
        markup.add(btn1, btn2)
        
        bot.send_message(
            message.chat.id,
            "❌ Текущая операция отменена. Выберите, что вы хотите сделать:",
            reply_markup=markup
        )
        
        logger.info(f"Пользователь {message.chat.id} отменил текущую операцию")
    except Exception as e:
        logger.error(f"Ошибка в обработчике команды /cancel: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при отмене операции. Пожалуйста, попробуйте снова.")

# Обработчик для скриншотов с ошибками
@bot.message_handler(content_types=['photo'], func=lambda message: user_states.get(message.chat.id) == "waiting_for_error_screenshot")
def process_error_photo(message):
    """Исправление ошибок в скрипте на основе скриншота ошибки"""
    try:
        # Сообщаем пользователю, что начали обработку
        processing_msg = bot.send_message(
            message.chat.id,
            "🔍 Анализирую ошибку на скриншоте...",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
        # Создаем экземпляр бота
        optimization_bot = OptimizationBot(ANTHROPIC_API_KEY)
        
        # Вызываем асинхронную функцию через asyncio.run
        result = asyncio.run(optimization_bot.fix_script_errors(message))
        
        if isinstance(result, dict) and len(result) > 0:
            # Сообщаем об успешном исправлении
            try:
                bot.edit_message_text(
                    "✅ Ошибки успешно исправлены! Создаю ZIP-архив с исправленными скриптами...",
                    message.chat.id,
                    processing_msg.message_id
                )
            except telebot.apihelper.ApiTelegramException as api_error:
                if "message can't be edited" in str(api_error):
                    logger.warning(f"Не удалось отредактировать сообщение - сообщение не может быть отредактировано")
                    # Отправляем новое сообщение вместо редактирования
                    bot.send_message(
                        message.chat.id,
                        "✅ Ошибки успешно исправлены! Создаю ZIP-архив с исправленными скриптами..."
                    )
                else:
                    raise
            except Exception as edit_error:
                logger.warning(f"Не удалось отредактировать сообщение: {edit_error}")
                # Отправляем новое сообщение вместо редактирования
                bot.send_message(
                    message.chat.id,
                    "✅ Ошибки успешно исправлены! Создаю ZIP-архив с исправленными скриптами..."
                )
            
            # Отправляем файлы пользователю
            asyncio.run(optimization_bot.send_script_files_to_user(message.chat.id, result))
            
            # Возвращаем в главное меню
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            btn1 = types.KeyboardButton("🔧 Создать скрипт оптимизации")
            btn2 = types.KeyboardButton("🔨 Исправить ошибки в скрипте")
            markup.add(btn1, btn2)
            
            bot.send_message(
                message.chat.id,
                "Что еще вы хотите сделать?",
                reply_markup=markup
            )
            
            # Сбрасываем состояние
            user_states[message.chat.id] = "main_menu"
            
        else:
            # В случае ошибки
            try:
                bot.edit_message_text(
                    f"❌ {result}",
                    message.chat.id,
                    processing_msg.message_id
                )
            except telebot.apihelper.ApiTelegramException as api_error:
                if "message can't be edited" in str(api_error):
                    logger.warning(f"Не удалось отредактировать сообщение - сообщение не может быть отредактировано")
                    # Отправляем новое сообщение вместо редактирования
                    bot.send_message(
                        message.chat.id,
                        f"❌ {result}"
                    )
                else:
                    raise
            except Exception as edit_error:
                logger.warning(f"Не удалось отредактировать сообщение: {edit_error}")
                # Отправляем новое сообщение вместо редактирования
                bot.send_message(
                    message.chat.id,
                    f"❌ {result}"
                )
            
            # Предлагаем попробовать снова
            bot.send_message(
                message.chat.id,
                "Пожалуйста, отправьте более четкий скриншот с ошибкой или вернитесь в главное меню с помощью команды /cancel."
            )
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике фото с ошибкой: {e}", exc_info=True)
        bot.send_message(
            message.chat.id,
            f"❌ Произошла ошибка при обработке фото: {str(e)}\n\nПопробуйте отправить другой скриншот или вернитесь в главное меню с помощью команды /cancel."
        )

# Обработчик для скриншотов с системной информацией
@bot.message_handler(content_types=['photo'], func=lambda message: user_states.get(message.chat.id) == "waiting_for_screenshot")
def process_photo(message):
    try:
        # Сообщаем пользователю, что начали обработку
        processing_msg = bot.send_message(
            message.chat.id,
            "🔍 Анализирую скриншот и генерирую скрипты оптимизации...",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
        # Создаем экземпляр бота
        optimization_bot = OptimizationBot(ANTHROPIC_API_KEY)
        
        # Вызываем асинхронную функцию через asyncio.run
        result = asyncio.run(optimization_bot.generate_new_script(message))
        
        if isinstance(result, dict) and len(result) > 0:
            # Сообщаем об успешной генерации
            try:
                bot.edit_message_text(
                    "✅ Скрипты успешно созданы! Создаю ZIP-архив с файлами...",
                    message.chat.id,
                    processing_msg.message_id
                )
            except telebot.apihelper.ApiTelegramException as api_error:
                if "message can't be edited" in str(api_error):
                    logger.warning(f"Не удалось отредактировать сообщение - сообщение не может быть отредактировано")
                    # Отправляем новое сообщение вместо редактирования
                    bot.send_message(
                        message.chat.id,
                        "✅ Скрипты успешно созданы! Создаю ZIP-архив с файлами..."
                    )
                else:
                    raise
            except Exception as edit_error:
                logger.warning(f"Не удалось отредактировать сообщение: {edit_error}")
                # Отправляем новое сообщение вместо редактирования
                bot.send_message(
                    message.chat.id,
                    "✅ Скрипты успешно созданы! Создаю ZIP-архив с файлами..."
                )
            
            # Отправляем файлы пользователю
            asyncio.run(optimization_bot.send_script_files_to_user(message.chat.id, result))
            
            # Возвращаем в главное меню
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            btn1 = types.KeyboardButton("🔧 Создать скрипт оптимизации")
            btn2 = types.KeyboardButton("🔨 Исправить ошибки в скрипте")
            markup.add(btn1, btn2)
            
            bot.send_message(
                message.chat.id,
                "Что еще вы хотите сделать?",
                reply_markup=markup
            )
            
            # Сбрасываем состояние
            user_states[message.chat.id] = "main_menu"
            
        else:
            # В случае ошибки
            try:
                bot.edit_message_text(
                    f"❌ {result}",
                    message.chat.id,
                    processing_msg.message_id
                )
            except telebot.apihelper.ApiTelegramException as api_error:
                if "message can't be edited" in str(api_error):
                    logger.warning(f"Не удалось отредактировать сообщение - сообщение не может быть отредактировано")
                    # Отправляем новое сообщение вместо редактирования
                    bot.send_message(
                        message.chat.id,
                        f"❌ {result}"
                    )
                else:
                    raise
            except Exception as edit_error:
                logger.warning(f"Не удалось отредактировать сообщение: {edit_error}")
                # Отправляем новое сообщение вместо редактирования
                bot.send_message(
                    message.chat.id,
                    f"❌ {result}"
                )
            
            # Предлагаем попробовать снова
            bot.send_message(
                message.chat.id,
                "Пожалуйста, отправьте более четкий скриншот с системной информацией или вернитесь в главное меню с помощью команды /cancel."
            )
        
    except Exception as e:
        logger.error(f"Ошибка в обработчике фото: {e}", exc_info=True)
        bot.send_message(
            message.chat.id,
            f"❌ Произошла ошибка при обработке фото: {str(e)}\n\nПопробуйте отправить другой скриншот или вернитесь в главное меню с помощью команды /cancel."
        )

# Обработчик для текстовых сообщений в других состояниях
@bot.message_handler(func=lambda message: user_states.get(message.chat.id) in ["waiting_for_screenshot", "waiting_for_error_screenshot"])
def handle_text_in_photo_states(message):
    """Обработка текстовых сообщений"""
    try:
        # Сохраняем текст сообщения
        user_messages[message.chat.id] = message.text
        
        # Определяем текущее состояние
        state = user_states.get(message.chat.id)
        
        if state == "waiting_for_screenshot":
            bot.send_message(
                message.chat.id,
                "📸 Отправьте скриншот с информацией о вашей системе.\n\n"
                "Ваше описание сохранено и будет использовано при генерации скрипта."
            )
        elif state == "waiting_for_error_screenshot":
            bot.send_message(
                message.chat.id,
                "📸 Отправьте скриншот с ошибкой, которую нужно исправить.\n\n"
                "Ваше описание сохранено и будет использовано при исправлении скрипта."
            )
    except Exception as e:
        logger.error(f"Ошибка в обработчике текстовых сообщений: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка. Пожалуйста, попробуйте снова.")

# Обработчик команды /stats
@bot.message_handler(commands=['stats'])
def cmd_stats(message):
    """Команда для получения статистики по скриптам"""
    try:
        # Формируем статистику
        stats_text = "📊 *Статистика генерации скриптов*\n\n"
        
        # Общая статистика
        stats_text += f"Всего сгенерировано скриптов: *{script_gen_count}*\n"
        stats_text += f"Всего ошибок обнаружено: *{error_stats['total_errors']}*\n\n"
        
        # Статистика по типам ошибок (сортировка по частоте)
        stats_text += "*Типы ошибок:*\n"
        
        # Сортируем ошибки по количеству
        error_types_sorted = sorted(
            [
                ("Синтаксис PowerShell", error_stats["ps_syntax"]),
                ("Синтаксис Batch", error_stats["bat_syntax"]),
                ("Доступ к файлам", error_stats["file_access"]),
                ("Безопасность", error_stats["security"]),
                ("Отсутствующие блоки", error_stats["missing_blocks"]),
                ("Другие", error_stats["other"])
            ],
            key=lambda x: x[1],
            reverse=True
        )
        
        # Выводим только ненулевые значения
        for error_type, count in error_types_sorted:
            if count > 0:
                stats_text += f"- {error_type}: *{count}*\n"
        
        # Статистика PowerShell vs Batch
        ps_errors = error_stats["ps_syntax"] + error_stats["file_access"] + error_stats["security"]
        bat_errors = error_stats["bat_syntax"]
        
        if ps_errors > 0 or bat_errors > 0:
            stats_text += f"\n*Распределение ошибок:*\n"
            stats_text += f"- PowerShell: *{ps_errors}* ошибок\n"
            stats_text += f"- Batch: *{bat_errors}* ошибок\n"
        
        # Отправляем статистику
        bot.send_message(message.chat.id, stats_text, parse_mode="Markdown")
        
        logger.info(f"Пользователь {message.chat.id} запросил статистику")
    except Exception as e:
        logger.error(f"Ошибка в обработчике команды /stats: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при получении статистики. Пожалуйста, попробуйте снова.")

# Обработчик команды для принудительного обновления промптов
@bot.message_handler(commands=['update_prompts'])
def cmd_update_prompts(message):
    """Команда для обновления промптов"""
    try:
        # Создаем экземпляр оптимизатора промптов
        optimizer = PromptOptimizer()
        
        # Пытаемся обновить промпты
        updated = optimizer.update_prompts_based_on_metrics()
        
        if updated:
            bot.send_message(
                message.chat.id,
                "✅ Промпты успешно обновлены на основе накопленных данных"
            )
        else:
            bot.send_message(
                message.chat.id,
                "ℹ️ Промпты не были обновлены. Недостаточно данных для оптимизации."
            )
    except Exception as e:
        logger.error(f"Ошибка при обновлении промптов: {e}")
        bot.send_message(
            message.chat.id,
            f"❌ Ошибка при обновлении промптов: {str(e)}"
        )

def main():
    """Запуск бота"""
    try:
        logger.info("Запуск бота...")
        
        # Инициализация оптимизатора промптов
        prompt_optimizer = PromptOptimizer()
        
        # Попытка обновления промптов на основе накопленных данных
        updated = prompt_optimizer.update_prompts_based_on_metrics()
        if updated:
            logger.info("Промпты успешно обновлены на основе накопленных данных")
        else:
            logger.info("Промпты не были обновлены, используются стандартные шаблоны")
            
        # Вывод статистики для логов
        logger.info("Статистика по скриптам:")
        logger.info(f"Всего сгенерировано скриптов: {script_gen_count}")
        
        total_errors = error_stats["total_errors"]
        logger.info(f"Обнаружено ошибок: {total_errors}")
        
        # Запуск бота
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main() 