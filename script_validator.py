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
    """Класс для валидации и исправления скриптов оптимизации"""
    
    def __init__(self):
        """Инициализация валидатора"""
        self.validation_rules = {
            "ps_syntax": [
                # Несбалансированные скобки
                (r"\{[^{}]*$", "Несбалансированные скобки (отсутствует закрывающая скобка)"),
                (r"^[^{}]*\}", "Несбалансированные скобки (отсутствует открывающая скобка)"),
                # Незакрытая строка
                (r"\"[^\"]*$", "Незакрытая строка (отсутствует закрывающая кавычка)"),
                # Незавершенная строка присваивания
                (r"\$[A-Za-z_]+\s*=\s*[^;{(\[@]+$(?!\s*$)(?!\s*#)", "Незавершенная строка присваивания (отсутствует ;)"),
                # Незавершенный блок catch
                (r"catch\s*\{[^}]*$", "Незавершенный блок catch"),
                # Незавершенный блок if
                (r"if\s*\([^)]*$", "Незавершенный блок if"),
            ],
            "file_access": [
                # Remove-Item без параметра -Force
                (r"Remove-Item\s+[^-]+(?!-Force)", "Remove-Item без параметра -Force"),
                # Отсутствие проверки Test-Path перед операциями с файлами
                (r"(Get-Content|Set-Content|Remove-Item|Copy-Item|Move-Item)(?!\s+.+?Test-Path)", 
                 "Отсутствие проверки Test-Path перед операциями с файлами"),
            ],
            "security": [
                # Потенциально опасные команды без проверок
                (r"(Invoke-Expression|iex|Invoke-Command)(?!\s+.+?validate|authorize)", 
                 "Использование потенциально опасных команд без проверок"),
                # Доступ к системным папкам без проверок
                (r"(\\Windows\\System32|C:\\Windows)(?!\s+.+?Test-Path)", 
                 "Доступ к системным папкам без проверок"),
            ],
            "encoding": [
                # Отсутствие установки кодировки UTF-8
                (r"^(?!.*\$OutputEncoding\s*=\s*\[System\.Text\.Encoding\]::UTF8).*$", 
                 "Отсутствие установки кодировки UTF-8"),
            ]
        }
        
        self.required_blocks = [
            # Минимум один блок try-catch
            (r"try\s*{[\s\S]*?}\s*catch\s*{", "Отсутствие блоков обработки ошибок (try-catch)"),
            # Использование Get-Service с параметрами безопасности
            (r"Get-Service[\s\S]*?(?:-ErrorAction SilentlyContinue|Select-Object)", 
             "Небезопасное использование Get-Service"),
            # Наличие функции меню
            (r"function\s+(?:Show-Menu|Display)", "Отсутствие функции меню"),
            # Наличие функции резервного копирования
            (r"(?:function\s+Backup-Settings|# Создание резервной копии|# Back)", 
             "Отсутствие функции резервного копирования"),
        ]
    
    def validate_files(self, files):
        """Валидация скриптов
        
        Args:
            files (dict): Словарь с файлами (имя файла -> содержимое)
            
        Returns:
            dict: Результаты валидации (имя файла -> список ошибок)
        """
        validation_results = {}
        
        for filename, content in files.items():
            if filename.endswith('.ps1'):
                # Валидация PowerShell скрипта
                validation_results[filename] = self.validate_powershell_script(content)
            elif filename.endswith('.bat'):
                # Валидация BAT скрипта
                validation_results[filename] = self.validate_batch_script(content)
        
        return validation_results
    
    def validate_powershell_script(self, content):
        """Валидация PowerShell скрипта
        
        Args:
            content (str): Содержимое PowerShell скрипта
            
        Returns:
            list: Список найденных ошибок
        """
        issues = []
        
        try:
            # Логирование начала валидации
            logger.info(f"Начинаю валидацию PowerShell скрипта длиной {len(content)} символов")
            
            # Разбиваем скрипт на строки для анализа
            lines = content.split('\n')
            logger.info(f"Скрипт содержит {len(lines)} строк")
            
            # Проверка на балансировку скобок
            if not self._are_braces_balanced(content):
                issues.append("Несбалансированные скобки в скрипте (ps_syntax)")
            
            # Проверка на установку кодировки UTF-8
            if "$OutputEncoding = [System.Text.Encoding]::UTF8" not in content:
                issues.append("Отсутствует установка кодировки UTF-8 (encoding)")
            
            # Проверка правил для различных категорий
            for category, rules in self.validation_rules.items():
                logger.info(f"Проверка шаблонов категории {category}")
                
                # Пропуск некоторых правил в зависимости от содержимого скрипта
                if category == "ps_syntax" and ("Get-Service" in content or "Get-CimInstance" in content):
                    logger.info(f"Пропускаю проверку шаблона ({rules[3][0]}) из-за наличия Get-Service/Get-CimInstance")
                    continue
                
                # Проверка правил на основе регулярных выражений
                for pattern, message in rules:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    match_count = 0
                    
                    for match in matches:
                        match_count += 1
                        # Определяем номер строки для сообщения об ошибке
                        line_number = content[:match.start()].count('\n') + 1
                        issue = f"{category} в строке {line_number}"
                        logger.info(f"Добавляю ошибку: {issue}")
                        issues.append(issue)
                    
                    if match_count > 0:
                        logger.info(f"Найдено {match_count} совпадений для шаблона ({pattern})")
            
            # Проверка наличия обязательных блоков
            logger.info(f"Проверка шаблонов категории security")
            
            # Пропуск некоторых проверок в зависимости от содержимого
            if "Test-Path" in content and ("if" in content or "elseif" in content):
                logger.info(f"Скрипт содержит Test-Path и проверки условий, исключаю соответствующие требования")
            
            # Проверка обязательных блоков
            for pattern, message in self.required_blocks:
                if re.search(pattern, content):
                    logger.info(f"Обязательный блок найден: {pattern}")
                else:
                    issues.append(f"Отсутствует обязательный блок: {message} (required_block)")
            
            # Проверка наличия проверок перед операциями с файлами
            lines_with_file_ops = [i for i, line in enumerate(lines) if re.search(r"(Get-Content|Set-Content|Remove-Item|Copy-Item|Move-Item)", line)]
            
            for line_idx in lines_with_file_ops:
                line_number = line_idx + 1
                
                # Проверка наличия Test-Path перед операцией
                has_test_path = False
                
                # Ищем Test-Path в предыдущих строках в том же блоке
                for i in range(line_idx - 1, max(0, line_idx - 10), -1):
                    if "Test-Path" in lines[i]:
                        has_test_path = True
                        logger.info(f"Найдена проверка Test-Path перед {lines[line_idx][:20]} в строке {line_number}")
                        break
                    
                    # Если встретили начало блока, останавливаем поиск
                    if re.search(r"^\s*(function|if|else|elseif|for|while|switch|process)\s", lines[i]):
                        break
                
                if not has_test_path and "Remove-Item" in lines[line_idx]:
                    # Проверяем наличие параметра -Force
                    if "-Force" not in lines[line_idx]:
                        issues.append(f"Отсутствует параметр -Force в Remove-Item в строке {line_number} (file_access)")
            
            logger.info(f"Валидация PowerShell скрипта завершена, найдено {len(issues)} проблем")
            
            return issues
            
        except Exception as e:
            logger.error(f"Ошибка при валидации PowerShell скрипта: {e}")
            issues.append(f"Ошибка валидации: {str(e)}")
            return issues
    
    def validate_batch_script(self, content):
        """Валидация BAT скрипта
        
        Args:
            content (str): Содержимое BAT скрипта
            
        Returns:
            list: Список найденных ошибок
        """
        issues = []
        
        try:
            # Базовые проверки для BAT скрипта
            if "chcp 65001" not in content.lower() and "chcp 1251" not in content.lower():
                issues.append("Отсутствует установка кодировки (bat_syntax)")
            
            if "powershell -executionpolicy bypass" not in content.lower():
                issues.append("Отсутствует параметр ExecutionPolicy Bypass (bat_syntax)")
            
            if "administrator" not in content.lower() and "админ" not in content.lower():
                issues.append("Отсутствует проверка прав администратора (bat_syntax)")
            
            return issues
            
        except Exception as e:
            logger.error(f"Ошибка при валидации BAT скрипта: {e}")
            issues.append(f"Ошибка валидации: {str(e)}")
            return issues
    
    def _are_braces_balanced(self, content):
        """Проверка балансировки скобок в скрипте
        
        Args:
            content (str): Содержимое скрипта
            
        Returns:
            bool: True если скобки сбалансированы, иначе False
        """
        stack = []
        for char in content:
            if char == '{':
                stack.append(char)
            elif char == '}':
                if not stack or stack.pop() != '{':
                    return False
        
        return len(stack) == 0
    
    def enhance_scripts(self, files):
        """Улучшение скриптов с добавлением полезных функций
        
        Args:
            files (dict): Словарь с файлами (имя файла -> содержимое)
            
        Returns:
            dict: Улучшенные файлы
        """
        enhanced_files = {}
        
        for filename, content in files.items():
            if filename.endswith('.ps1'):
                logger.info(f"Улучшаю PowerShell скрипт: {filename}")
                enhanced_content = self._enhance_powershell_script(content)
                enhanced_files[filename] = enhanced_content
            elif filename.endswith('.bat'):
                logger.info(f"Улучшаю BAT скрипт: {filename}")
                enhanced_content = self._enhance_batch_script(content)
                enhanced_files[filename] = enhanced_content
            else:
                enhanced_files[filename] = content
        
        return enhanced_files
    
    def _enhance_powershell_script(self, content):
        """Улучшение PowerShell скрипта
        
        Args:
            content (str): Содержимое PowerShell скрипта
            
        Returns:
            str: Улучшенное содержимое скрипта
        """
        # Добавление функции отображения прогресса, если ее нет
        if "function Show-Progress" not in content:
            try:
                logger.info("Добавляю функцию отображения прогресса")
                progress_function = """
# Функция для отображения прогресса выполнения
function Show-Progress {
    param (
        [string]$Activity,
        [int]$PercentComplete
    )
    
    Write-Progress -Activity $Activity -PercentComplete $PercentComplete
    Write-Host "$Activity: $PercentComplete%" -ForegroundColor Cyan
}
"""
                # Находим место для добавления функции - после комментариев в начале файла
                lines = content.split('\n')
                insertion_point = 0
                
                for i, line in enumerate(lines):
                    if line.strip() and not line.strip().startswith('#') and not line.strip().startswith('$'):
                        insertion_point = i
                        break
                
                # Вставляем функцию
                lines.insert(insertion_point, progress_function)
                content = '\n'.join(lines)
            except Exception as e:
                logger.error(f"Ошибка при добавлении функции отображения прогресса: {e}")
        
        # Добавление логирования, если его нет
        if "Start-Transcript" not in content:
            try:
                logger.info("Добавляю логирование действий скрипта")
                logging_code = """
# Настройка логирования
$LogPath = "$env:TEMP\WindowsOptimizer_Log.txt"
Start-Transcript -Path $LogPath -Append -Force
Write-Host "Логирование настроено. Лог будет сохранен в файл: $LogPath" -ForegroundColor Green
"""
                # Добавляем логирование после настройки кодировки
                if "$OutputEncoding = [System.Text.Encoding]::UTF8" in content:
                    content = content.replace("$OutputEncoding = [System.Text.Encoding]::UTF8", 
                                             "$OutputEncoding = [System.Text.Encoding]::UTF8\n" + logging_code)
                else:
                    # Если нет настройки кодировки, добавляем в начало
                    content = logging_code + content
            except Exception as e:
                logger.error(f"Ошибка при добавлении логирования: {e}")
        
        return content
    
    def _enhance_batch_script(self, content):
        """Улучшение BAT скрипта
        
        Args:
            content (str): Содержимое BAT скрипта
            
        Returns:
            str: Улучшенное содержимое скрипта
        """
        # Добавление проверки прав администратора, если ее нет
        if "administrator" not in content.lower() and "админ" not in content.lower():
            admin_check = """
:: Проверка прав администратора
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Этот скрипт требует запуска от имени администратора.
    echo Пожалуйста, запустите скрипт от имени администратора.
    pause
    exit /b 1
)
"""
            # Находим место после @echo off для вставки
            if "@echo off" in content:
                content = content.replace("@echo off", "@echo off" + admin_check)
            else:
                content = "@echo off" + admin_check + content
        
        # Добавление кодировки, если ее нет
        if "chcp 65001" not in content.lower() and "chcp 1251" not in content.lower():
            encoding_line = "chcp 65001 >nul\n"
            # Добавляем после @echo off или в начало
            if "@echo off" in content:
                content = content.replace("@echo off", "@echo off\n" + encoding_line)
            else:
                content = encoding_line + content
        
        return content
    
    def repair_common_issues(self, files):
        """Исправление распространенных проблем в скриптах
        
        Args:
            files (dict): Словарь с файлами (имя файла -> содержимое)
            
        Returns:
            dict: Исправленные файлы
        """
        repaired_files = {}
        
        for filename, content in files.items():
            if filename.endswith('.ps1'):
                repaired_content = self._repair_powershell_script(content)
                repaired_files[filename] = repaired_content
            elif filename.endswith('.bat'):
                repaired_content = self._repair_batch_script(content)
                repaired_files[filename] = repaired_content
            else:
                repaired_files[filename] = content
        
        return repaired_files
    
    def _repair_powershell_script(self, content):
        """Исправление распространенных проблем в PowerShell скрипте
        
        Args:
            content (str): Содержимое PowerShell скрипта
            
        Returns:
            str: Исправленное содержимое скрипта
        """
        repaired_content = content
        
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
                repaired_content += '\n' + '}' * (open_braces - close_braces)
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
        except Exception as e:
            logger.error(f"Ошибка при исправлении баланса скобок: {e}")
        
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
        Write-Warning "Не удалось создать резервную копию $SettingName: $_"
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
        
        # Добавление установки кодировки UTF-8, если ее нет
        if "$OutputEncoding = [System.Text.Encoding]::UTF8" not in repaired_content:
            encoding_setting = "$OutputEncoding = [System.Text.Encoding]::UTF8\n"
            # Добавляем в начало файла
            repaired_content = encoding_setting + repaired_content
        
        return repaired_content
    
    def _repair_batch_script(self, content):
        """Исправление распространенных проблем в BAT скрипте
        
        Args:
            content (str): Содержимое BAT скрипта
            
        Returns:
            str: Исправленное содержимое скрипта
        """
        repaired_content = content
        
        # Добавление установки кодировки UTF-8, если ее нет
        if "chcp 65001" not in repaired_content.lower():
            encoding_line = "chcp 65001 >nul\n"
            # Добавляем после @echo off или в начало
            if "@echo off" in repaired_content:
                repaired_content = repaired_content.replace("@echo off", "@echo off\n" + encoding_line)
            else:
                repaired_content = encoding_line + repaired_content
        
        # Добавление параметра -ExecutionPolicy Bypass, если его нет
        if "powershell" in repaired_content.lower() and "-executionpolicy bypass" not in repaired_content.lower():
            repaired_content = repaired_content.replace("powershell", "powershell -ExecutionPolicy Bypass")
        
        # Добавление проверки прав администратора, если ее нет
        if "administrator" not in repaired_content.lower() and "админ" not in repaired_content.lower():
            admin_check = """
:: Проверка прав администратора
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Этот скрипт требует запуска от имени администратора.
    echo Пожалуйста, запустите скрипт от имени администратора.
    pause
    exit /b 1
)
"""
            # Находим место после @echo off для вставки
            if "@echo off" in repaired_content:
                repaired_content = repaired_content.replace("@echo off", "@echo off" + admin_check)
            else:
                repaired_content = "@echo off" + admin_check + repaired_content
        
        return repaired_content

    def should_regenerate_script(self, validation_results):
        """Проверка необходимости повторной генерации скрипта
        
        Args:
            validation_results (dict): Результаты валидации
            
        Returns:
            bool: True если нужна повторная генерация, иначе False
        """
        # Подсчет общего количества ошибок
        total_errors = sum(len(issues) for issues in validation_results.values())
        
        # Если слишком много ошибок, стоит перегенерировать скрипт
        return total_errors > 10

# Пример использования:
# validator = ScriptValidator()
# validation_results = validator.validate_scripts(files)
# if validator.should_regenerate_script(validation_results):
#     # Запрос на регенерацию скриптов
# else:
#     # Применение автоматических исправлений
#     fixed_files = validator.repair_common_issues(files) 