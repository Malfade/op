import os
import sys
import logging
from script_validator import ScriptValidator

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Примеры скриптов с распространенными ошибками
EXAMPLE_SCRIPTS = {
    "WindowsOptimizer_bad.ps1": """
# Пример PowerShell скрипта с распространенными ошибками
function Show-Menu {
    Write-Host "Меню оптимизации Windows:"
    Write-Host "1. Очистить временные файлы"
    Write-Host "2. Оптимизировать службы"
    Write-Host "3. Выход"
    
    $choice = Read-Host "Выберите опцию"
    return $choice
}

function Clear-TempFiles {
    # Ошибка: Нет проверки на существование файлов и обработки ошибок
    Remove-Item "$env:TEMP\\*" -Recurse
    Remove-Item "$env:windir\\Temp\\*" -Recurse
    Write-Host "Временные файлы очищены."
}

function Optimize-Services {
    # Ошибка: Нет проверки существования служб
    Set-Service "DiagTrack" -StartupType Disabled
    Set-Service "dmwappushservice" -StartupType Disabled
    # Ошибка: Попытка отключить критическую службу
    Set-Service "WinDefend" -StartupType Disabled
    Write-Host "Службы оптимизированы."
}

# Ошибка: Нет проверки прав администратора
# Ошибка: Несбалансированные фигурные скобки
function Main {
    $choice = Show-Menu
    
    switch ($choice) {
        "1" {
            Clear-TempFiles
        }
        "2" {
            Optimize-Services
        # Ошибка: Пропущена закрывающая скобка для case "2"
        "3" {
            exit
        }
        default {
            Write-Host "Неверный выбор."
        }
    }
}

Main
""",

    "Start-Optimizer_bad.bat": """
@echo off
REM Ошибка: Нет установки кодировки UTF-8
REM Ошибка: Нет проверки прав администратора

REM Ошибка: Нет проверки существования файла
powershell -File "WindowsOptimizer.ps1"

echo Оптимизация завершена.
pause
""",

    "WindowsOptimizer_good.ps1": """
# Пример PowerShell скрипта с правильными практиками
function Check-AdminRights {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    $isAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    
    if (-not $isAdmin) {
        Write-Host "Для запуска скрипта необходимы права администратора." -ForegroundColor Red
        Write-Host "Пожалуйста, запустите скрипт от имени администратора." -ForegroundColor Red
        return $false
    }
    
    return $true
}

function Backup-Settings {
    try {
        $backupFolder = "$env:USERPROFILE\\WindowsOptimizerBackup"
        
        if (-not (Test-Path $backupFolder)) {
            New-Item -Path $backupFolder -ItemType Directory -Force | Out-Null
        }
        
        $backupFile = "$backupFolder\\backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').reg"
        
        # Создание резервной копии реестра
        reg export "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer" "$backupFile" /y | Out-Null
        
        Write-Host "Резервная копия настроек создана: $backupFile" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Warning "Ошибка при создании резервной копии: $_"
        return $false
    }
}

function Show-Menu {
    Write-Host "┌──────────────────────────────────────┐" -ForegroundColor Cyan
    Write-Host "│    Оптимизация Windows 10/11         │" -ForegroundColor Cyan
    Write-Host "├──────────────────────────────────────┤" -ForegroundColor Cyan
    Write-Host "│ 1. Показать информацию о системе     │" -ForegroundColor White
    Write-Host "│ 2. Очистить временные файлы          │" -ForegroundColor White
    Write-Host "│ 3. Оптимизировать службы             │" -ForegroundColor White
    Write-Host "│ 4. Оптимизировать визуальные эффекты │" -ForegroundColor White
    Write-Host "│ 5. Оптимизировать автозагрузку       │" -ForegroundColor White
    Write-Host "│ 6. Запустить все оптимизации         │" -ForegroundColor Green
    Write-Host "│ 7. Восстановить предыдущие настройки │" -ForegroundColor Yellow
    Write-Host "│ 8. Выход                             │" -ForegroundColor Red
    Write-Host "└──────────────────────────────────────┘" -ForegroundColor Cyan
    
    $choice = Read-Host "Выберите опцию (1-8)"
    return $choice
}

function Clear-TempFiles {
    try {
        Write-Host "Очистка временных файлов..." -ForegroundColor Cyan
        
        $tempFolders = @(
            "$env:TEMP",
            "$env:windir\\Temp"
        )
        
        foreach ($folder in $tempFolders) {
            if (Test-Path $folder) {
                Write-Host "Очистка $folder..."
                
                # Перечисляем файлы и папки вместо Remove-Item с маской *
                Get-ChildItem -Path $folder -Force -ErrorAction SilentlyContinue | ForEach-Object {
                    try {
                        if (Test-Path $_.FullName) {
                            Remove-Item $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
                            Write-Verbose "Удален: $($_.FullName)"
                        }
                    }
                    catch {
                        Write-Warning "Не удалось удалить $($_.FullName): $_"
                    }
                }
            }
        }
        
        Write-Host "Очистка временных файлов завершена." -ForegroundColor Green
    }
    catch {
        Write-Warning "Ошибка при очистке временных файлов: $_"
    }
}

function Optimize-Services {
    param([bool]$Revert = $false)
    
    try {
        Write-Host "Оптимизация служб Windows..." -ForegroundColor Cyan
        
        # Список служб для оптимизации (только безопасные службы)
        $servicesToDisable = @(
            "DiagTrack",           # Телеметрия Windows
            "dmwappushservice",    # WAP Push
            "SysMain"              # Superfetch
        )
        
        foreach ($service in $servicesToDisable) {
            # Проверка существования службы
            $svc = Get-Service -Name $service -ErrorAction SilentlyContinue
            
            if ($svc) {
                # Сохраняем текущее состояние для отката
                $currentState = $svc.StartType
                $backupFile = "$env:TEMP\\service_$service.bak"
                $currentState | Out-File -FilePath $backupFile -Force
                
                if ($Revert) {
                    # Восстановление настроек
                    if (Test-Path $backupFile) {
                        $originalState = Get-Content $backupFile
                        Write-Host "Восстановление службы $service в состояние $originalState..."
                        try {
                            Set-Service -Name $service -StartupType $originalState -ErrorAction SilentlyContinue
                            Write-Host "Служба $service восстановлена." -ForegroundColor Green
                        }
                        catch {
                            Write-Warning "Не удалось восстановить службу $service: $_"
                        }
                    }
                }
                else {
                    # Оптимизация
                    try {
                        Set-Service -Name $service -StartupType Disabled -ErrorAction SilentlyContinue
                        Write-Host "Служба $service отключена." -ForegroundColor Green
                    }
                    catch {
                        Write-Warning "Не удалось отключить службу $service: $_"
                    }
                }
            }
            else {
                Write-Host "Служба $service не найдена на данном компьютере." -ForegroundColor Yellow
            }
        }
    }
    catch {
        Write-Warning "Произошла ошибка при оптимизации служб: $_"
    }
}

function Main {
    if (-not (Check-AdminRights)) {
        exit
    }
    
    Write-Host "Запуск оптимизации Windows..." -ForegroundColor Cyan
    
    # Создание резервной копии настроек
    Backup-Settings | Out-Null
    
    $exit = $false
    
    while (-not $exit) {
        $choice = Show-Menu
        
        switch ($choice) {
            "1" {
                # Показать информацию о системе
                try {
                    $osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
                    $cpuInfo = Get-CimInstance -ClassName Win32_Processor
                    $ramInfo = Get-CimInstance -ClassName Win32_ComputerSystem
                    
                    Write-Host "Информация о системе:" -ForegroundColor Cyan
                    Write-Host "  ОС: $($osInfo.Caption) $($osInfo.Version)" -ForegroundColor White
                    Write-Host "  Процессор: $($cpuInfo.Name)" -ForegroundColor White
                    Write-Host "  ОЗУ: $([math]::Round($ramInfo.TotalPhysicalMemory / 1GB, 2)) ГБ" -ForegroundColor White
                }
                catch {
                    Write-Warning "Ошибка при получении информации о системе: $_"
                }
            }
            "2" {
                Clear-TempFiles
            }
            "3" {
                Optimize-Services
            }
            "6" {
                Clear-TempFiles
                Optimize-Services
            }
            "7" {
                Optimize-Services -Revert $true
            }
            "8" {
                $exit = $true
            }
            default {
                Write-Host "Неверный выбор. Пожалуйста, выберите опцию от 1 до 8." -ForegroundColor Yellow
            }
        }
        
        if (-not $exit) {
            Write-Host "`nНажмите Enter для возврата в меню..."
            Read-Host | Out-Null
            Clear-Host
        }
    }
    
    Write-Host "Завершение работы скрипта оптимизации Windows." -ForegroundColor Cyan
}

# Запуск основной функции
Main
""",

    "Start-Optimizer_good.bat": """
@echo off
chcp 65001 >nul
title Запуск оптимизации Windows

REM Проверка прав администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Для запуска необходимы права администратора.
    echo Пожалуйста, запустите скрипт от имени администратора.
    pause
    exit /b 1
)

REM Проверка наличия файла скрипта
if not exist "WindowsOptimizer.ps1" (
    echo Не найден файл WindowsOptimizer.ps1
    echo Убедитесь, что файл находится в той же папке, что и этот .bat файл.
    pause
    exit /b 1
)

REM Создание временной копии скрипта с правильной кодировкой
powershell -NoProfile -Command "$content = Get-Content -Path 'WindowsOptimizer.ps1' -Raw; [System.IO.File]::WriteAllText('WindowsOptimizer_temp.ps1', $content, [System.Text.Encoding]::UTF8)" >nul 2>&1

REM Запуск PowerShell скрипта с обходом политики выполнения
echo Запуск скрипта оптимизации Windows...
powershell -ExecutionPolicy Bypass -NoProfile -File "WindowsOptimizer_temp.ps1" -Encoding UTF8

REM Удаление временной копии скрипта
if exist "WindowsOptimizer_temp.ps1" del "WindowsOptimizer_temp.ps1" >nul 2>&1

pause
exit /b 0
"""
}

def test_validator():
    """Функция тестирования валидатора скриптов"""
    # Создаем экземпляр валидатора
    validator = ScriptValidator()
    
    # Проверяем скрипты с ошибками
    print("\n=== Тестирование скриптов с ошибками ===")
    bad_scripts = {
        "WindowsOptimizer.ps1": EXAMPLE_SCRIPTS["WindowsOptimizer_bad.ps1"],
        "Start-Optimizer.bat": EXAMPLE_SCRIPTS["Start-Optimizer_bad.bat"]
    }
    
    validation_results = validator.validate_scripts(bad_scripts)
    total_issues = 0
    
    for filename, issues in validation_results.items():
        total_issues += len(issues)
        print(f"\nФайл: {filename} ({len(issues)} проблем)")
        for issue in issues:
            print(f"  - {issue}")
    
    print(f"\nВсего найдено {total_issues} проблем в плохих скриптах")
    print(f"Требуется регенерация: {validator.should_regenerate_script(validation_results)}")
    
    # Пытаемся автоматически исправить скрипты
    print("\n=== Тестирование автоматического исправления ===")
    try:
        fixed_scripts = validator.repair_common_issues(bad_scripts)
        
        # Проверяем исправленные скрипты
        fixed_validation = validator.validate_scripts(fixed_scripts)
        fixed_issues = sum(len(issues) for issues in fixed_validation.values())
        
        print(f"После исправлений осталось {fixed_issues} проблем из {total_issues}")
        
        for filename, issues in fixed_validation.items():
            if issues:
                print(f"\nФайл после исправления: {filename} ({len(issues)} проблем)")
                for issue in issues:
                    print(f"  - {issue}")
    except Exception as e:
        print(f"Ошибка при автоматическом исправлении: {e}")
    
    # Проверяем хорошие скрипты
    print("\n=== Тестирование хороших скриптов ===")
    good_scripts = {
        "WindowsOptimizer.ps1": EXAMPLE_SCRIPTS["WindowsOptimizer_good.ps1"],
        "Start-Optimizer.bat": EXAMPLE_SCRIPTS["Start-Optimizer_good.bat"]
    }
    
    good_validation = validator.validate_scripts(good_scripts)
    good_issues = sum(len(issues) for issues in good_validation.values())
    
    for filename, issues in good_validation.items():
        if issues:
            print(f"\nФайл: {filename} ({len(issues)} проблем)")
            for issue in issues:
                print(f"  - {issue}")
    
    print(f"\nВсего найдено {good_issues} проблем в хороших скриптах")
    print(f"Требуется регенерация: {validator.should_regenerate_script(good_validation)}")
    
    return total_issues, fixed_issues, good_issues

if __name__ == "__main__":
    print("Тестирование валидатора скриптов")
    bad_issues, fixed_issues, good_issues = test_validator()
    
    # Вывод общего результата
    print("\n=== Итоговые результаты ===")
    print(f"Проблемы в плохих скриптах: {bad_issues}")
    print(f"Проблемы после автоисправления: {fixed_issues}")
    print(f"Улучшение: {bad_issues - fixed_issues} проблем ({(1 - fixed_issues/bad_issues)*100:.1f}%)")
    print(f"Проблемы в хороших скриптах: {good_issues}")
    
    # Возвращаем код успеха, если автоисправление улучшило ситуацию
    if fixed_issues < bad_issues:
        sys.exit(0)
    else:
        sys.exit(1) 