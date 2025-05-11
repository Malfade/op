import os
import re
import subprocess
from io import BytesIO
import logging

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ScriptValidator:
    """Класс для валидации PowerShell и Batch скриптов на наличие распространенных ошибок"""
    
    def __init__(self):
        # Шаблоны для проверки общих ошибок
        self.error_patterns = {
            # Ошибки в PowerShell скриптах
            "ps_syntax": [
                r"(Set-Service\s+\w+\s+(?!-ErrorAction))",  # Отсутствие обработки ошибок при работе со службами
                r"(Get-ChildItem\s+[\w\\]+\s+(?!-ErrorAction))", # Отсутствие обработки ошибок при работе с файлами
                r"(Remove-Item\s+[\w\\]+\s+(?!-ErrorAction))", # Отсутствие обработки ошибок при удалении файлов
                # Исключаем из проверки объявления массивов и хэш-таблиц
                r"(\$[A-Za-z_]+\s*=\s*[^;\n{(\[@]+$(?!\s*$)(?!\s*#))", # Незакрытые строки или отсутствие точки с запятой
                r"(try\s*{(?![\s\S]*?catch)[\s\S]*?})", # Try без catch блока
            ],
            # Ошибки в Batch скриптах
            "bat_syntax": [
                r"(powershell\s+(?!.*-ExecutionPolicy\s+Bypass).*\w+\.ps1)", # PowerShell без обхода политики выполнения при запуске скрипта
                r"(^@echo off(?![\s\S]*?chcp 65001))", # Отсутствие установки кодировки UTF-8
                r"(del\s+[^>]+(?!>nul 2>&1))", # Удаление файлов без перенаправления ошибок
            ],
            # Ошибки взаимодействия с файловой системой
            "file_access": [
                r"(Remove-Item\s+[^-]+(?!-Force))", # Удаление файлов без параметра -Force
                # Исключаем некоторые стандартные пути и шаблоны, где проверка Test-Path излишня
                r"(Write-Output\s+['\"][C-Zc-z]:\\[^'\"]+['\"](?!.*Test-Path))", # Запись в файл без проверки пути
            ],
            # Ошибки безопасности
            "security": [
                r"(-ExecutionPolicy Bypass -Command)", # Использование Bypass без дополнительных проверок
                r"(Invoke-Expression\s+\$)", # Использование Invoke-Expression с переменными (риск инъекций)
                r"(\[Ref\]\.Assembly\.GetType\([^\)]*\))", # Потенциально опасные вызовы .NET
            ]
        }
        
        # Обязательные блоки кода, которые должны присутствовать в скриптах
        self.required_code_blocks = {
            "ps1": [
                r"try\s*{[\s\S]*?}\s*catch\s*{", # Обработка исключений try-catch
                r"Get-Service[\s\S]*?(?:-ErrorAction SilentlyContinue|Select-Object)", # Безопасная работа со службами
                r"(?:Test-Path[\s\S]*?(?:before|if)|if[\s\S]*?Test-Path)", # Проверка наличия файлов перед их использованием
                r"function\s+(?:Show-Menu|Display)", # Наличие интерактивного меню или вывода
                r"(?:function\s+Backup-Settings|# Создание резервной копии|# Back)", # Функция резервного копирования или комментарий о ней
            ],
            "bat": [
                r"chcp 65001", # Установка кодировки UTF-8
                r"@echo off", # Отключение вывода команд
                r"if\s+(?:not\s+exist|exist)", # Проверка наличия файлов
                r"(?:net\s+session\s*>nul|administrator|runas|Admin)", # Проверка прав администратора
                r"-ExecutionPolicy Bypass", # Обход политики выполнения PowerShell
            ]
        }
    
    def validate_powershell_script(self, script_content):
        """Проверка PowerShell скрипта на синтаксические ошибки и соответствие стандартам"""
        issues = []
        
        logger.info(f"Начинаю валидацию PowerShell скрипта длиной {len(script_content)} символов")
        
        # Разбиваем скрипт на строки для анализа
        lines = script_content.split('\n')
        logger.info(f"Скрипт содержит {len(lines)} строк")
        
        # Проверка на синтаксические ошибки с учетом контекста
        for pattern_name, patterns in self.error_patterns.items():
            if pattern_name in ["ps_syntax", "file_access", "security"]:
                logger.info(f"Проверка шаблонов категории {pattern_name}")
                for pattern in patterns:
                    try:
                        # Пропускаем проверки для определённых шаблонов кода
                        if (('Get-Service' in script_content or 'Get-CimInstance' in script_content or 
                             'Get-ComputerInfo' in script_content) and 
                            pattern.startswith(r"(\$") and 'ps_syntax' in pattern_name):
                            logger.info(f"Пропускаю проверку шаблона {pattern} из-за наличия Get-Service/Get-CimInstance")
                            continue
                        
                        # Для паттернов, которые могут вызывать ошибки с многострочными блоками,
                        # используем специальную обработку
                        if 'try' in pattern or '$' in pattern:
                            matches = re.finditer(pattern, script_content, re.MULTILINE | re.DOTALL)
                        else:
                            matches = re.finditer(pattern, script_content, re.MULTILINE)
                            
                        matches_list = list(matches)
                        if matches_list:
                            logger.info(f"Найдено {len(matches_list)} совпадений для шаблона {pattern}")
                            
                        for match in matches_list:
                            # Проверка, что совпадение не является частью объявления массива или хэш-таблицы
                            match_text = match.group(0)
                            line_number = script_content[:match.start()].count('\n')
                            
                            # Пропускаем ложные срабатывания для массивов, объектов и Get команд
                            skip = False
                            if line_number < len(lines):
                                curr_line = lines[line_number]
                                next_line = lines[line_number + 1] if line_number + 1 < len(lines) else ""
                                
                                # Расширяем список исключений
                                if (('=' in curr_line and ('@(' in curr_line or '{' in next_line or '@{' in curr_line)) or
                                    ('Get-Service' in curr_line or 'Get-CimInstance' in curr_line or 
                                     'Get-ComputerInfo' in curr_line or 'Read-Host' in curr_line or
                                     '=' in curr_line and ('New-Object' in curr_line or '[PSCustomObject]' in curr_line)) or
                                    ('$services' in curr_line and '#' in curr_line)):
                                    skip = True
                                    logger.info(f"Пропускаю ложное срабатывание в строке {line_number+1}: {curr_line.strip()}")
                            
                            if not skip:
                                # Ограничиваем длину сообщения об ошибке для многострочных совпадений
                                if len(match_text) > 100:
                                    match_text = match_text[:97] + "..."
                                
                                logger.info(f"Добавляю ошибку: {pattern_name} в строке {line_number+1}")
                                issues.append(f"Потенциальная ошибка ({pattern_name}): {match_text}")
                    except Exception as e:
                        logger.error(f"Ошибка при проверке паттерна {pattern}: {e}")
        
        # Также модифицируем требование обязательных блоков кода
        required_blocks_to_check = self.required_code_blocks["ps1"].copy()
        
        # Если скрипт содержит явную обработку файлов с проверкой, но не содержит ключевого слова "before",
        # не считаем это ошибкой
        if ("Test-Path" in script_content and "if (Test-Path" in script_content) or \
           ("Test-Path" in script_content and "Remove-Item" in script_content and len(script_content) > 2000):
            logger.info("Скрипт содержит Test-Path и проверки условий, исключаю соответствующие требования")
            required_blocks_to_check = [block for block in required_blocks_to_check if "Test-Path" not in block]
        
        # Если скрипт содержит явное резервное копирование без отдельной функции
        if "# Резервное копирование" in script_content or "# Создаем резервную копию" in script_content:
            logger.info("Скрипт содержит резервное копирование, исключаю соответствующие требования")
            required_blocks_to_check = [block for block in required_blocks_to_check if "Backup-Settings" not in block]
        
        # Проверка наличия обязательных блоков кода
        for required_block in required_blocks_to_check:
            try:
                if not re.search(required_block, script_content, re.MULTILINE | re.DOTALL):
                    logger.info(f"Отсутствует обязательный блок кода: {required_block}")
                    issues.append(f"Отсутствует обязательный блок кода: {required_block}")
                else:
                    logger.info(f"Обязательный блок найден: {required_block}")
            except Exception as e:
                logger.error(f"Ошибка при проверке обязательного блока {required_block}: {e}")
        
        # Дополнительные проверки с учётом более сложного контекста
        if "Remove-Item" in script_content:
            if "Test-Path" not in script_content and "if (Test-Path" not in script_content:
                logger.info("Найдено использование Remove-Item без проверки Test-Path")
                issues.append("Удаление файлов без предварительной проверки их наличия")
            else:
                # Проверяем, что все Remove-Item предваряются Test-Path
                remove_lines = [i for i, line in enumerate(lines) if "Remove-Item" in line]
                test_path_found = False
                
                for line_num in remove_lines:
                    # Ищем Test-Path выше в коде
                    context_start = max(0, line_num - 5)
                    context = lines[context_start:line_num]
                    
                    if any("Test-Path" in line for line in context) or any("if " in line and "exist" in line.lower() for line in context):
                        test_path_found = True
                        logger.info(f"Найдена проверка Test-Path перед Remove-Item в строке {line_num+1}")
                        break
                
                if not test_path_found and len(remove_lines) > 0:
                    logger.info("Не все Remove-Item предваряются проверкой Test-Path")
        
        # Проверка на балансировку скобок
        open_curly = script_content.count("{")
        close_curly = script_content.count("}")
        if open_curly != close_curly:
            issues.append(f"Несбалансированные фигурные скобки: открыто {open_curly}, закрыто {close_curly}")
        
        open_bracket = script_content.count("(")
        close_bracket = script_content.count(")")
        if open_bracket != close_bracket:
            issues.append(f"Несбалансированные круглые скобки: открыто {open_bracket}, закрыто {close_bracket}")
        
        logger.info(f"Валидация PowerShell скрипта завершена, найдено {len(issues)} проблем")
        return issues
    
    def validate_batch_script(self, script_content):
        """Проверка Batch скрипта на ошибки и соответствие стандартам"""
        issues = []
        
        logger.info(f"Начинаю валидацию Batch скрипта длиной {len(script_content)} символов")
        
        # Проверка на ошибки в bat скриптах
        for pattern_name, patterns in self.error_patterns.items():
            if pattern_name == "bat_syntax":
                logger.info(f"Проверка шаблонов категории {pattern_name}")
                for pattern in patterns:
                    try:
                        # Используем DOTALL для обработки многострочных паттернов
                        if 'chcp' in pattern:
                            matches = re.finditer(pattern, script_content, re.MULTILINE | re.DOTALL)
                        else:
                            matches = re.finditer(pattern, script_content, re.MULTILINE)
                            
                        matches_list = list(matches)
                        if matches_list:
                            logger.info(f"Найдено {len(matches_list)} совпадений для шаблона {pattern}")
                            
                        for match in matches_list:
                            # Ограничиваем длину сообщения об ошибке
                            match_text = match.group(0)
                            if len(match_text) > 100:
                                match_text = match_text[:97] + "..."
                                
                            # Проверяем случай, когда PowerShell вызывается без Bypass, но в скрипте это уже есть
                            if "powershell" in match_text.lower() and "-ExecutionPolicy" not in match_text:
                                if "-ExecutionPolicy Bypass" in script_content:
                                    logger.info("Пропускаю ложное срабатывание для powershell, т.к. Bypass уже указан в скрипте")
                                    continue
                            
                            logger.info(f"Добавляю ошибку: {pattern_name} для текста: {match_text}")
                            issues.append(f"Потенциальная ошибка ({pattern_name}): {match_text}")
                    except Exception as e:
                        logger.error(f"Ошибка при проверке batch паттерна {pattern}: {e}")
                
        # Проверка наличия обязательных блоков кода
        for required_block in self.required_code_blocks["bat"]:
            try:
                if not re.search(required_block, script_content, re.MULTILINE | re.DOTALL):
                    logger.info(f"Отсутствует обязательный блок кода: {required_block}")
                    issues.append(f"Отсутствует обязательный блок кода: {required_block}")
                else:
                    logger.info(f"Обязательный блок найден: {required_block}")
            except Exception as e:
                logger.error(f"Ошибка при проверке обязательного блока bat {required_block}: {e}")
        
        # Проверка кодировки и наличия nul для перенаправления
        if "del" in script_content and ">nul" not in script_content:
            issues.append("Удаление файлов без перенаправления вывода в nul")
        
        logger.info(f"Валидация Batch скрипта завершена, найдено {len(issues)} проблем")
        return issues
    
    def validate_scripts(self, files):
        """Проверка всех скриптов в наборе файлов"""
        validation_results = {}
        
        for filename, content in files.items():
            if filename.endswith(".ps1"):
                issues = self.validate_powershell_script(content)
                validation_results[filename] = issues
            elif filename.endswith(".bat"):
                issues = self.validate_batch_script(content)
                validation_results[filename] = issues
        
        return validation_results
    
    def repair_common_issues(self, files):
        """Исправление распространенных ошибок в скриптах"""
        repaired_files = {}
        
        for filename, content in files.items():
            try:
                if filename.endswith(".ps1"):
                    # Исправление распространенных ошибок в PowerShell скриптах
                    fixed_content = content
                    
                    # Добавление обработки ошибок для операций со службами
                    try:
                        fixed_content = re.sub(
                            r"(Set-Service\s+\w+)(?!.*-ErrorAction)",
                            r"\1 -ErrorAction SilentlyContinue",
                            fixed_content
                        )
                        logger.info("Добавлена обработка ошибок для Set-Service")
                    except Exception as e:
                        logger.error(f"Ошибка при исправлении обработки ошибок служб: {e}")
                    
                    # Добавление проверки перед удалением файлов
                    try:
                        # Ищем все вхождения Remove-Item без предварительной проверки
                        remove_item_pattern = r"(Remove-Item\s+['\"]?[\w\\:.][^{\n]*?['\"]?)(?!\s+[-{])"
                        
                        if re.search(remove_item_pattern, fixed_content) and "Test-Path" not in fixed_content:
                            logger.info("Добавляю проверки Test-Path перед Remove-Item")
                            fixed_content = re.sub(
                                remove_item_pattern,
                                r"if (Test-Path \1) { \1 -Force -ErrorAction SilentlyContinue }",
                                fixed_content
                            )
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении проверки перед удалением файлов: {e}")
                    
                    # Добавление компонента резервного копирования, если его нет
                    if ("function Backup-Settings" not in fixed_content and 
                        "# Создание резервной копии" not in fixed_content and
                        "# Резервное копирование" not in fixed_content):
                        try:
                            logger.info("Добавляю функцию резервного копирования")
                            backup_function = """
# Функция для создания резервных копий
function Backup-Settings {
    param (
        [string]$SettingsType
    )
    
    $backupFolder = "$env:USERPROFILE\\WindowsOptimizer_Backups"
    
    # Создаем папку для резервных копий, если она не существует
    if (-not (Test-Path $backupFolder)) {
        New-Item -Path $backupFolder -ItemType Directory -Force | Out-Null
    }
    
    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $backupFile = "$backupFolder\\$SettingsType-Backup-$timestamp.reg"
    
    switch ($SettingsType) {
        "Registry" {
            Write-Host "Создание резервной копии реестра..." -ForegroundColor Cyan
            Start-Process -FilePath "reg" -ArgumentList "export HKCU $backupFile /y" -Wait -WindowStyle Hidden
        }
        default {
            Write-Host "Создание общей резервной копии настроек..." -ForegroundColor Cyan
            # Дополнительная логика резервного копирования других типов настроек
        }
    }
    
    if (Test-Path $backupFile) {
        Write-Host "Резервная копия создана: $backupFile" -ForegroundColor Green
    } else {
        Write-Host "Не удалось создать резервную копию." -ForegroundColor Red
    }
}
"""
                            # Поиск подходящего места для вставки функции
                            if "function " in fixed_content:
                                # Вставляем перед первой функцией
                                fixed_content = re.sub(
                                    r"(function\s+\w+\s*\{.*?$)",
                                    f"{backup_function}\n\n\\1",
                                    fixed_content,
                                    count=1,
                                    flags=re.MULTILINE | re.DOTALL
                                )
                            else:
                                # Вставляем в начало скрипта после комментариев
                                fixed_content = re.sub(
                                    r"(^.*?#.*?\n+)",
                                    f"\\1\n{backup_function}\n",
                                    fixed_content,
                                    count=1,
                                    flags=re.MULTILINE | re.DOTALL
                                )
                        except Exception as e:
                            logger.error(f"Ошибка при добавлении функции резервного копирования: {e}")
                    
                    # Добавление try-catch блоков для потенциально опасных операций
                    if "try" not in fixed_content and "catch" not in fixed_content:
                        try:
                            logger.info("Добавляю обработку исключений try-catch")
                            lines = fixed_content.split("\n")
                            in_function = False
                            function_start = -1
                            
                            for i, line in enumerate(lines):
                                line_trimmed = line.strip()
                                if line_trimmed.startswith("function ") and ("{" in line_trimmed or i < len(lines) - 1 and "{" in lines[i+1].strip()):
                                    in_function = True
                                    function_start = i
                                elif in_function and line_trimmed == "{":
                                    # Добавляем try-catch внутрь функции
                                    lines[i] = "{\n    try {"
                                    # Ищем закрывающую скобку функции с учетом вложенных блоков
                                    brace_count = 1
                                    for j in range(i+1, len(lines)):
                                        if "{" in lines[j]:
                                            brace_count += lines[j].count("{")
                                        if "}" in lines[j]:
                                            brace_count -= lines[j].count("}")
                                            if brace_count == 0:
                                                lines[j] = "    }\n    catch {\n        Write-Warning \"Ошибка: $_\"\n    }\n}"
                                                break
                                    in_function = False
                                    
                            fixed_content = "\n".join(lines)
                        except Exception as e:
                            logger.error(f"Ошибка при добавлении try-catch блоков: {e}")
                    
                    repaired_files[filename] = fixed_content
                    
                elif filename.endswith(".bat"):
                    # Исправление распространенных ошибок в Batch скриптах
                    fixed_content = content
                    
                    # Добавление установки кодировки UTF-8
                    try:
                        if "chcp 65001" not in fixed_content:
                            if "@echo off" in fixed_content:
                                fixed_content = fixed_content.replace("@echo off", "@echo off\nchcp 65001 >nul")
                            else:
                                fixed_content = "chcp 65001 >nul\n" + fixed_content
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении установки кодировки: {e}")
                    
                    # Добавление проверки прав администратора
                    try:
                        if "net session" not in fixed_content and "administrator" not in fixed_content.lower():
                            admin_check = """
@echo off
chcp 65001 >nul
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Для запуска необходимы права администратора.
    echo Пожалуйста, запустите скрипт от имени администратора.
    pause
    exit
)
"""
                            fixed_content = admin_check + fixed_content.replace("@echo off", "").replace("chcp 65001", "")
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении проверки прав администратора: {e}")
                    
                    # Добавляем параметр bypass при вызове PowerShell
                    try:
                        if "powershell" in fixed_content and "-ExecutionPolicy Bypass" not in fixed_content:
                            logger.info("Добавляю параметр ExecutionPolicy Bypass к вызовам PowerShell")
                            fixed_content = re.sub(
                                r"(powershell)(?!.*-ExecutionPolicy Bypass)",
                                r"\1 -ExecutionPolicy Bypass -NoProfile",
                                fixed_content
                            )
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении параметра bypass: {e}")
                    
                    # Добавляем перенаправление вывода для команды del
                    try:
                        if "del " in fixed_content and ">nul" not in fixed_content:
                            logger.info("Добавляю перенаправление вывода >nul для команд del")
                            fixed_content = re.sub(
                                r"(del\s+[\w\.\\\*\"\']+)(?!\s*>)",
                                r"\1 >nul 2>&1",
                                fixed_content
                            )
                    except Exception as e:
                        logger.error(f"Ошибка при добавлении перенаправления >nul: {e}")
                    
                    repaired_files[filename] = fixed_content
                else:
                    # Для других файлов оставляем содержимое без изменений
                    repaired_files[filename] = content
            except Exception as e:
                logger.error(f"Ошибка при исправлении файла {filename}: {e}")
                # В случае ошибки оставляем исходное содержимое
                repaired_files[filename] = content
        
        return repaired_files
    
    def enhance_scripts(self, files):
        """Улучшение скриптов путем добавления дополнительных функций и документации"""
        enhanced_files = {}
        
        for filename, content in files.items():
            try:
                if filename.endswith(".ps1") and len(content) > 0:
                    logger.info(f"Улучшаю PowerShell скрипт: {filename}")
                    enhanced_content = content
                    
                    # Добавление вывода прогресса
                    if "Write-Progress" not in enhanced_content:
                        try:
                            logger.info("Добавляю функцию отображения прогресса")
                            progress_function = """
# Функция для отображения прогресса
function Show-Progress {
    param (
        [string]$Task,
        [int]$PercentComplete
    )
    
    Write-Progress -Activity "Оптимизация Windows" -Status $Task -PercentComplete $PercentComplete
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Task" -ForegroundColor Cyan
}
"""
                            # Вставляем после определений функций
                            if "function " in enhanced_content:
                                enhanced_content = re.sub(
                                    r"(function\s+\w+\s*\{.*?\})\s*(?=\n)",
                                    f"\\1\n\n{progress_function}",
                                    enhanced_content,
                                    count=1,
                                    flags=re.MULTILINE | re.DOTALL
                                )
                            else:
                                # Вставляем в начало скрипта
                                enhanced_content = f"{progress_function}\n\n{enhanced_content}"
                        except Exception as e:
                            logger.error(f"Ошибка при добавлении функции прогресса: {e}")
                    
                    # Добавление улучшенной документации в скрипт
                    if not enhanced_content.startswith("#") and not enhanced_content.startswith("<#"):
                        try:
                            logger.info("Добавляю документацию к скрипту")
                            documentation = r"""<#
.SYNOPSIS
   Скрипт для оптимизации и настройки системы Windows.
   
.DESCRIPTION
   Скрипт выполняет комплексную оптимизацию системы Windows, включая:
   - Очистку ненужных файлов и оптимизацию дискового пространства
   - Настройку служб для повышения производительности
   - Отключение ненужных компонентов и фоновых процессов
   - Оптимизацию реестра для улучшения отзывчивости системы
   
.NOTES
   Автор: WindowsOptimizer Bot
   Версия: 1.0
   Дата создания: $(Get-Date -Format "yyyy-MM-dd")
   
.EXAMPLE
   .\WindowsOptimizer.ps1
   Запуск полной оптимизации системы.
#>

"""
                            enhanced_content = documentation + enhanced_content
                        except Exception as e:
                            logger.error(f"Ошибка при добавлении документации: {e}")
                    
                    # Добавление логов
                    if "Start-Transcript" not in enhanced_content:
                        try:
                            logger.info("Добавляю логирование действий скрипта")
                            logging_code = r"""
# Включаем логирование действий скрипта
$logPath = "$env:USERPROFILE\WindowsOptimizer_Logs"
if (-not (Test-Path $logPath)) {
    New-Item -Path $logPath -ItemType Directory -Force | Out-Null
}
$logFile = "$logPath\Optimization-Log-$(Get-Date -Format 'yyyy-MM-dd_HH-mm-ss').txt"
Start-Transcript -Path $logFile -Force
Write-Host "Начинаю оптимизацию. Лог сохраняется в файл: $logFile" -ForegroundColor Green

"""
                            # Находим точку после объявления функций или после документации
                            if "<#" in enhanced_content and "#>" in enhanced_content:
                                enhanced_content = re.sub(
                                    r"(#>.*?\n+)",
                                    f"\\1\n{logging_code}",
                                    enhanced_content,
                                    count=1,
                                    flags=re.MULTILINE | re.DOTALL
                                )
                            else:
                                # Вставляем после всех начальных комментариев
                                enhanced_content = re.sub(
                                    r"(^(?:#.*?\n+)*)",
                                    f"\\1\n{logging_code}",
                                    enhanced_content,
                                    count=1,
                                    flags=re.MULTILINE | re.DOTALL
                                )
                        except Exception as e:
                            logger.error(f"Ошибка при добавлении логирования: {e}")
                    
                    # Добавление строки остановки логирования в конец скрипта
                    if "Start-Transcript" in enhanced_content and "Stop-Transcript" not in enhanced_content:
                        enhanced_content += "\n\n# Останавливаем логирование\nStop-Transcript\n"
                    
                    enhanced_files[filename] = enhanced_content
                
                elif filename.endswith(".bat") and len(content) > 0:
                    logger.info(f"Улучшаю Batch скрипт: {filename}")
                    enhanced_content = content
                    
                    # Добавление расширенной проверки прав администратора
                    if "administrator" in enhanced_content.lower() and "NET FILE" not in enhanced_content:
                        try:
                            logger.info("Добавляю улучшенную проверку прав администратора")
                            admin_check = """
@echo off
chcp 65001 >nul

echo Проверка прав администратора...
NET FILE 1>NUL 2>NUL
if '%errorlevel%' == '0' (
    echo Запуск с правами администратора: OK
) else (
    echo Для работы скрипта требуются права администратора.
    echo Запуск от имени администратора...
    
    powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b
)

"""
                            if "@echo off" in enhanced_content:
                                enhanced_content = enhanced_content.replace("@echo off", admin_check)
                            else:
                                enhanced_content = admin_check + enhanced_content
                        except Exception as e:
                            logger.error(f"Ошибка при добавлении проверки прав администратора: {e}")
                    
                    # Добавление комментариев с описанием работы скрипта
                    if not enhanced_content.startswith("::") and not enhanced_content.startswith("REM"):
                        logger.info("Добавляю документацию к batch-скрипту")
                        header = f"""::============================================================================
:: WindowsOptimizer - Скрипт запуска оптимизации системы Windows
::============================================================================
:: Описание: Этот скрипт запускает основной скрипт оптимизации PowerShell
::           с правильными параметрами и проверяет наличие необходимых прав.
::
:: Автор: WindowsOptimizer Bot
:: Дата: {subprocess.check_output('date /t', shell=True).decode('cp866').strip()}
::============================================================================

"""
                        enhanced_content = header + enhanced_content
                    
                    enhanced_files[filename] = enhanced_content
                
                elif filename.endswith(".md") and len(content) > 0:
                    logger.info(f"Улучшаю документацию: {filename}")
                    enhanced_content = content
                    
                    # Добавление дополнительных секций в README
                    if "# " in enhanced_content and "## Устранение проблем" not in enhanced_content:
                        logger.info("Добавляю секцию по устранению проблем")
                        troubleshooting = r"""

## Устранение проблем

Если при запуске скриптов возникают проблемы:

1. **Ошибки выполнения PowerShell**:
   - Убедитесь, что запускаете скрипт с правами администратора
   - Проверьте политику выполнения PowerShell: `Get-ExecutionPolicy`
   - При необходимости, измените политику: `Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process`

2. **Скрипт не запускается**:
   - Запустите командную строку от имени администратора
   - Перейдите в папку со скриптами: `cd путь_к_папке`
   - Запустите bat-файл вручную: `Start-Optimizer.bat`

3. **Система работает нестабильно после оптимизации**:
   - Все изменения фиксируются в логах, расположенных в `%USERPROFILE%\WindowsOptimizer_Logs`
   - Для откатов оптимизаций можно использовать точки восстановления системы
   - Резервные копии создаются в папке `%USERPROFILE%\WindowsOptimizer_Backups`
"""
                        enhanced_content += troubleshooting
                    
                    enhanced_files[filename] = enhanced_content
                
                else:
                    # Оставляем без изменений
                    enhanced_files[filename] = content
                
            except Exception as e:
                logger.error(f"Ошибка при улучшении файла {filename}: {e}")
                # В случае ошибки оставляем исходное содержимое
                enhanced_files[filename] = content
        
        return enhanced_files
        
    def should_regenerate_script(self, validation_results):
        """Определяет, требуется ли полная регенерация скрипта"""
        critical_issues_count = 0
        
        for filename, issues in validation_results.items():
            for issue in issues:
                # Подсчет критических ошибок, которые нельзя исправить автоматически
                if any(critical in issue.lower() for critical in ["несбалансированные", "синтаксис", "отсутствует"]):
                    critical_issues_count += 1
        
        # Если больше 3 критических ошибок, рекомендуем регенерацию
        return critical_issues_count > 3

# Пример использования:
# validator = ScriptValidator()
# validation_results = validator.validate_scripts(files)
# if validator.should_regenerate_script(validation_results):
#     # Запрос на регенерацию скриптов
# else:
#     # Применение автоматических исправлений
#     fixed_files = validator.repair_common_issues(files) 