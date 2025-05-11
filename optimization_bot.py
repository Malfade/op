import os
import logging
import sys
import json
import base64
from io import BytesIO
from datetime import datetime
import zipfile
import requests

# Настройка базового логирования для вывода сообщений о зависимостях
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Проверка наличия необходимых зависимостей
required_packages = {
    "telebot": "pyTelegramBotAPI",
    "anthropic": "anthropic",
    "aiohttp": "aiohttp",
    "asyncio": "asyncio",
    "dotenv": "python-dotenv",
}

missing_packages = []

for module_name, package_name in required_packages.items():
    try:
        __import__(module_name)
    except ImportError:
        missing_packages.append(package_name)

if missing_packages:
    logger.error(f"Отсутствуют необходимые зависимости: {', '.join(missing_packages)}")
    logger.error("Установите их с помощью команды: pip install -r requirements.txt")
    sys.exit(1)

# Импорт зависимостей после проверки
import anthropic
import telebot
from telebot import types
from telebot.types import Message, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
import aiohttp
import asyncio

# Импорт локальных модулей
try:
    from script_validator import ScriptValidator
    from script_metrics import ScriptMetrics
    from prompt_optimizer import PromptOptimizer
except ImportError as e:
    logger.error(f"Ошибка при импорте локальных модулей: {e}")
    logger.error("Убедитесь, что все файлы проекта находятся в одной директории")
    sys.exit(1)

# Загрузка переменных окружения из .env файла
load_dotenv()

# Получение токенов и параметров из переменных окружения
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
CLAUDE_MODEL = os.getenv('CLAUDE_MODEL', 'claude-3-5-sonnet-20240620')

# Список разрешенных пользователей (пустой список - доступ для всех)
ALLOWED_USERS = os.getenv('ALLOWED_USERS', '').strip()
ALLOWED_USERS_LIST = [int(user_id.strip()) for user_id in ALLOWED_USERS.split(',') if user_id.strip().isdigit()] if ALLOWED_USERS else []
ADMIN_USER_ID = os.getenv('ADMIN_USER_ID', '').strip()
ADMIN_USER_ID = int(ADMIN_USER_ID) if ADMIN_USER_ID.isdigit() else None

# Включен ли режим ограничения доступа
RESTRICTED_ACCESS = bool(ALLOWED_USERS_LIST) or bool(ADMIN_USER_ID)

if RESTRICTED_ACCESS:
    logger.info(f"Режим ограниченного доступа включен. Разрешенные пользователи: {ALLOWED_USERS_LIST}")
    if ADMIN_USER_ID:
        logger.info(f"Администратор: {ADMIN_USER_ID}")
else:
    logger.info("Режим ограниченного доступа отключен. Доступ разрешен всем пользователям.")

# Настройка логирования на основе параметров из .env
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_PATH = os.getenv('LOG_PATH', '.')

# Создаем директорию для логов, если она не существует
if not os.path.exists(LOG_PATH):
    try:
        os.makedirs(LOG_PATH)
    except Exception as e:
        logger.warning(f"Не удалось создать директорию для логов: {e}. Будет использована текущая директория.")
        LOG_PATH = '.'

# Настройка расширенного логирования
numeric_level = getattr(logging, LOG_LEVEL.upper(), None)
if not isinstance(numeric_level, int):
    numeric_level = logging.INFO
    logger.warning(f"Некорректный уровень логирования {LOG_LEVEL}, используется INFO")

# Настраиваем логирование с сохранением в файл
log_file = os.path.join(LOG_PATH, f"windows_optimizer_bot_{datetime.now().strftime('%Y%m%d')}.log")
logging.basicConfig(
    level=numeric_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

# Проверка наличия токенов
if not TELEGRAM_TOKEN or not ANTHROPIC_API_KEY:
    logger.error("Не удалось загрузить токены из .env файла. Убедитесь, что файл .env настроен правильно.")
    sys.exit(1)

# Базовые шаблоны промптов (перенесены из base_prompts.json для прямого доступа)
OPTIMIZATION_PROMPT_TEMPLATE = """
Ты эксперт по оптимизации Windows. Проанализируй скриншот системной информации и создай универсальные скрипты для оптимизации Windows 10 и Windows 11.

Создай следующие файлы:
1. PowerShell скрипт (WindowsOptimizer.ps1) с детальной оптимизацией
2. Batch файл (Start-Optimizer.bat) для запуска PowerShell скрипта с правами администратора
3. README.txt с пояснениями по использованию

Обязательно включи в PowerShell скрипт:
- Проверку прав администратора
- Создание резервной копии настроек перед изменениями
- Меню с различными опциями оптимизаций
- Обработку ошибок через try-catch
- Проверку наличия файлов перед их использованием (Test-Path)
- Добавь комментарии к важным операциям

Batch файл должен содержать:
- Установку кодировки UTF-8 (chcp 65001)
- Проверку наличия файла PowerShell скрипта
- Запуск PowerShell с правами администратора и обходом политики выполнения
- Обработку ошибок

README.txt должен содержать:
- Пояснения по назначению скриптов
- Инструкцию по запуску
- Меры предосторожности
- Описание функций оптимизации

Предоставь три файла: WindowsOptimizer.ps1, Start-Optimizer.bat и README.txt
"""

ERROR_FIX_PROMPT_TEMPLATE = """
Ты эксперт по оптимизации Windows и скриптам PowerShell/Batch. Мне нужно исправить ошибки в следующих скриптах:

{script_files}

Ошибки и проблемы, которые нужно исправить:
{error_details}

Важно:
1. Исправь все найденные ошибки, сохраняя основную функциональность скриптов
2. Добавь проверки и обработку ошибок там, где их не хватает
3. Не добавляй новых функций, только исправь существующие проблемы
4. Используй правильные практики программирования для Windows
5. Сделай код более безопасным, проверяя наличие файлов перед их использованием
6. Обязательно добавь обработку ошибок через try-catch для всех потенциально опасных операций
7. В batch файле убедись в наличии проверки прав администратора и установки кодировки UTF-8

Предоставь исправленные версии файлов:
"""

# Класс для обработки оптимизации Windows
class OptimizationBot:
    """Класс для управления ботом оптимизации Windows"""
    
    def __init__(self, token, api_key, model="claude-3-5-sonnet-20240620"):
        """Инициализация бота с заданными токенами"""
        self.token = token
        self.api_key = api_key
        self.model = model
        
        # Инициализация клиентов
        self.bot = telebot.TeleBot(token)
        self.claude_client = anthropic.Anthropic(api_key=self.api_key)
        
        # Состояния пользователей
        self.user_states = {}
        self.user_files = {}
        self.user_message_texts = {}  # Для хранения текстов сообщений пользователей
        
        # Статистика генераций и ошибок
        self.script_gen_count = 0
        self.script_fix_count = 0
        self.error_stats = {
            "total_errors": 0,
            "missing_file_checks": 0,
            "missing_error_handling": 0,
            "missing_admin_checks": 0,
            "encoding_issues": 0,
            "syntax_errors": 0,
            "missing_backup": 0,
            "other_errors": 0,
            "powershell_errors": 0,
            "batch_errors": 0
        }
        
        # Инициализация оптимизатора промптов
        self.prompt_optimizer = PromptOptimizer()
        self.script_validator = ScriptValidator()
        
        # Загрузка шаблона промпта из глобального пространства имен
        self.OPTIMIZATION_PROMPT_TEMPLATE = OPTIMIZATION_PROMPT_TEMPLATE
        self.ERROR_FIX_PROMPT_TEMPLATE = ERROR_FIX_PROMPT_TEMPLATE

    async def generate_new_script(self, message):
        """Генерация нового скрипта оптимизации на основе скриншота системы"""
        # Устанавливаем состояние "генерация скриптов"
        await self.bot.send_message(message.chat.id, "⏳ Анализирую изображение и генерирую универсальные скрипты оптимизации... Это может занять несколько минут.")
        
        # Получение файла фото с наилучшим разрешением
        photo = message.photo[-1]
        file_info = await self.bot.get_file(photo.file_id)
        file_url = f"https://api.telegram.org/file/bot{self.token}/{file_info.file_path}"
        
        # Загрузка фото
        async with aiohttp.ClientSession() as session:
            async with session.get(file_url) as response:
                photo_bytes = BytesIO(await response.read())
        
        # Кодирование изображения в base64 для передачи в Claude
        photo_base64 = base64.b64encode(photo_bytes.read()).decode('utf-8')
        
        # Формирование запроса к Claude с изображением
        logging.info("Отправка запроса к API Claude...")
        system_info_text = self.OPTIMIZATION_PROMPT_TEMPLATE
        
        try:
            # Запрос к API Claude с использованием нового API (messages.create)
            response = self.claude_client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {
                        "role": "user", 
                        "content": [
                            {
                                "type": "text", 
                                "text": system_info_text
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64", 
                                    "media_type": "image/jpeg", 
                                    "data": photo_base64
                                }
                            }
                        ]
                    }
                ]
            )
            
            logging.info(f"Получен ответ от API Claude, статус: успешно, модель: {self.model}")
            
            # Проверка структуры ответа
            if not hasattr(response, 'content') or not response.content:
                logging.error("Некорректная структура ответа API: отсутствует content")
                await message.reply("Ошибка при получении ответа от API. Пожалуйста, попробуйте позже.")
                return
                
            if not response.content or len(response.content) == 0:
                logging.error("Пустой content в ответе API")
                await message.reply("Получен пустой ответ от API. Пожалуйста, попробуйте позже.")
                return
                
            # Используем полученный текст как ответ
            response_text = response.content[0].text
            logging.info(f"Длина полученного текста: {len(response_text or '')} символов")
            
            # Извлекаем файлы из ответа API
            if response_text:
                script_files = extract_files_from_response(response_text)
                if not script_files:
                    logging.error(f"Не удалось извлечь файлы из ответа: {response_text[:200]}")
                    await message.reply("Не удалось сгенерировать скрипты. Пожалуйста, попробуйте еще раз или обратитесь к разработчику.")
                    return
                
                # Валидация и исправление скриптов
                validation_results = self.script_validator.validate_files(script_files)
                
                # Улучшаем скрипты перед исправлением
                script_files = self.script_validator.enhance_scripts(script_files)
                
                # Если есть ошибки, исправляем их
                if sum(len(errors) for errors in validation_results.values()) > 0:
                    logging.info(f"Найдены ошибки в скриптах: {validation_results}")
                    # Записываем статистику ошибок
                    self.update_error_stats(validation_results)
                    
                    # Исправляем ошибки
                    repaired_files = self.script_validator.repair_common_issues(script_files)
                    
                    # Повторная валидация после исправления
                    new_validation_results = self.script_validator.validate_files(repaired_files)
                    logging.info(f"Результаты повторной валидации: {new_validation_results}")
                    
                    if self.script_validator.should_regenerate_script(new_validation_results):
                        logging.warning("Слишком много ошибок в скриптах, регенерация...")
                        await message.reply("Найдены критические ошибки в скриптах. Запускаю повторную генерацию...")
                        # Регенерация скриптов с использованием другого промпта
                        self.prompt_optimizer.update_metrics('regeneration_required', 1)
                        await self.generate_with_improved_prompt(message, system_info_text)
                        return
                    
                    script_files = repaired_files
                
                # Отправка файлов пользователю
                await self.send_script_files_to_user(message, script_files)
                
                # Обновление глобальной статистики успешных генераций
                global script_gen_count
                script_gen_count += 1
                
                # Обновляем метрики для оптимизатора промптов
                self.prompt_optimizer.update_metrics('successful_generations', 1)
                
            else:
                logging.error("Пустой ответ от API")
                await message.reply("Не удалось сгенерировать скрипты. Пожалуйста, попробуйте еще раз или обратитесь к разработчику.")
                
                # Обновляем метрики для оптимизатора промптов
                self.prompt_optimizer.update_metrics('empty_responses', 1)
                
        except Exception as e:
            logging.error(f"Ошибка при генерации скриптов: {str(e)}")
            await message.reply(f"❌ Произошла ошибка при генерации скриптов: {str(e)[:100]}...\nПожалуйста, попробуйте снова.")
            self.prompt_optimizer.update_metrics('errors', 1)
    
    async def send_script_files_to_user(self, message, files):
        """Отправляет сгенерированные файлы пользователю в виде архива"""
        try:
            # Сохраняем файлы пользователя в словарь экземпляра класса
            self.user_files[message.chat.id] = files
            
            # Создание ZIP-архива с файлами
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_name, file_content in files.items():
                    zip_file.writestr(file_name, file_content)
            
            zip_buffer.seek(0)
            
            # Отправка ZIP-архива пользователю через бот экземпляра класса
            now = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            await self.bot.send_document(
                message.chat.id,
                types.InputFile(zip_buffer, filename=f"WindowsOptimizer_{now}.zip"),
                caption=(
                    "✅ Скрипты оптимизации Windows успешно созданы!\n\n"
                    "📁 В архиве три файла:\n"
                    "1. WindowsOptimizer.ps1 - Основной скрипт PowerShell\n"
                    "2. Start-Optimizer.bat - Скрипт для запуска с правами администратора\n"
                    "3. README.txt - Инструкция по использованию\n\n"
                    "⚠️ Для запуска просто распакуйте архив и запустите Start-Optimizer.bat от имени администратора\n\n"
                    "🔍 Обнаружили ошибку в скриптах? Напишите /fix"
                )
            )
            
            # Обновляем статистику
            self.script_gen_count += 1
            
            # Сбрасываем состояние пользователя
            self.user_states[message.chat.id] = None
            
            logger.info(f"Файлы успешно отправлены пользователю {message.chat.id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке файлов пользователю: {str(e)}")
            await message.reply("❌ Произошла ошибка при отправке файлов. Пожалуйста, попробуйте снова.")
    
    async def generate_with_improved_prompt(self, message, original_prompt):
        """Генерация скриптов с улучшенным промптом после обнаружения ошибок"""
        try:
            # Получение исходного фото
            photo = message.photo[-1]
            file_info = await self.bot.get_file(photo.file_id)
            file_url = f"https://api.telegram.org/file/bot{self.token}/{file_info.file_path}"
            
            # Загрузка фото
            async with aiohttp.ClientSession() as session:
                async with session.get(file_url) as response:
                    photo_bytes = BytesIO(await response.read())
            
            # Кодирование изображения в base64
            photo_base64 = base64.b64encode(photo_bytes.read()).decode('utf-8')
            
            # Улучшенный промпт с добавлением информации об обнаруженных ошибках
            improved_prompt = original_prompt + "\n\nВ предыдущей версии скриптов были обнаружены ошибки. Пожалуйста, обрати особое внимание на следующие аспекты:\n\n"
            improved_prompt += "1. Все операции с файловой системой должны содержать проверки существования файлов (Test-Path).\n"
            improved_prompt += "2. Операции с реестром и службами должны содержать обработку ошибок (try/catch или -ErrorAction).\n"
            improved_prompt += "3. Включи функцию создания резервных копий настроек перед изменениями.\n"
            improved_prompt += "4. Batch-скрипт должен проверять наличие прав администратора и использовать кодировку UTF-8.\n"
            improved_prompt += "5. Убедись, что все строки и блоки в PowerShell правильно закрыты.\n\n"
            improved_prompt += "Пожалуйста, создай более надежную версию скриптов с учетом этих требований."
            
            logging.info("Отправка запроса с улучшенным промптом к API Claude...")
            
            # Запрос к API Claude с улучшенным промптом
            response = self.claude_client.messages.create(
                model=self.model,
                max_tokens=4000,
                messages=[
                    {
                        "role": "user", 
                        "content": [
                            {
                                "type": "text", 
                                "text": improved_prompt
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64", 
                                    "media_type": "image/jpeg", 
                                    "data": photo_base64
                                }
                            }
                        ]
                    }
                ]
            )
            
            logging.info(f"Получен ответ от API Claude с улучшенным промптом, статус: успешно")
            
            # Проверка структуры ответа
            if not hasattr(response, 'content') or not response.content:
                logging.error("Некорректная структура ответа API: отсутствует content")
                await message.reply("Ошибка при получении ответа от API. Пожалуйста, попробуйте позже.")
                return
                
            # Используем полученный текст как ответ
            improved_response_text = response.content[0].text
            logging.info(f"Длина полученного текста с улучшенным промптом: {len(improved_response_text or '')} символов")
            
            # Извлекаем файлы из ответа API
            if improved_response_text:
                improved_script_files = extract_files_from_response(improved_response_text)
                if not improved_script_files:
                    logging.error(f"Не удалось извлечь файлы из ответа с улучшенным промптом")
                    await message.reply("Не удалось сгенерировать скрипты с улучшенным промптом. Пожалуйста, попробуйте еще раз.")
                    return
                
                # Валидация улучшенных скриптов
                validation_results = self.script_validator.validate_files(improved_script_files)
                
                # Улучшаем скрипты дополнительно
                improved_script_files = self.script_validator.enhance_scripts(improved_script_files)
                
                # Если остались ошибки, исправляем их
                if sum(len(errors) for errors in validation_results.values()) > 0:
                    logging.info(f"Найдены ошибки в улучшенных скриптах: {validation_results}")
                    # Исправляем ошибки
                    improved_script_files = self.script_validator.repair_common_issues(improved_script_files)
                
                # Отправка файлов пользователю
                await self.send_script_files_to_user(message, improved_script_files)
                
                # Обновление глобальной статистики
                global script_gen_count
                script_gen_count += 1
                self.prompt_optimizer.update_metrics('regenerations_successful', 1)
                
            else:
                logging.error("Пустой ответ от API с улучшенным промптом")
                await message.reply("Не удалось сгенерировать скрипты с улучшенным промптом. Пожалуйста, попробуйте еще раз.")
                self.prompt_optimizer.update_metrics('empty_responses', 1)
                
        except Exception as e:
            logging.error(f"Ошибка при генерации скриптов с улучшенным промптом: {str(e)}")
            await message.reply(f"❌ Произошла ошибка при генерации улучшенных скриптов: {str(e)[:100]}...\nПожалуйста, попробуйте снова.")
            self.prompt_optimizer.update_metrics('errors', 1)
    
    def update_error_stats(self, validation_results):
        """Обновление статистики ошибок на основе результатов валидации

        Args:
            validation_results (dict): Словарь с результатами валидации
        """
        try:
            # Общее количество ошибок
            error_count = sum(len(issues) for issues in validation_results.values())
            self.error_stats["total_errors"] += error_count
            
            # Категоризация ошибок по типам
            for filename, issues in validation_results.items():
                for issue in issues:
                    # Определяем тип ошибки по ключевым словам
                    if "ps_syntax" in issue:
                        self.error_stats["syntax_errors"] += 1
                        self.error_stats["powershell_errors"] += 1
                    elif "bat_syntax" in issue:
                        self.error_stats["syntax_errors"] += 1
                        self.error_stats["batch_errors"] += 1
                    elif "Test-Path" in issue or "проверка" in issue:
                        self.error_stats["missing_file_checks"] += 1
                    elif "try" in issue or "catch" in issue or "обработки ошибок" in issue:
                        self.error_stats["missing_error_handling"] += 1
                    elif "администратора" in issue or "прав" in issue:
                        self.error_stats["missing_admin_checks"] += 1
                    elif "кодировк" in issue or "chcp" in issue or "UTF" in issue:
                        self.error_stats["encoding_issues"] += 1
                    elif "резерв" in issue or "backup" in issue or "точка восстановления" in issue:
                        self.error_stats["missing_backup"] += 1
                    else:
                        self.error_stats["other_errors"] += 1
            
            # Обновляем метрики в оптимизаторе промптов
            try:
                # Создаем словарь метрик на основе результатов
                metrics_data = {
                    "total_errors": error_count,
                    "script_type": "ps1" if "powershell_errors" in self.error_stats and self.error_stats["powershell_errors"] > 0 else "bat",
                    "validation_issues": sum(len(issues) for issues in validation_results.values())
                }
                
                # Обновляем метрики
                self.prompt_optimizer.update_metrics('error_detection', 1)
                if error_count > 0:
                    self.prompt_optimizer.update_metrics('with_errors', 1)
                
                logger.info(f"Метрики обновлены: {metrics_data}")
                
            except Exception as e:
                logger.error(f"Ошибка при обновлении метрик: {e}")
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении статистики ошибок: {e}")
            
        return self.error_stats

def extract_files_from_response(response_text):
    """Извлечение файлов из ответа Claude"""
    files = {}
    
    # Поиск содержимого файлов в ответе
    powershell_pattern = "```powershell\n"
    cmd_pattern = "```batch\n"
    md_pattern = "```markdown\n"
    
    # Проверка корректности данных
    if not response_text or not isinstance(response_text, str):
        logger.warning("Получен некорректный ответ от API")
        return files
    
    try:
        # Извлечение PowerShell скрипта
        if powershell_pattern in response_text:
            ps_start = response_text.find(powershell_pattern) + len(powershell_pattern)
            ps_end = response_text.find("```", ps_start)
            if ps_end > ps_start:
                files["WindowsOptimizer.ps1"] = response_text[ps_start:ps_end].strip()
        
        # Извлечение BAT скрипта
        if cmd_pattern in response_text:
            cmd_start = response_text.find(cmd_pattern) + len(cmd_pattern)
            cmd_end = response_text.find("```", cmd_start)
            if cmd_end > cmd_start:
                files["Start-Optimizer.bat"] = response_text[cmd_start:cmd_end].strip()
        
        # Если нет специфического маркера batch, поиск альтернативного
        if "Start-Optimizer.bat" not in files:
            alt_patterns = ["```cmd\n", "```bat\n", "```\n@echo off"]
            for pattern in alt_patterns:
                if pattern in response_text:
                    cmd_start = response_text.find(pattern) + len(pattern)
                    cmd_end = response_text.find("```", cmd_start)
                    if cmd_end > cmd_start:
                        content = response_text[cmd_start:cmd_end].strip()
                        if content.startswith("@echo off") or "chcp" in content:
                            files["Start-Optimizer.bat"] = content
                            break
        
        # Извлечение README.md
        if md_pattern in response_text:
            md_start = response_text.find(md_pattern) + len(md_pattern)
            md_end = response_text.find("```", md_start)
            if md_end > md_start:
                files["README.md"] = response_text[md_start:md_end].strip()
        
        # Если не найден маркер markdown, поиск README в обычном тексте
        if "README.md" not in files and "# " in response_text:
            sections = response_text.split("```")
            for section in sections:
                if section.strip().startswith("# ") or "## " in section:
                    files["README.md"] = section.strip()
                    break
    except Exception as e:
        logger.error(f"Ошибка при извлечении файлов из ответа: {e}")
    
    return files

def is_user_authorized(user_id):
    """Проверка авторизации пользователя
    
    Args:
        user_id (int): ID пользователя Telegram
        
    Returns:
        bool: True если пользователь авторизован, иначе False
    """
    if not RESTRICTED_ACCESS:
        return True
    
    if ADMIN_USER_ID and user_id == ADMIN_USER_ID:
        return True
    
    if user_id in ALLOWED_USERS_LIST:
        return True
    
    logger.warning(f"Попытка неавторизованного доступа от пользователя {user_id}")
    return False

def main():
    """Основная функция запуска бота"""
    try:
        logger.info("Запуск бота оптимизации Windows...")
        
        # Проверка наличия всех необходимых токенов
        if not TELEGRAM_TOKEN:
            logger.error("Не указан токен Telegram бота в .env файле")
            return
        
        if not ANTHROPIC_API_KEY:
            logger.error("Не указан API ключ Anthropic Claude в .env файле")
            return
        
        # Инициализация бота с использованием модели из .env
        logger.info(f"Используется модель: {CLAUDE_MODEL}")
        optimization_bot = OptimizationBot(TELEGRAM_TOKEN, ANTHROPIC_API_KEY, CLAUDE_MODEL)
        bot = optimization_bot.bot
        
        # Регистрация обработчиков команд и сообщений
        @bot.message_handler(commands=['start'])
        def cmd_start(message):
            try:
                # Проверка авторизации
                if not is_user_authorized(message.from_user.id):
                    bot.send_message(
                        message.chat.id,
                        "⛔ У вас нет доступа к этому боту. Обратитесь к администратору для получения разрешения."
                    )
                    return

                # Приветственное сообщение и базовые инструкции
                bot.send_message(
                    message.chat.id,
                    f"👋 Привет, {message.from_user.first_name}!\n\n"
                    "🖥️ Я бот для создания и исправления скриптов оптимизации Windows.\n\n"
                    "🔄 Чтобы создать скрипт оптимизации, отправьте мне скриншот сведений о системе из Панели управления.\n\n"
                    "🔧 Если вы уже создали скрипт и столкнулись с ошибкой, напишите /fix и отправьте скриншот ошибки.\n\n"
                    "❓ Для получения помощи напишите /help",
                    parse_mode='Markdown'
                )
                
                # Добавляем инструкцию, как получить сведения о системе
                bot.send_message(
                    message.chat.id,
                    "📸 *Как сделать снимок экрана сведений о системе:*\n\n"
                    "1. Нажмите Win + R, введите 'control system' и нажмите Enter\n"
                    "2. Или откройте Параметры Windows → Система → О системе\n"
                    "3. Сделайте скриншот открывшегося окна\n"
                    "4. Отправьте скриншот мне",
                    parse_mode='Markdown'
                )
                
                # Сбрасываем состояние пользователя
                optimization_bot.user_states[message.chat.id] = None
                
            except Exception as e:
                logger.error(f"Ошибка в обработчике команды start: {e}")
                bot.send_message(message.chat.id, "Произошла ошибка, пожалуйста, повторите попытку позже.")
        
        @bot.message_handler(commands=['help'])
        def cmd_help(message):
            try:
                # Проверка авторизации
                if not is_user_authorized(message.from_user.id):
                    bot.send_message(
                        message.chat.id,
                        "⛔ У вас нет доступа к этому боту. Обратитесь к администратору для получения разрешения."
                    )
                    return
                    
                bot.send_message(
                    message.chat.id,
                    "🔍 *Справка по использованию бота*\n\n"
                    "Этот бот создает скрипты оптимизации Windows на основе скриншота вашей системы "
                    "или исправляет ошибки в ранее созданных скриптах.\n\n"
                    "*Доступные команды:*\n"
                    "/start - Начать работу с ботом\n"
                    "/help - Показать эту справку\n"
                    "/fix - Режим исправления ошибок в скриптах\n"
                    "/stats - Статистика использования бота\n"
                    "/cancel - Отменить текущую операцию\n\n"
                    "*Как использовать:*\n"
                    "1. Отправьте скриншот сведений о системе для создания скриптов\n"
                    "2. Если в работе скриптов возникнут ошибки, используйте команду /fix и отправьте скриншот с ошибкой\n\n"
                    "*Рекомендации:*\n"
                    "• Используйте четкие скриншоты без обрезки\n"
                    "• Запускайте скрипты только от имени администратора\n"
                    "• Создавайте точку восстановления системы перед запуском оптимизаций",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Ошибка в обработчике команды help: {e}")
                bot.send_message(message.chat.id, "Произошла ошибка, пожалуйста, повторите попытку позже.")
        
        @bot.message_handler(commands=['cancel'])
        def cmd_cancel(message):
            try:
                # Проверка авторизации
                if not is_user_authorized(message.from_user.id):
                    bot.send_message(
                        message.chat.id,
                        "⛔ У вас нет доступа к этому боту. Обратитесь к администратору для получения разрешения."
                    )
                    return
                    
                # Сбрасываем состояние пользователя
                optimization_bot.user_states[message.chat.id] = None
                optimization_bot.user_message_texts[message.chat.id] = None
                
                bot.send_message(
                    message.chat.id,
                    "🛑 Текущая операция отменена.\n"
                    "Вы можете отправить скриншот системы для создания скриптов или использовать /fix для исправления ошибок."
                )
            except Exception as e:
                logger.error(f"Ошибка в обработчике команды cancel: {e}")
                bot.send_message(message.chat.id, "Произошла ошибка, пожалуйста, повторите попытку позже.")
        
        @bot.message_handler(commands=['fix'])
        def cmd_fix(message):
            try:
                # Проверка авторизации
                if not is_user_authorized(message.from_user.id):
                    bot.send_message(
                        message.chat.id,
                        "⛔ У вас нет доступа к этому боту. Обратитесь к администратору для получения разрешения."
                    )
                    return
                    
                # Устанавливаем состояние "ожидание скриншота ошибки"
                optimization_bot.user_states[message.chat.id] = "waiting_for_error_screenshot"
                
                bot.send_message(
                    message.chat.id,
                    "🔧 Режим исправления ошибок активирован.\n\n"
                    "Пожалуйста, отправьте скриншот с ошибкой, и я помогу её исправить.\n"
                    "Чтобы получить наилучший результат, убедитесь, что текст ошибки хорошо виден на скриншоте.",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Ошибка в обработчике команды fix: {e}")
                bot.send_message(message.chat.id, "Произошла ошибка, пожалуйста, повторите попытку позже.")
        
        @bot.message_handler(commands=['stats'])
        def cmd_stats(message):
            try:
                # Проверка авторизации
                if not is_user_authorized(message.from_user.id):
                    bot.send_message(
                        message.chat.id,
                        "⛔ У вас нет доступа к этому боту. Обратитесь к администратору для получения разрешения."
                    )
                    return
                    
                # Проверяем, является ли пользователь администратором
                if ADMIN_USER_ID and message.from_user.id != ADMIN_USER_ID:
                    bot.send_message(
                        message.chat.id,
                        "⛔ Только администратор может просматривать статистику бота."
                    )
                    return
                    
                # Выводим статистику использования бота
                stats_text = (
                    "📊 *Статистика использования бота*\n\n"
                    f"🔄 Всего сгенерировано скриптов: {optimization_bot.script_gen_count}\n"
                    f"🔧 Всего исправлено скриптов: {optimization_bot.script_fix_count}\n\n"
                    "*Статистика ошибок:*\n"
                    f"📝 Всего выявлено ошибок: {optimization_bot.error_stats['total_errors']}\n"
                    f"🔹 Отсутствие проверок файлов: {optimization_bot.error_stats['missing_file_checks']}\n"
                    f"🔹 Отсутствие обработки ошибок: {optimization_bot.error_stats['missing_error_handling']}\n"
                    f"🔹 Отсутствие проверок прав админа: {optimization_bot.error_stats['missing_admin_checks']}\n"
                    f"🔹 Проблемы с кодировкой: {optimization_bot.error_stats['encoding_issues']}\n"
                    f"🔹 Синтаксические ошибки: {optimization_bot.error_stats['syntax_errors']}\n"
                    f"🔹 Отсутствие резервного копирования: {optimization_bot.error_stats['missing_backup']}\n"
                    f"🔹 Ошибки в PowerShell: {optimization_bot.error_stats['powershell_errors']}\n"
                    f"🔹 Ошибки в Batch: {optimization_bot.error_stats['batch_errors']}\n"
                    f"🔹 Другие ошибки: {optimization_bot.error_stats['other_errors']}"
                )
                
                bot.send_message(message.chat.id, stats_text, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Ошибка в обработчике команды stats: {e}")
                bot.send_message(message.chat.id, "Произошла ошибка, пожалуйста, повторите попытку позже.")
        
        @bot.message_handler(commands=['add_user'])
        def cmd_add_user(message):
            try:
                # Проверяем, является ли отправитель администратором
                if not ADMIN_USER_ID or message.from_user.id != ADMIN_USER_ID:
                    bot.send_message(
                        message.chat.id,
                        "⛔ Только администратор может добавлять новых пользователей."
                    )
                    return
                
                # Синтаксис команды: /add_user USER_ID [NAME]
                command_args = message.text.split()
                if len(command_args) < 2:
                    bot.send_message(
                        message.chat.id,
                        "❌ Неверный формат команды.\nИспользуйте: /add_user USER_ID [NAME]"
                    )
                    return
                
                try:
                    # Извлекаем user_id из аргументов
                    user_id = int(command_args[1])
                    
                    # Добавляем в список разрешенных пользователей (только в памяти)
                    if user_id not in ALLOWED_USERS_LIST:
                        ALLOWED_USERS_LIST.append(user_id)
                        
                        # Формируем имя пользователя (опционально)
                        user_name = " ".join(command_args[2:]) if len(command_args) > 2 else f"User {user_id}"
                        
                        bot.send_message(
                            message.chat.id,
                            f"✅ Пользователь {user_name} (ID: {user_id}) успешно добавлен в белый список."
                        )
                        logger.info(f"Администратор добавил пользователя {user_id} в белый список")
                    else:
                        bot.send_message(
                            message.chat.id,
                            f"ℹ️ Пользователь с ID {user_id} уже есть в белом списке."
                        )
                except ValueError:
                    bot.send_message(
                        message.chat.id,
                        "❌ ID пользователя должен быть целым числом."
                    )
            except Exception as e:
                logger.error(f"Ошибка в обработчике команды add_user: {e}")
                bot.send_message(message.chat.id, "Произошла ошибка, пожалуйста, повторите попытку позже.")
        
        @bot.message_handler(content_types=['photo'])
        def process_photo(message):
            try:
                # Проверка авторизации
                if not is_user_authorized(message.from_user.id):
                    bot.send_message(
                        message.chat.id,
                        "⛔ У вас нет доступа к этому боту. Обратитесь к администратору для получения разрешения."
                    )
                    return
                    
                # Определяем текущее состояние пользователя
                current_state = optimization_bot.user_states.get(message.chat.id)
                
                if current_state == "waiting_for_error_screenshot":
                    # Пользователь отправил скриншот с ошибкой
                    bot.send_message(
                        message.chat.id,
                        "⏳ Анализирую скриншот с ошибкой и готовлю исправления... Это может занять несколько минут."
                    )
                    
                    # Асинхронный запуск исправления ошибок
                    asyncio.run(fix_script_errors(message))
                    
                elif message.caption and "fix" in message.caption.lower():
                    # Пользователь отправил скриншот с указанием "fix" в подписи
                    bot.send_message(
                        message.chat.id,
                        "⏳ Анализирую скриншот с ошибкой и готовлю исправления... Это может занять несколько минут."
                    )
                    
                    # Асинхронный запуск исправления ошибок
                    asyncio.run(fix_script_errors(message))
                    
                else:
                    # По умолчанию генерируем новый скрипт на основе скриншота системы
                    bot.send_message(
                        message.chat.id,
                        "⏳ Анализирую информацию о системе и создаю скрипты оптимизации... Это может занять несколько минут."
                    )
                    
                    # Асинхронный запуск генерации скриптов
                    asyncio.run(optimization_bot.generate_new_script(message))
                    
            except Exception as e:
                logger.error(f"Ошибка в обработчике фото: {e}")
                bot.send_message(
                    message.chat.id,
                    "❌ Произошла ошибка при обработке фото. Пожалуйста, попробуйте снова или обратитесь к разработчику."
                )
        
        @bot.message_handler(content_types=['text'])
        def handle_text(message):
            try:
                # Проверка авторизации
                if not is_user_authorized(message.from_user.id):
                    bot.send_message(
                        message.chat.id,
                        "⛔ У вас нет доступа к этому боту. Обратитесь к администратору для получения разрешения."
                    )
                    return
                    
                # Обработка текстовых сообщений
                text = message.text.lower()
                
                if "создать" in text or "оптимизация" in text or "скрипт" in text:
                    bot.send_message(
                        message.chat.id,
                        "📸 Для создания скриптов оптимизации отправьте скриншот сведений о вашей системе Windows.\n\n"
                        "Вы можете получить сведения о системе, нажав Win+R и введя 'control system'."
                    )
                    
                elif "исправить" in text or "ошибка" in text or "fix" in text:
                    # Устанавливаем состояние "ожидание скриншота ошибки"
                    optimization_bot.user_states[message.chat.id] = "waiting_for_error_screenshot"
                    
                    bot.send_message(
                        message.chat.id,
                        "🔧 Пожалуйста, отправьте скриншот с ошибкой, и я помогу её исправить."
                    )
                    
                elif "справка" in text or "помощь" in text or "help" in text:
                    cmd_help(message)
                    
                else:
                    bot.send_message(
                        message.chat.id,
                        "🤔 Не совсем понимаю, что вы хотите сделать.\n\n"
                        "📸 Отправьте скриншот системы для создания скриптов оптимизации\n"
                        "🔧 Используйте /fix для исправления ошибок\n"
                        "❓ Или /help для получения справки"
                    )
                    
            except Exception as e:
                logger.error(f"Ошибка в обработчике текста: {e}")
                bot.send_message(message.chat.id, "Произошла ошибка, пожалуйста, повторите попытку позже.")
        
        # Определяем асинхронную функцию для исправления ошибок
        async def fix_script_errors(message):
            try:
                # Создаем собственный экземпляр клиента Claude для изоляции от других процессов
                claude_client = anthropic.Anthropic(api_key=optimization_bot.api_key)
                
                # Отправляем сообщение об ожидании
                await bot.send_message(
                    message.chat.id,
                    "⏳ Анализирую скриншот с ошибкой и исправляю скрипты..."
                )
                
                # Получение файла фото с наилучшим разрешением
                photo = message.photo[-1]
                file_info = await bot.get_file(photo.file_id)
                file_url = f"https://api.telegram.org/file/bot{optimization_bot.token}/{file_info.file_path}"
                
                # Загрузка фото
                async with aiohttp.ClientSession() as session:
                    async with session.get(file_url) as response:
                        photo_bytes = BytesIO(await response.read())
                
                # Кодирование изображения в base64 для передачи в Claude
                photo_base64 = base64.b64encode(photo_bytes.read()).decode('utf-8')
                
                # Формирование запроса к Claude с изображением
                prompt = optimization_bot.ERROR_FIX_PROMPT_TEMPLATE
                
                # Пытаемся получить ранее отправленные файлы
                user_script_files = optimization_bot.user_files.get(message.chat.id, {})
                formatted_files = ""
                
                if user_script_files:
                    # Если есть файлы, добавляем их содержимое в запрос
                    for file_name, file_content in user_script_files.items():
                        formatted_files += f"\n{file_name}:\n```\n{file_content}\n```\n"
                
                # Заполняем шаблон промпта
                if formatted_files:
                    prompt = prompt.format(
                        script_files=formatted_files,
                        error_details="Проанализируй скриншот ошибки и исправь проблемы в скриптах."
                    )
                else:
                    prompt = prompt.replace("{script_files}", "Доступных скриптов нет, создай новые на основе скриншота ошибки.")
                    prompt = prompt.replace("{error_details}", "Проанализируй скриншот ошибки и создай исправленные скрипты.")
                
                try:
                    # Запрос к API Claude
                    response = claude_client.messages.create(
                        model=optimization_bot.model,
                        max_tokens=4000,
                        messages=[
                            {
                                "role": "user", 
                                "content": [
                                    {
                                        "type": "text", 
                                        "text": prompt
                                    },
                                    {
                                        "type": "image",
                                        "source": {
                                            "type": "base64", 
                                            "media_type": "image/jpeg", 
                                            "data": photo_base64
                                        }
                                    }
                                ]
                            }
                        ]
                    )
                    
                    if not hasattr(response, 'content') or not response.content:
                        logger.error("Некорректная структура ответа API")
                        await bot.send_message(
                            message.chat.id,
                            "❌ Ошибка при получении ответа от API. Пожалуйста, попробуйте позже."
                        )
                        return
                    
                    # Используем полученный текст как ответ
                    response_text = response.content[0].text
                    
                    # Извлекаем исправленные файлы из ответа API
                    if response_text:
                        # Извлекаем файлы из ответа
                        repaired_files = extract_files_from_response(response_text)
                        
                        if not repaired_files:
                            logger.error(f"Не удалось извлечь файлы из ответа: {response_text[:200]}")
                            await bot.send_message(
                                message.chat.id,
                                "❌ Не удалось извлечь исправленные скрипты из ответа. Пожалуйста, попробуйте еще раз."
                            )
                            return
                        
                        # Отправляем исправленные файлы пользователю
                        await optimization_bot.send_script_files_to_user(message, repaired_files)
                        
                        # Обновляем статистику исправлений
                        optimization_bot.script_fix_count += 1
                        
                        # Сбрасываем состояние пользователя
                        optimization_bot.user_states[message.chat.id] = None
                        
                    else:
                        logger.error("Пустой ответ от API")
                        await bot.send_message(
                            message.chat.id,
                            "❌ Не удалось получить исправленные скрипты. Пожалуйста, попробуйте еще раз или обратитесь к разработчику."
                        )
                        
                except Exception as e:
                    logger.error(f"Ошибка при запросе к API Claude: {e}")
                    await bot.send_message(
                        message.chat.id,
                        f"❌ Произошла ошибка при обработке запроса: {str(e)[:100]}...\nПожалуйста, попробуйте снова."
                    )
                    
            except Exception as e:
                logger.error(f"Ошибка при исправлении скриптов: {e}")
                await bot.send_message(
                    message.chat.id,
                    "❌ Произошла ошибка при исправлении скриптов. Пожалуйста, попробуйте снова или обратитесь к разработчику."
                )
        
        # Запуск бота
        logger.info("Бот запущен и готов принимать сообщения...")
        bot.polling(none_stop=True, interval=0)
        
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске бота: {e}")
        print(f"❌ Критическая ошибка: {e}")

if __name__ == '__main__':
    main() 