function Backup-Settings {
    param($path)

    if (!(Test-Path $path)) {
        New-Item -ItemType Directory -Path $path | Out-Null
    }
    
    # Бэкап реестра
    reg export "HKCU\SOFTWARE" "$path\HKCU_SOFTWARE.reg" /y
    reg export "HKLM\SOFTWARE" "$path\HKLM_SOFTWARE.reg" /y
    reg export "HKLM\SYSTEM" "$path\HKLM_SYSTEM.reg" /y

    # Бэкап файла подкачки
    Copy-Item -Path "C:\pagefile.sys" -Destination "$path\pagefile.sys" -Force
}

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (!$isAdmin) {
    Write-Host "Скрипт должен быть запущен от имени администратора. Выход..."
    Exit
}

# Оптимизация производительности
function Optimize-Performance {
    try {
        # Отключение визуальных эффектов
        Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "DragFullWindows" -Value 0
        Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "MenuShowDelay" -Value 0
        Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "UserPreferencesMask" -Value ([byte[]](144,18,3,128,16,0,0,0))
        Set-ItemProperty -Path "HKCU:\Control Panel\Desktop\WindowMetrics" -Name "MinAnimate" -Value 0
        Set-ItemProperty -Path "HKCU:\Control Panel\Keyboard" -Name "KeyboardDelay" -Value 0
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "ListviewAlphaSelect" -Value 0
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "ListviewShadow" -Value 0
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -Name "TaskbarAnimations" -Value 0
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Name "VisualFXSetting" -Value 3
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\DWM" -Name "EnableAeroPeek" -Value 0

        # Отключение индексации
        Set-Service -Name "WSearch" -StartupType Disabled
        Stop-Service -Name "WSearch" -WarningAction SilentlyContinue

        # Оптимизация файла подкачки
        $mem = Get-WmiObject -Class Win32_ComputerSystem | Select-Object TotalPhysicalMemory
        $memSize = [Math]::Round($mem.TotalPhysicalMemory/1MB)  
        $recommendedPageSize = [Math]::Round($memSize / 1024 * 1.5) * 1024
        Set-WmiInstance -Class Win32_PageFileSetting -Arguments @{Name="C:\pagefile.sys"; InitialSize = $recommendedPageSize; MaximumSize = $recommendedPageSize}

        Write-Host "Оптимизация производительности выполнена успешно"
    }
    catch {
        Write-Host "Ошибка при оптимизации производительности: $_"
    }
}

# Очистка временных файлов и диска
function Clean-Disk {
    # Удаление временных файлов
    try {
        Remove-Item -Path "$env:TEMP\*" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -Path "$env:windir\Temp\*" -Recurse -Force -ErrorAction SilentlyContinue
        Remove-Item -Path "$env:windir\Prefetch\*" -Recurse -Force -ErrorAction SilentlyContinue
        
        Write-Host "Временные файлы удалены успешно"  
    }
    catch {
        Write-Host "Ошибка при удалении временных файлов: $_"
    }
    
    # Очистка диска
    try {
        cleanmgr /sagerun:1 | Out-Null
        
        Write-Host "Очистка диска выполнена успешно" 
    }
    catch {
        Write-Host "Ошибка при очистке диска: $_"
    }
}

# Отключение ненужных служб
function Disable-Services {
    $services = @(
        "XblAuthManager",
        "XblGameSave", 
        "XboxNetApiSvc",
        "XboxGipSvc",
        "WalletService",
        "RetailDemo",
        "WbioSrvc",
        "WerSvc"
    )

    foreach ($service in $services) {
        try {
            if (Get-Service -Name $service -ErrorAction SilentlyContinue) {
                Set-Service -Name $service -StartupType Disabled
                Stop-Service -Name $service -WarningAction SilentlyContinue
            }
        }
        catch {
            Write-Host "Ошибка при отключении службы $service`: $_"
        }
    }

    Write-Host "Службы отключены успешно"
}

# Логирование действий
function Write-LogEntry {
    param($message)

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"  
    Add-Content -Path "optimizer.log" -Value "$timestamp - $message"
}

# Вызов функций оптимизации
Write-Host "Создание резервной копии параметров..."
Backup-Settings -Path "$env:USERPROFILE\SettingsBackup"
Write-LogEntry "Резервная копия параметров создана"

Write-Host "Оптимизация производительности..."
Optimize-Performance
Write-LogEntry "Оптимизация производительности выполнена"

Write-Host "Очистка временных файлов и диска..."
Clean-Disk
Write-LogEntry "Очистка временных файлов и диска выполнена"

Write-Host "Отключение ненужных служб..."
Disable-Services
Write-LogEntry "Отключение ненужных служб выполнено"

Write-Host "Оптимизация Windows завершена. Подробности см. в файле optimizer.log"
