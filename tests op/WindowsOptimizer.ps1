# Encoding: UTF-8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Set system to use English language for output
[System.Threading.Thread]::CurrentThread.CurrentUICulture = 'en-US'
[System.Threading.Thread]::CurrentThread.CurrentCulture = 'en-US'

# Проверка прав администратора
function Test-Administrator {
    $user = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($user)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) {
    Write-Warning "This script requires administrator privileges."
    Write-Warning "Please run the script as administrator."
    pause
    exit
}

# Настройка логирования
$LogPath = "${1}:TEMP\WindowsOptimizer_Log.txt"

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
Start-Transcript -Path $LogPath -Append -Force
Write-Host "Logging configured. Log will be saved to: $LogPath" -ForegroundColor Green

# Функция для создания резервных копий настроек
function Backup-Settings {
    param (
        [string]$SettingName,
        [string]$Data
    )
    
    try {
        # Создаем директорию для резервных копий, если ее нет
        $BackupDir = "${1}:USERPROFILE\WindowsOptimizer_Backups"
        if (-not (Test-Path -Path $BackupDir)) {
            New-Item -Path $BackupDir -ItemType Directory -Force | Out-Null
        }
        
        # Формируем имя файла резервной копии
        $Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $BackupFile = "$BackupDir\${SettingName}_$Timestamp.bak"
        
        # Сохраняем данные в файл
        $Data | Out-File -FilePath $BackupFile -Encoding UTF8 -Force
        
        Write-Host "Created backup of $SettingName in file $BackupFile" -ForegroundColor Green
        return $BackupFile
    }
    catch {
        Write-Warning "Failed to create backup of ${SettingName}: ${_}"
        return $null
    }
}

# Функция отображения прогресса
function Show-Progress {
    param (
        [string]$Activity,
        [int]$PercentComplete
    )
    
    Write-Progress -Activity $Activity -PercentComplete $PercentComplete
    Write-Host "[$Activity]: $PercentComplete%" -ForegroundColor Cyan
}

# Основная функция оптимизации
function Optimize-Windows {
    Write-Host "Starting Windows optimization..." -ForegroundColor Green
    
    # Отключение ненужных служб
    Show-Progress -Activity "Optimization" -PercentComplete 10
    Disable-Services
    
    # Очистка диска
    Show-Progress -Activity "Optimization" -PercentComplete 40
    Clean-System
    
    # Оптимизация производительности
    Show-Progress -Activity "Optimization" -PercentComplete 70
    Optimize-Performance
    
    Show-Progress -Activity "Optimization" -PercentComplete 100
    Write-Host "Optimization completed successfully!" -ForegroundColor Green
}

# Функция для отключения ненужных служб
function Disable-Services {
    Write-Host "Disabling unused services..." -ForegroundColor Cyan
    
    $services = @(
        "DiagTrack",          # Телеметрия
        "dmwappushservice",   # Служба WAP Push
        "SysMain",            # Superfetch
        "WSearch"             # Поиск Windows
    )
    
    foreach ($service in $services) {
        try {
            $serviceObj = Get-Service -Name $service -ErrorAction SilentlyContinue
            if ($serviceObj -and $serviceObj.Status -eq "Running") {
                Stop-Service -Name $service -Force -ErrorAction SilentlyContinue
                Set-Service -Name $service -StartupType Disabled -ErrorAction SilentlyContinue
                Write-Host "Service $service successfully disabled" -ForegroundColor Green
            }
        }
        catch {
            Write-Warning "Failed to disable service ${service}: ${_}"
        }
    }
}

# Функция для очистки системы
function Clean-System {
    Write-Host "Cleaning system..." -ForegroundColor Cyan
    
    try {
        # Очистка временных файлов
        if (Test-Path "${1}:TEMP") {
            Remove-Item -Path "${1}:TEMP\*" -Force -Recurse -ErrorAction SilentlyContinue
            Write-Host "User temporary files folder cleaned" -ForegroundColor Green
        }
        
        if (Test-Path "C:\Windows\Temp") {
            Remove-Item -Path "C:\Windows\Temp\*" -Force -Recurse -ErrorAction SilentlyContinue
            Write-Host "System temporary files folder cleaned" -ForegroundColor Green
        }
        
        # Очистка корзины
        try {
            Clear-RecycleBin -Force -ErrorAction SilentlyContinue
            Write-Host "Recycle Bin emptied" -ForegroundColor Green
        } catch {
            Write-Warning "Failed to empty Recycle Bin: ${_}"
        }
        
        # Очистка кэша обновлений Windows
        if (Test-Path "C:\Windows\SoftwareDistribution") {
            try {
                Stop-Service -Name wuauserv -Force -ErrorAction SilentlyContinue
                Remove-Item -Path "C:\Windows\SoftwareDistribution\Download\*" -Force -Recurse -ErrorAction SilentlyContinue
                Start-Service -Name wuauserv -ErrorAction SilentlyContinue
                Write-Host "Windows Update cache cleaned" -ForegroundColor Green
            } catch {
                Write-Warning "Failed to clean Windows Update cache: ${_}"
            }
        }
        
        Write-Host "System cleaning completed successfully" -ForegroundColor Green
    }
    catch {
        Write-Warning "Error during system cleaning: ${_}"
    }
}

# Функция для оптимизации производительности
function Optimize-Performance {
    Write-Host "Optimizing performance..." -ForegroundColor Cyan
    
    try {
        # Отключение визуальных эффектов
        try {
            # Сохраняем текущие настройки
            $currentSettings = Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -ErrorAction SilentlyContinue
            if ($currentSettings) {
                Backup-Settings -SettingName "VisualEffects" -Data ($currentSettings | Out-String)
            }
            
            # Устанавливаем производительность вместо внешнего вида
            Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Name "VisualFXSetting" -Type DWord -Value 2 -ErrorAction SilentlyContinue
            Write-Host "Visual effects set to performance mode" -ForegroundColor Green
        } catch {
            Write-Warning "Failed to configure visual effects: ${_}"
        }
        
        # Отключение автозапуска программ
        try {
            $startupPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
            if (Test-Path $startupPath) {
                # Сохраняем текущие настройки
                $currentStartup = Get-ItemProperty -Path $startupPath -ErrorAction SilentlyContinue
                if ($currentStartup) {
                    Backup-Settings -SettingName "Autorun" -Data ($currentStartup | Out-String)
                }
                
                $startupItems = Get-ItemProperty -Path $startupPath
                foreach ($item in $startupItems.PSObject.Properties) {
                    if ($item.Name -notlike "PS*") {
                        Write-Host "Disabling autostart: $($item.Name)" -ForegroundColor Yellow
                        Remove-ItemProperty -Path $startupPath -Name $item.Name -ErrorAction SilentlyContinue
                    }
                }
                Write-Host "Startup items processing completed" -ForegroundColor Green
            }
        } catch {
            Write-Warning "Failed to process startup items: ${_}"
        }
        
        # Настройка плана электропитания на высокую производительность
        try {
            $powerSchemes = powercfg /list | Where-Object { $_ -match "высок|High" }
            if ($powerSchemes) {
                $highPerfScheme = $powerSchemes -match "высок|High" | Select-Object -First 1
                if ($highPerfScheme -match "([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})") {
                    $schemeGuid = $Matches[1]
                    powercfg /setactive $schemeGuid
                    Write-Host "High performance power plan activated" -ForegroundColor Green
                }
            }
        } catch {
            Write-Warning "Failed to configure power plan: ${_}"
        }
        
        Write-Host "Performance optimization completed successfully" -ForegroundColor Green
    }
    catch {
        Write-Warning "Error during performance optimization: ${_}"
    }
}

# Запуск основной функции
Optimize-Windows

# Остановка логирования
Stop-Transcript
Write-Host "Optimization completed. Log saved to file: $LogPath" -ForegroundColor Green
pause
