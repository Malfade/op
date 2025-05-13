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
        """Исправляет распространенные проблемы в скрипте

        Args:
            files (dict): Словарь с файлами (имя файла -> содержимое)
            
        Returns:
            dict: Словарь с исправленными файлами
        """
        try:
            fixed_files = {}
            
            for filename, content in files.items():
                try:
                    if filename.lower().endswith('.ps1'):
                        logger.info(f"Исправляю PowerShell скрипт: {filename}")
                        fixed_content = self._repair_powershell_script(content)
                    elif filename.lower().endswith('.bat'):
                        logger.info(f"Исправляю Batch скрипт: {filename}")
                        fixed_content = self._repair_batch_script(content)
                    else:
                        fixed_content = content
                    
                    fixed_files[filename] = fixed_content
                except Exception as e:
                    logger.error(f"Ошибка при исправлении файла {filename}: {e}")
                    fixed_files[filename] = content
            
            return fixed_files
        except Exception as e:
            logger.error(f"Общая ошибка при исправлении файлов: {e}")
            return files
    
    def enhance_scripts(self, files):
        """
        Улучшает скрипты, добавляя полезные функции и повышая удобство использования
        
        Args:
            files: словарь с файлами (имя файла -> содержимое)
            
        Returns:
            dict: Словарь с улучшенными файлами
        """
        enhanced_files = files.copy()
        
        # Улучшаем каждый файл в зависимости от типа
        for filename, content in files.items():
            if filename.endswith('.ps1'):
                enhanced_files[filename] = self._enhance_powershell_script(content)
                logger.info(f"Улучшаю PowerShell скрипт: {filename}")
            elif filename.endswith('.bat'):
                enhanced_files[filename] = self.enhance_batch_script(content)
                logger.info(f"Улучшаю Batch скрипт: {filename}")
            elif filename.endswith('.md'):
                enhanced_files[filename] = self._enhance_markdown(content)
                logger.info(f"Улучшаю документацию: {filename}")
        
        # Добавляем файл Run-Optimizer.ps1 для альтернативного запуска
        if "WindowsOptimizer.ps1" in files.keys() and "Run-Optimizer.ps1" not in files.keys():
            logger.info("Создаю альтернативный PowerShell скрипт для запуска")
            enhanced_files["Run-Optimizer.ps1"] = """# Encoding: UTF-8
# PowerShell script to launch the main optimization script
$OutputEncoding = [System.Text.Encoding]::UTF8

# Check administrator rights
function Test-Administrator {
    $user = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($user)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) {
    Write-Warning "This script requires administrator privileges."
    Write-Warning "Please run this file as administrator."
    pause
    exit
}

Write-Host "Starting Windows optimization script..." -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

# Check if the main script exists
if (Test-Path -Path "WindowsOptimizer.ps1") {
    # Run the main PowerShell script
    try {
        & .\\WindowsOptimizer.ps1
    } catch {
        Write-Host "Error running the optimization script: $_" -ForegroundColor Red
    }
} else {
    Write-Host "Error: WindowsOptimizer.ps1 not found in the current directory." -ForegroundColor Red
    Write-Host "Make sure all files are extracted from the ZIP archive." -ForegroundColor Yellow
}

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Optimization script completed." -ForegroundColor Green
pause
"""
            
            # Обновляем инструкцию в README.md
            if "README.md" in enhanced_files:
                readme_content = enhanced_files["README.md"]
                if "Run-Optimizer.ps1" not in readme_content:
                    insert_point = readme_content.find("## Использование")
                    if insert_point > 0:
                        alternative_text = """

### Альтернативный метод запуска (при проблемах с кодировкой)
Если при запуске batch-файла возникают ошибки с кодировкой (неправильное отображение символов):
1. Запустите файл `Run-Optimizer.ps1` от имени администратора
2. Для этого щелкните по файлу правой кнопкой мыши и выберите "Запустить с помощью PowerShell"
"""
                        enhanced_files["README.md"] = readme_content[:insert_point+14] + alternative_text + readme_content[insert_point+14:]
                        logger.info("Обновлена документация с информацией об альтернативном методе запуска")
            
            # Добавляем информацию в КАК_ИСПОЛЬЗОВАТЬ.txt, если он существует
            if "КАК_ИСПОЛЬЗОВАТЬ.txt" in enhanced_files:
                usage_content = enhanced_files["КАК_ИСПОЛЬЗОВАТЬ.txt"]
                if "Run-Optimizer.ps1" not in usage_content:
                    enhanced_files["КАК_ИСПОЛЬЗОВАТЬ.txt"] = usage_content + """

АЛЬТЕРНАТИВНЫЙ СПОСОБ ЗАПУСКА (если возникают ошибки кодировки):
1. Запустите файл Run-Optimizer.ps1 от имени администратора
2. Щелкните правой кнопкой мыши по файлу и выберите "Запустить с помощью PowerShell"
"""
                    logger.info("Обновлена инструкция КАК_ИСПОЛЬЗОВАТЬ.txt")
        
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

    def fix_variables_in_strings(self, content):
        """Исправляет формат переменных в строках с двоеточием
        
        Args:
            content (str): Содержимое PowerShell скрипта
            
        Returns:
            str: Исправленное содержимое скрипта
        """
        try:
            # Ищем строки с двоеточием и переменными
            pattern = r'("[^"]*\$[a-zA-Z_][a-zA-Z0-9_]*\s*:[^"]*")'
            
            def replace_variables(match):
                # Получаем строку с двоеточием
                string_with_colon = match.group(1)
                
                # Ищем переменные в строке
                var_pattern = r'\$([a-zA-Z_][a-zA-Z0-9_]*)'
                return re.sub(var_pattern, r'${\\1}', string_with_colon)
            
            # Исправляем все найденные строки
            fixed_content = re.sub(pattern, replace_variables, content)
            
            # Проверяем результат и исправляем проблемы с экранированием
            fixed_content = fixed_content.replace('${\\', '${')
            
            return fixed_content
        except Exception as e:
            logger.error(f"Ошибка при исправлении переменных в строках: {e}")
            return content

    def _repair_powershell_script(self, content):
        """Исправление распространенных проблем в PowerShell скрипте
        
        Args:
            content (str): Содержимое PowerShell скрипта
            
        Returns:
            str: Исправленное содержимое скрипта
        """
        repaired_content = content
        
        # Добавление установки кодировки UTF-8, если ее нет
        if "$OutputEncoding = [System.Text.Encoding]::UTF8" not in repaired_content:
            encoding_setting = "# Encoding: UTF-8\n$OutputEncoding = [System.Text.Encoding]::UTF8\n\n"
            # Добавляем в начало файла
            repaired_content = encoding_setting + repaired_content
        
        # Исправление переменных в строках с двоеточием
        repaired_content = self.fix_variables_in_strings(repaired_content)
        
        # Добавление параметра -Force для операций Remove-Item
        repaired_content = re.sub(r'(Remove-Item\s+[^-\n]+)(?!-Force)', r'\1 -Force', repaired_content)
        
        # Добавление -ErrorAction SilentlyContinue для критичных операций
        for operation in ['Set-Service', 'Stop-Service', 'Start-Service', 'Remove-Item']:
            try:
                repaired_content = re.sub(f'({operation}\\s+[^-\\n]+)(?!-ErrorAction)', 
                                         r'\1 -ErrorAction SilentlyContinue', repaired_content)
                
                if operation == 'Set-Service':
                    logger.info(f"Добавлена обработка ошибок для {operation}")
            except Exception as e:
                logger.error(f"Ошибка при добавлении параметра -ErrorAction: {e}")
        
        # Исправление проблем с балансировкой скобок
        try:
            # Подсчет открывающих и закрывающих скобок
            open_braces = repaired_content.count('{')
            close_braces = repaired_content.count('}')
            
            # Если есть дисбаланс, пытаемся исправить
            if open_braces > close_braces:
                # Добавляем недостающие закрывающие скобки в конец
                repaired_content += '\n\n# Автоматически добавленные закрывающие скобки\n' + '}' * (open_braces - close_braces)
                logger.info(f"Добавлено {open_braces - close_braces} закрывающих скобок для исправления баланса")
            elif close_braces > open_braces:
                # Удаляем лишние закрывающие скобки с конца
                excess_braces = close_braces - open_braces
                last_brace_index = len(repaired_content) - 1
                
                while excess_braces > 0 and last_brace_index >= 0:
                    if repaired_content[last_brace_index] == '}':
                        # Удаляем закрывающую скобку
                        repaired_content = repaired_content[:last_brace_index] + repaired_content[last_brace_index+1:]
                        excess_braces -= 1
                    last_brace_index -= 1
                logger.info(f"Удалено {close_braces - open_braces} лишних закрывающих скобок")
        except Exception as e:
            logger.error(f"Ошибка при исправлении баланса скобок: {e}")
        
        # Исправление незавершенных блоков try-catch
        try:
            # Ищем все блоки try без соответствующих catch
            try_blocks = []
            catch_blocks = []
            
            for match in re.finditer(r'try\s*{', repaired_content):
                try_blocks.append(match.start())
            
            for match in re.finditer(r'catch\s*{', repaired_content):
                catch_blocks.append(match.start())
            
            # Если количество try больше, чем catch, добавляем недостающие catch блоки
            if len(try_blocks) > len(catch_blocks):
                missing_catch = len(try_blocks) - len(catch_blocks)
                repaired_content += '\n\n# Автоматически добавленные catch блоки\n'
                for i in range(missing_catch):
                    repaired_content += 'catch {\n    Write-Warning "Произошла ошибка в блоке try"\n}\n'
                logger.info(f"Добавлено {missing_catch} недостающих блоков catch")
        except Exception as e:
            logger.error(f"Ошибка при исправлении блоков try-catch: {e}")
        
        # Добавление функции резервного копирования, если ее нет
        if "function Backup-Settings" not in repaired_content:
            try:
                logger.info("Добавляю функцию резервного копирования")
                backup_function = """
# Функция для создания резервных копий настроек
function Backup-Settings {
    param (
        [string]$SettingName,
        [string]$Data
    )
    
    try {
        # Создаем директорию для резервных копий, если ее нет
        $BackupDir = "$env:USERPROFILE\\WindowsOptimizer_Backups"
        if (-not (Test-Path -Path $BackupDir)) {
            New-Item -Path $BackupDir -ItemType Directory -Force | Out-Null
        }
        
        # Формируем имя файла резервной копии
        $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $BackupFile = "$BackupDir\\${SettingName}_$Timestamp.bak"
        
        # Сохраняем данные в файл
        $Data | Out-File -FilePath $BackupFile -Encoding UTF8 -Force
        
        Write-Host "Создана резервная копия $SettingName в файле $BackupFile" -ForegroundColor Green
        return $BackupFile
    }
    catch {
        Write-Warning "Не удалось создать резервную копию ${SettingName}: ${_}"
        return $null
    }
}
"""
                # Находим место для вставки - после первой функции или в начало
                if "function " in repaired_content:
                    # Ищем первое определение функции
                    match = re.search(r'function\s+\w+\s*{', repaired_content)
                    if match:
                        insert_pos = match.start()
                        repaired_content = repaired_content[:insert_pos] + backup_function + repaired_content[insert_pos:]
                else:
                    # Если нет функций, добавляем после настройки кодировки
                    if "$OutputEncoding = [System.Text.Encoding]::UTF8" in repaired_content:
                        repaired_content = repaired_content.replace("$OutputEncoding = [System.Text.Encoding]::UTF8", 
                                                                  "$OutputEncoding = [System.Text.Encoding]::UTF8\n" + backup_function)
                    else:
                        # Если нет настройки кодировки, добавляем в начало
                        repaired_content = backup_function + repaired_content
            except Exception as e:
                logger.error(f"Ошибка при добавлении функции резервного копирования: {e}")
        
        return repaired_content

    def _repair_batch_script(self, content):
        """Исправляет распространенные проблемы в Batch скрипте
        
        Args:
            content (str): Содержимое Batch скрипта
            
        Returns:
            str: Исправленное содержимое скрипта
        """
        repaired_content = content
        
        # Убедимся, что файл начинается с правильных команд
        if not repaired_content.startswith("@echo off"):
            repaired_content = "@echo off\n" + repaired_content
        
        if "chcp 65001" not in repaired_content:
            repaired_content = repaired_content.replace("@echo off", "@echo off\nchcp 65001 >nul")
        
        # Исправляем команду запуска PowerShell
        powershell_cmd = re.search(r'powershell\s+.*(-File|\.\\|\./).*WindowsOptimizer\.ps1', repaired_content)
        if powershell_cmd:
            cmd_text = powershell_cmd.group(0)
            if "-ExecutionPolicy Bypass" not in cmd_text:
                fixed_cmd = "powershell -ExecutionPolicy Bypass -NoProfile -File \"WindowsOptimizer.ps1\""
                repaired_content = repaired_content.replace(cmd_text, fixed_cmd)
        else:
            # Если команды нет, добавляем правильную
            insertion_point = repaired_content.find("echo")
            if insertion_point > 0:
                # Ищем точку для вставки после блока проверки прав администратора
                admin_check = re.search(r'if\s+%errorlevel%\s+neq\s+0', repaired_content)
                if admin_check:
                    admin_block_end = repaired_content.find(')', admin_check.end())
                    if admin_block_end > 0:
                        insertion_point = repaired_content.find('\n', admin_block_end) + 1
            
                # Вставляем правильную команду запуска
                repaired_content = (repaired_content[:insertion_point] + 
                                  "\necho Starting Windows optimization script...\n" +
                                  "echo ==========================================\n\n" +
                                  "powershell -ExecutionPolicy Bypass -NoProfile -File \"WindowsOptimizer.ps1\"\n\n" +
                                  "echo ==========================================\n" +
                                  "echo Optimization script completed.\n" +
                                  "pause\n" +
                                  repaired_content[insertion_point:])
        
        # Исправляем команды del, чтобы они использовали перенаправление ошибок
        repaired_content = re.sub(r'(del\s+[^>]+)(?!>nul)', r'\1 >nul 2>&1', repaired_content)
        
        # Добавляем проверку существования файла перед удалением
        if "del" in repaired_content and "if exist" not in repaired_content:
            repaired_content = repaired_content.replace("del", "if exist")
        
        # Исправляем проблемы с экранированием путей
        repaired_content = repaired_content.replace("\\\\", "\\")
        
        # НОВОЕ: Проверяем на наличие русских символов и заменяем их на английские
        # Словарь замен русских фраз на английские
        ru_to_en = {
            "Запуск": "Starting",
            "скрипта": "script",
            "оптимизации": "optimization",
            "завершен": "completed",
            "Windows": "Windows",
            "Скрипт": "Script",
            "выполнен": "completed",
            "требует": "requires",
            "запуска": "to run",
            "от имени": "as",
            "администратора": "administrator",
            "Пожалуйста": "Please",
            "запустите": "run",
            "этот": "this",
            "файл": "file",
            "Нажмите": "Press",
            "любую": "any",
            "клавишу": "key",
            "для": "to",
            "продолжения": "continue",
            "не найден": "not found",
            "Убедитесь": "Make sure",
            "что он": "it is",
            "находится": "located",
            "в той же": "in the same",
            "папке": "folder"
        }
        
        # Собираем шаблон для поиска всех русских слов разом
        ru_pattern = r'[А-Яа-я]+'
        
        # Функция замены, которая заменяет русские слова на английские
        def replace_ru_text(match):
            ru_word = match.group(0)
            # Проверяем, есть ли слово в словаре замен
            for ru, en in ru_to_en.items():
                if ru in ru_word:
                    return en
            # Если нет точного соответствия, возвращаем общую замену
            return "text"
        
        # Заменяем все русские слова на английские
        repaired_content = re.sub(ru_pattern, replace_ru_text, repaired_content)
        
        # Замена всех оставшихся русских символов
        cyrillic_pattern = re.compile('[А-Яа-яЁё]')
        if cyrillic_pattern.search(repaired_content):
            logger.info("Обнаружены кириллические символы в BAT-файле, заменяю на стандартный шаблон")
            # Заменяем весь контент стандартным шаблоном
            repaired_content = """@echo off
chcp 65001 >nul
title Windows Optimization

:: Check administrator rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Administrator rights required.
    echo Please run this file as administrator.
    pause
    exit /b 1
)

:: Script file check
if not exist "WindowsOptimizer.ps1" (
    echo File WindowsOptimizer.ps1 not found.
    echo Please make sure it is in the same folder.
    pause
    exit
)

:: Run PowerShell script with needed parameters
echo Starting Windows optimization script...
echo ==========================================

powershell -ExecutionPolicy Bypass -NoProfile -File "WindowsOptimizer.ps1" -Encoding UTF8

echo ==========================================
echo Optimization script completed.
pause
"""
        
        return repaired_content

    def enhance_batch_script(self, content):
        """Улучшает Batch скрипт, добавляя полезные функции
        
        Args:
            content (str): Содержимое Batch скрипта
            
        Returns:
            str: Улучшенное содержимое скрипта
        """
        enhanced_content = content
        
        # Проверяем, нет ли уже необходимой функциональности
        if "title" not in enhanced_content.lower():
            # Добавляем заголовок окна
            enhanced_content = enhanced_content.replace("@echo off", "@echo off\ntitle Запуск оптимизации Windows")
        
        # Улучшенная проверка прав администратора
        if "net session" not in enhanced_content:
            admin_check = """
:: Проверка прав администратора
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Скрипт требует запуска от имени администратора.
    echo Пожалуйста, запустите этот файл от имени администратора.
    pause
    exit /b 1
)
"""
            # Находим подходящее место для вставки
            if "chcp 65001" in enhanced_content:
                position = enhanced_content.find("chcp 65001") + 14
                enhanced_content = enhanced_content[:position] + "\n" + admin_check + enhanced_content[position:]
            else:
                enhanced_content = enhanced_content.replace("@echo off", "@echo off\nchcp 65001 >nul" + admin_check)
        
        # Добавляем визуальное оформление
        if "=========" not in enhanced_content:
            if "powershell" in enhanced_content:
                pattern = r'(powershell\s+.*WindowsOptimizer\.ps1.*)\n'
                replacement = "echo Starting Windows optimization script...\necho ==========================================\n\n\\1\n\necho ==========================================\necho Optimization script completed.\npause\n"
                enhanced_content = re.sub(pattern, replacement, enhanced_content)
        
        return enhanced_content
        
    def _enhance_powershell_script(self, content):
        """Улучшает PowerShell скрипт, добавляя полезные функции
        
        Args:
            content (str): Содержимое PowerShell скрипта
            
        Returns:
            str: Улучшенное содержимое скрипта
        """
        enhanced_content = content
        
        # Добавляем функцию отображения прогресса, если её нет
        if "function Show-Progress" not in enhanced_content:
            logger.info("Добавляю функцию отображения прогресса")
            progress_function = '''
# Функция отображения прогресса
function Show-Progress {
    param (
        [string]$Activity,
        [int]$PercentComplete
    )
    
    Write-Progress -Activity $Activity -PercentComplete $PercentComplete
    Write-Host "[$($Activity)]: $PercentComplete%" -ForegroundColor Cyan
}
'''
            # Находим место для вставки (после других функций)
            if "function " in enhanced_content:
                function_matches = list(re.finditer(r'function\s+[^{]+{', enhanced_content))
                if function_matches:
                    last_function = function_matches[-1].end()
                    function_end = enhanced_content.find("}", last_function)
                    if function_end > 0:
                        insert_point = enhanced_content.find("\n", function_end) + 1
                        enhanced_content = enhanced_content[:insert_point] + progress_function + enhanced_content[insert_point:]
                    else:
                        enhanced_content = enhanced_content + "\n\n" + progress_function
                else:
                    enhanced_content = enhanced_content + "\n\n" + progress_function
            else:
                enhanced_content = enhanced_content + "\n\n" + progress_function
        
        # Добавляем логирование, если его нет
        if "Write-Log" not in enhanced_content:
            try:
                logger.info("Добавляю логирование действий скрипта")
                log_function = '''
# Функция для записи в лог
function Write-Log {
    param (
        [string]$Message,
        [string]$Level = "INFO"
    )
    
    $LogTime = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogEntry = "[$LogTime] [$Level] $Message"
    
    # Выводим в консоль
    if ($Level -eq "ERROR") {
        Write-Host $LogEntry -ForegroundColor Red
    } elseif ($Level -eq "WARNING") {
        Write-Host $LogEntry -ForegroundColor Yellow
    } else {
        Write-Host $LogEntry -ForegroundColor Green
    }
    
    # Записываем в файл лога
    $LogEntry | Out-File -FilePath $LogPath -Append -Encoding UTF8
}
'''
                # Находим строку с объявлением пути к логу
                log_path_match = re.search(r'\$LogPath\s*=\s*"([^"]+)"', enhanced_content)
                if log_path_match:
                    # Вставляем после объявления пути к логу
                    insert_point = enhanced_content.find("\n", log_path_match.end()) + 1
                    enhanced_content = enhanced_content[:insert_point] + log_function + enhanced_content[insert_point:]
                else:
                    # Ищем блок с кодировкой
                    encoding_match = re.search(r'\$OutputEncoding\s*=\s*\[System\.Text\.Encoding\]::UTF8', enhanced_content)
                    if encoding_match:
                        insert_point = enhanced_content.find("\n", encoding_match.end()) + 1
                        log_path_decl = '\n# Путь к лог-файлу\n$LogPath = "$env:TEMP\\WindowsOptimizer_Log.txt"\n'
                        enhanced_content = enhanced_content[:insert_point] + log_path_decl + log_function + enhanced_content[insert_point:]
                    else:
                        # Вставляем в начало после комментариев
                        first_non_comment = re.search(r'[^#\s]', enhanced_content)
                        if first_non_comment:
                            insert_point = first_non_comment.start()
                            log_path_decl = '# Путь к лог-файлу\n$LogPath = "$env:TEMP\\WindowsOptimizer_Log.txt"\n'
                            enhanced_content = enhanced_content[:insert_point] + log_path_decl + log_function + "\n" + enhanced_content[insert_point:]
                        else:
                            # Вставляем в конец
                            enhanced_content += "\n\n" + log_function
            except Exception as e:
                logger.error(f"Ошибка при добавлении логирования: {e}")
        
        return enhanced_content
    
    def _enhance_markdown(self, content):
        """Улучшает Markdown-документацию, добавляя полезные разделы
        
        Args:
            content (str): Содержимое Markdown-файла
            
        Returns:
            str: Улучшенное содержимое файла
        """
        enhanced_content = content
        
        # Добавляем секцию по устранению проблем, если её нет
        if "## Устранение проблем" not in enhanced_content:
            enhanced_content += "\n\n## Устранение проблем\n\n"
            enhanced_content += "Если вы столкнулись с ошибками при выполнении скриптов, попробуйте следующие решения:\n\n"
            enhanced_content += "1. **Ошибка запуска PowerShell скрипта**:\n"
            enhanced_content += "   - Убедитесь, что запускаете скрипт от имени администратора\n"
            enhanced_content += "   - Проверьте политику выполнения в PowerShell: запустите `Get-ExecutionPolicy` и убедитесь, что разрешено выполнение скриптов\n"
            enhanced_content += "   - Если видите ошибки кодировки, откройте скрипт в Notepad++ и сохраните его в кодировке UTF-8\n\n"
            enhanced_content += "2. **Ошибки доступа к файлам**:\n"
            enhanced_content += "   - Проверьте, что файлы не заблокированы другими программами\n"
            enhanced_content += "   - Проверьте права доступа к директориям, используемым в скрипте\n\n"
            enhanced_content += "3. **Команды не выполняются**:\n"
            enhanced_content += "   - Проверьте наличие необходимых зависимостей и программ\n"
            enhanced_content += "   - Убедитесь, что имена файлов и пути не содержат специальных символов\n\n"
            enhanced_content += "Если проблема не устраняется, отправьте скриншот с ошибкой для получения помощи."
        
        return enhanced_content

# Пример использования:
# validator = ScriptValidator()
# validation_results = validator.validate_scripts(files)
# if validator.should_regenerate_script(validation_results):
#     # Запрос на регенерацию скриптов
# else:
#     # Применение автоматических исправлений
#     fixed_files = validator.repair_common_issues(files) 