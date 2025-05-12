import os
import logging
import sys
import json
import base64
from io import BytesIO
from datetime import datetime
import zipfile
import requests
import subprocess
import asyncio
import signal

# Настройка базового логирования для вывода сообщений о зависимостях
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("windows_optimizer_bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
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

# Проверка, что только один экземпляр бота запущен
def check_single_instance():
    """Проверяет, запущен ли только один экземпляр бота"""
    try:
        # Получение списка процессов, содержащих имя скрипта
        output = subprocess.check_output(["tasklist", "/fi", f"imagename eq python.exe", "/fo", "csv"]).decode('cp866')
        lines = output.strip().split('\n')
        
        # Подсчет процессов скрипта
        script_name = os.path.basename(__file__)
        count = 0
        
        for line in lines:
            if script_name in line:
                count += 1
        
        if count > 1:
            logger.warning(f"Уже запущен экземпляр бота! Количество процессов с этим скриптом: {count}")
            print("Уже запущен экземпляр бота! Завершение работы...")
            return False
    
    except Exception as e:
        logger.error(f"Ошибка при проверке экземпляров: {e}")
    
    return True

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

# Шаблон промпта для оптимизации системы - расширенная и более подробная версия
OPTIMIZATION_PROMPT_TEMPLATE = r"""
# Задача: Создание PowerShell скриптов для оптимизации Windows

Ты - опытный системный администратор со специализацией на PowerShell и оптимизации Windows. Тебе необходимо создать профессиональные скрипты для оптимизации производительности Windows на основе изображения, которое предоставил пользователь.

## Требования к скриптам

### Обязательные файлы:
1. `WindowsOptimizer.ps1` - основной скрипт оптимизации на PowerShell
2. `Start-Optimizer.bat` - вспомогательный bat-файл для запуска с правами администратора
3. `README.md` - документация по использованию скриптов

### Технические требования к PowerShell скрипту:
- **Кодировка UTF-8** - в начале скрипта обязательно добавь: `$OutputEncoding = [System.Text.Encoding]::UTF8`
- **Проверка прав администратора** - скрипт должен проверять наличие прав администратора и выходить, если прав недостаточно
- **Модульная структура** - раздели функциональность на отдельные функции с четкими зонами ответственности
- **Обработка ошибок** - используй блоки try-catch для всех операций, которые могут вызвать ошибки
- **Логирование** - добавь логирование всех действий скрипта с отметками времени
- **Проверка существования файлов** - перед операциями с файлами добавь проверку их существования через Test-Path
- **Параметры безопасности** - используй -Force и -ErrorAction SilentlyContinue для критических операций

### Обязательные функции PowerShell скрипта:
1. `Backup-Settings` - создание резервных копий настроек перед их изменением
2. `Optimize-Performance` - оптимизация производительности системы
3. `Clean-System` - очистка временных файлов и ненужных данных
4. `Disable-Services` - отключение ненужных служб
5. `Show-Menu` - интерактивное меню для выбора операций

### Требования к BAT-файлу:
- Проверка наличия прав администратора
- Запуск PowerShell с параметром -ExecutionPolicy Bypass
- Содержит инструкции для пользователя

## Рекомендации по написанию кода

### Структура PowerShell скрипта:
```
# Информация о скрипте и документация
# Настройка кодировки и параметров
# Объявление глобальных переменных
# Функция резервного копирования
# Функции оптимизации
# Интерактивное меню
# Основная логика скрипта
# Очистка и завершение
```

### Баланс скобок и синтаксис:
- Тщательно проверяй баланс открывающих и закрывающих скобок `{}`
- Проверяй все блоки try/catch на правильное закрытие
- Проверяй корректность всех путей к файлам
- Проверяй синтаксис каждой функции

### Безопасность:
- Не отключай критически важные службы Windows
- Всегда создавай резервные копии перед изменениями
- Добавь возможность отката изменений
- Проверяй версию Windows для совместимости

## Анализ входных данных

Внимательно изучи предоставленный скриншот и определи:
1. Версию Windows
2. Технические характеристики системы (процессор, память, диск)
3. Проблемные службы или компоненты, которые можно оптимизировать
4. Конкретные настройки, которые можно изменить для улучшения производительности

## Перед отправкой результата:

Выполни тщательную проверку созданных скриптов:
1. **Синтаксические ошибки** - убедись, что нет ошибок синтаксиса
2. **Баланс скобок** - проверь, что все открывающие скобки имеют закрывающие пары
3. **Логика выполнения** - мысленно проследи выполнение скрипта и убедись, что все работает как ожидается
4. **Безопасность** - убедись, что скрипт не выполняет опасных операций
5. **Кодировка** - проверь, что установлена UTF-8 для корректного отображения русских символов
6. **Обработка ошибок** - убедись, что все потенциально опасные операции обернуты в try-catch
7. **Документация** - проверь наличие комментариев и пояснений к функциям

Предоставь три файла:
1. WindowsOptimizer.ps1 (основной PowerShell скрипт оптимизации)
2. Start-Optimizer.bat (вспомогательный BAT-файл для запуска)
3. README.md (инструкции по использованию)
"""

# Шаблон промпта для исправления ошибок - расширенная и более подробная версия
ERROR_FIX_PROMPT_TEMPLATE = r"""
# Задача: Исправление ошибок в скриптах оптимизации Windows

Ты - опытный системный администратор со специализацией на PowerShell и Windows. Тебе необходимо проанализировать и исправить ошибки в скриптах оптимизации Windows, которые видны на предоставленном изображении.

## Процесс анализа и исправления ошибок

### Этап 1: Анализ ошибки
1. Внимательно изучи сообщение об ошибке на скриншоте
2. Определи тип ошибки (синтаксическая, логическая, ошибка доступа и т.д.)
3. Найди строку кода, вызывающую ошибку

### Этап 2: Диагностика причины
1. Определи, почему возникла ошибка
2. Проанализируй контекст выполнения скрипта
3. Определи, какие условия вызвали ошибку

### Этап 3: Исправление кода
1. Внеси необходимые изменения в код для устранения ошибки
2. Добавь защитные механизмы для предотвращения подобных ошибок в будущем
3. Улучши обработку ошибок в проблемных местах

## Типичные ошибки и их решения

### Синтаксические ошибки
- **Несбалансированные скобки** - проверь количество открывающих и закрывающих скобок
- **Незакрытые кавычки** - убедись, что все строки правильно закрыты
- **Неправильные параметры команд** - проверь синтаксис параметров PowerShell

### Ошибки доступа
- **Недостаточно прав** - добавь проверку прав администратора и запрос повышения привилегий
- **Доступ к защищенным файлам** - используй параметры -Force и предварительные проверки
- **Блокировка файлов** - добавь обработку исключений для занятых файлов

### Логические ошибки
- **Неправильная последовательность** - проверь логику выполнения скрипта
- **Отсутствие проверок условий** - добавь проверки перед выполнением операций
- **Неверные пути к файлам** - проверь и исправь пути к файлам

### Ошибки кодировки
- **Проблемы с русскими символами** - добавь установку UTF-8 в начале скрипта
- **Неправильные переносы строк** - проверь символы переноса строк

## Обязательные улучшения для внесения в код:

1. **Установка кодировки UTF-8** - добавь в начало PowerShell скрипта:
   ```powershell
   $OutputEncoding = [System.Text.Encoding]::UTF8
   ```

2. **Проверка прав администратора** - добавь в начало PowerShell скрипта:
   ```powershell
   if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
       Write-Warning "Скрипт требует запуска с правами администратора."
       Exit
   }
   ```

3. **Улучшенная обработка ошибок** - убедись, что все операции обернуты в try-catch:
   ```powershell
   try {
       # Код операции
   } catch {
       Write-Warning "Произошла ошибка: $_"
       # Код обработки ошибки
   }
   ```

4. **Проверка существования файлов** - перед операциями с файлами:
   ```powershell
   if (Test-Path $filePath) {
       # Операции с файлом
   } else {
       Write-Warning "Файл не существует: $filePath"
   }
   ```

5. **Параметры безопасности** - добавь параметры для безопасных операций:
   ```powershell
   Remove-Item -Path $filePath -Force -ErrorAction SilentlyContinue
   ```

## Требования к исправленным скриптам:

1. **BAT-файл** должен:
   - Проверять наличие прав администратора
   - Запускать PowerShell с параметром -ExecutionPolicy Bypass
   - Иметь понятные сообщения для пользователя

2. **PowerShell скрипт** должен:
   - Иметь правильную установку кодировки UTF-8
   - Содержать проверку прав администратора
   - Иметь модульную структуру с отдельными функциями
   - Включать механизм создания резервных копий
   - Содержать обработку ошибок для всех операций
   - Включать логирование действий

## Перед отправкой результата:

Выполни тщательную проверку исправленных скриптов:
1. **Синтаксические ошибки** - убедись, что нет ошибок синтаксиса
2. **Баланс скобок** - проверь, что все открывающие скобки имеют закрывающие пары
3. **Логика выполнения** - мысленно проследи выполнение скрипта и убедись, что все работает как ожидается
4. **Безопасность** - убедись, что скрипт не выполняет опасных операций
5. **Кодировка** - проверь, что установлена UTF-8 для корректного отображения русских символов
6. **Обработка ошибок** - убедись, что все потенциально опасные операции обернуты в try-catch

Предоставь исправленные версии файлов:
1. WindowsOptimizer.ps1 (исправленный PowerShell скрипт)
2. Start-Optimizer.bat (исправленный BAT-файл для запуска)
"""

# Добавляем обработчики сигналов для корректного завершения
def signal_handler(sig, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info("Получен сигнал завершения. Останавливаю бота...")
    bot.stop_polling()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

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
        """Обновление статистики ошибок"""
        try:
            if validation_results:
                self.metrics.record_validation_results(validation_results)
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении статистики: {e}")
            return False

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
        # Проверяем, что это единственный экземпляр бота
        if not check_single_instance():
            return
            
        logger.info("Запуск бота...")
        
        # Проверяем наличие необходимых API ключей
        if not TELEGRAM_TOKEN:
            logger.error("TELEGRAM_TOKEN не установлен в .env файле")
            print("Ошибка: TELEGRAM_TOKEN не установлен в .env файле")
            return
            
        if not ANTHROPIC_API_KEY:
            logger.warning("ANTHROPIC_API_KEY не установлен в .env файле")
            print("Предупреждение: ANTHROPIC_API_KEY не установлен в .env файле")
        
        # Проверяем режим ограниченного доступа
        restricted_mode = os.getenv('RESTRICTED_MODE', 'false').lower() == 'true'
        if restricted_mode:
            allowed_users = os.getenv('ALLOWED_USERS', '').split(',')
            logger.info(f"Режим ограниченного доступа включен. Разрешенные пользователи: {allowed_users}")
        else:
            logger.info("Режим ограниченного доступа отключен. Доступ разрешен всем пользователям.")
        
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
        logger.info("Бот запущен и готов принимать сообщения...")
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}", exc_info=True)

if __name__ == '__main__':
    main() 