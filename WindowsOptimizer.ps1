# WindowsOptimizer.ps1
# Скрипт для оптимизации Windows
# Автор: Бот оптимизации Windows

# Устанавливаем кодировку
$OutputEncoding = [System.Text.Encoding]::UTF8

# Функция для записи в лог
function Write-Log {
    param (
        [string]$Message
    )

    $LogDir = Join-Path -Path $PSScriptRoot -ChildPath "WindowsOptimizer_Logs"
    if (-not (Test-Path -Path $LogDir)) {
        New-Item -Path $LogDir -ItemType Directory -Force | Out-Null
    }

    $LogFile = Join-Path -Path $LogDir -ChildPath "Optimizer_Log_$(Get-Date -Format 'yyyy-MM-dd').log"
    $TimeStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$TimeStamp - $Message" | Out-File -FilePath $LogFile -Append -Encoding UTF8
    Write-Host $Message
}

# Функция для создания резервных копий
function Backup-Settings {
    param (
        [string]$Name,
        [string]$Path
    )

    try {
        Write-Log "Создание резервной копии для $Name"
        
        $BackupDir = Join-Path -Path $PSScriptRoot -ChildPath "WindowsOptimizer_Backups"
        if (-not (Test-Path -Path $BackupDir)) {
            New-Item -Path $BackupDir -ItemType Directory -Force | Out-Null
        }
        
        $BackupFile = Join-Path -Path $BackupDir -ChildPath "$($Name)_$(Get-Date -Format 'yyyy-MM-dd_HHmmss').reg"
        
        if (Test-Path -Path $Path) {
            # Экспорт ключа реестра
            if ($Path -like "HKLM:*" -or $Path -like "HKCU:*") {
                $RegExe = "reg.exe"
                $RegPath = $Path -replace "HKLM:", "HKLM" -replace "HKCU:", "HKCU"
                & $RegExe export $RegPath $BackupFile /y | Out-Null
            }
            # Копирование файла
            else {
                Copy-Item -Path $Path -Destination $BackupFile -Force
            }
            
            Write-Log "Резервная копия создана: $BackupFile"
        }
        else {
            Write-Log "Путь $Path не существует, резервная копия не создана"
        }
    }
    catch {
        Write-Log "Ошибка при создании резервной копии: $_"
    }
}

# Функция для оптимизации производительности
function Optimize-Performance {
    try {
        Write-Log "Запуск оптимизации производительности..."
        
        # Резервное копирование ключей реестра перед изменением
        Backup-Settings -Name "PerformanceSettings" -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
        Backup-Settings -Name "SystemPerformance" -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"

        # Визуальные эффекты - оптимизация для производительности
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Name "VisualFXSetting" -Value 2 -Type DWord -Force -ErrorAction SilentlyContinue
        
        # Отключение анимации элементов окна
        Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "UserPreferencesMask" -Value ([byte[]](0x90, 0x12, 0x01, 0x80)) -Force -ErrorAction SilentlyContinue
        
        # Отключение прозрачности интерфейса
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize" -Name "EnableTransparency" -Value 0 -Type DWord -Force -ErrorAction SilentlyContinue
        
        # Настройка план электропитания на высокую производительность
        $guid = (powercfg /list | Where-Object {$_ -match "High performance"} | ForEach-Object {($_ -split "\(")[1].Split(")")[0]})
        if ($guid) {
            powercfg -setactive $guid
            Write-Log "Установлен план электропитания: Высокая производительность"
        }
        
        # Оптимизация виртуальной памяти
        # Резервное копирование настроек перед изменением
        Backup-Settings -Name "PageFile" -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management"
        
        # Получаем информацию об объеме физической памяти
        $memory = (Get-CimInstance -ClassName Win32_PhysicalMemory | Measure-Object -Property Capacity -Sum).Sum / 1GB
        $pageFileSize = [Math]::Max(8, [Math]::Round($memory * 1.5))
        
        # Настраиваем размер файла подкачки
        $computerSystem = Get-CimInstance -ClassName Win32_ComputerSystem
        $computerSystem | Set-CimInstance -Property @{AutomaticManagedPagefile=$false}
        
        $pageFileSetting = Get-CimInstance -ClassName Win32_PageFileSetting
        if ($pageFileSetting) {
            $pageFileSetting | Set-CimInstance -Property @{InitialSize=$pageFileSize*1024; MaximumSize=$pageFileSize*1024}
        } else {
            Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" -Name "PagingFiles" -Value "C:\pagefile.sys $pageFileSize $pageFileSize" -Force -ErrorAction SilentlyContinue
        }
        
        Write-Log "Файл подкачки настроен: $pageFileSize ГБ"
        
        # Приоритет фоновых служб
        Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\PriorityControl" -Name "Win32PrioritySeparation" -Value 38 -Type DWord -Force -ErrorAction SilentlyContinue
        
        Write-Log "Оптимизация производительности завершена"
    }
    catch {
        Write-Log "Ошибка при оптимизации производительности: $_"
    }
}

# Функция для очистки временных файлов
function Clean-Temp-Files {
    try {
        Write-Log "Запуск очистки временных файлов..."
        
        # Очистка временных файлов пользователя
        if (Test-Path -Path $env:TEMP) {
            Get-ChildItem -Path $env:TEMP -Force -ErrorAction SilentlyContinue | 
                Where-Object { $_.FullName -ne $env:TEMP } | 
                Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
            Write-Log "Очищена папка временных файлов пользователя: $env:TEMP"
        }
        
        # Очистка Windows Temp
        if (Test-Path -Path $env:windir\Temp) {
            Get-ChildItem -Path "$env:windir\Temp" -Force -ErrorAction SilentlyContinue | 
                Where-Object { $_.FullName -ne "$env:windir\Temp" } | 
                Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
            Write-Log "Очищена папка временных файлов Windows: $env:windir\Temp"
        }
        
        # Очистка папки загрузок обновлений Windows
        if (Test-Path -Path $env:windir\SoftwareDistribution\Download) {
            Get-ChildItem -Path "$env:windir\SoftwareDistribution\Download" -Force -ErrorAction SilentlyContinue | 
                Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
            Write-Log "Очищена папка загрузок обновлений Windows"
        }
        
        # Очистка корзины
        Clear-RecycleBin -Force -ErrorAction SilentlyContinue
        Write-Log "Очищена корзина"
        
        # Запуск встроенного средства очистки диска
        Start-Process -FilePath cleanmgr.exe -ArgumentList "/sagerun:1" -Wait -WindowStyle Hidden -ErrorAction SilentlyContinue
        Write-Log "Запущена стандартная очистка диска"
        
        Write-Log "Очистка временных файлов завершена"
    }
    catch {
        Write-Log "Ошибка при очистке временных файлов: $_"
    }
}

# Функция для отключения ненужных служб
function Disable-Unnecessary-Services {
    try {
        Write-Log "Отключение ненужных служб и компонентов..."
        
        # Список служб для отключения
        $servicesToDisable = @(
            # Некритичные службы, которые можно безопасно отключить
            "DiagTrack",              # Телеметрия и диагностика
            "dmwappushservice",       # Служба WAP Push
            "MapsBroker",             # Брокер загрузки карт
            "lfsvc",                  # Служба геолокации
            "XblAuthManager",         # Менеджер авторизации Xbox Live
            "XblGameSave",            # Служба сохранения игр Xbox Live
            "XboxNetApiSvc",          # Сетевая служба Xbox Live
            "OneSyncSvc",             # Синхронизация
            "RetailDemo"              # Демонстрационный режим для магазинов
        )
        
        foreach ($service in $servicesToDisable) {
            # Проверяем, существует ли служба
            if (Get-Service -Name $service -ErrorAction SilentlyContinue) {
                # Резервное копирование состояния службы
                $serviceInfo = Get-Service -Name $service
                Backup-Settings -Name "Service_$service" -Path "HKLM:\SYSTEM\CurrentControlSet\Services\$service"
                
                # Останавливаем и отключаем службу
                Stop-Service -Name $service -Force -ErrorAction SilentlyContinue
                Set-Service -Name $service -StartupType Disabled -ErrorAction SilentlyContinue
                Write-Log "Служба $service отключена"
            }
            else {
                Write-Log "Служба $service не найдена"
            }
        }
        
        # Отключение запланированных задач связанных с телеметрией
        $scheduledTasksToDisable = @(
            "\Microsoft\Windows\Application Experience\Microsoft Compatibility Appraiser",
            "\Microsoft\Windows\Application Experience\ProgramDataUpdater",
            "\Microsoft\Windows\Autochk\Proxy",
            "\Microsoft\Windows\Customer Experience Improvement Program\Consolidator",
            "\Microsoft\Windows\Customer Experience Improvement Program\UsbCeip",
            "\Microsoft\Windows\DiskDiagnostic\Microsoft-Windows-DiskDiagnosticDataCollector"
        )
        
        foreach ($task in $scheduledTasksToDisable) {
            Disable-ScheduledTask -TaskName $task -ErrorAction SilentlyContinue | Out-Null
            Write-Log "Задача $task отключена"
        }
        
        Write-Log "Отключение ненужных служб завершено"
    }
    catch {
        Write-Log "Ошибка при отключении ненужных служб: $_"
    }
}

# Функция для оптимизации запуска системы
function Optimize-Startup {
    try {
        Write-Log "Оптимизация автозагрузки..."
        
        # Резервное копирование ключей автозагрузки
        Backup-Settings -Name "Startup_HKCU" -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
        Backup-Settings -Name "Startup_HKLM" -Path "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run"
        
        # Отключение лишних программ из автозагрузки
        $startupItems = @(
            "OneDrive",
            "Teams",
            "CCleaner",
            "SunJavaUpdateSched",
            "QuickTime"
        )
        
        foreach ($item in $startupItems) {
            # Отключаем в HKCU
            if (Get-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name $item -ErrorAction SilentlyContinue) {
                Remove-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name $item -Force -ErrorAction SilentlyContinue
                Write-Log "Программа $item удалена из автозагрузки пользователя"
            }
            
            # Отключаем в HKLM
            if (Get-ItemProperty -Path "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run" -Name $item -ErrorAction SilentlyContinue) {
                Remove-ItemProperty -Path "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run" -Name $item -Force -ErrorAction SilentlyContinue
                Write-Log "Программа $item удалена из автозагрузки системы"
            }
        }
        
        # Оптимизация времени загрузки служб
        Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control" -Name "ServicesPipeTimeout" -Value 60000 -Type DWord -Force -ErrorAction SilentlyContinue
        
        # Увеличение скорости завершения неотвечающих приложений
        Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "AutoEndTasks" -Value 1 -Type String -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "HungAppTimeout" -Value 5000 -Type String -Force -ErrorAction SilentlyContinue
        Set-ItemProperty -Path "HKCU:\Control Panel\Desktop" -Name "WaitToKillAppTimeout" -Value 4000 -Type String -Force -ErrorAction SilentlyContinue
        
        Write-Log "Оптимизация автозагрузки завершена"
    }
    catch {
        Write-Log "Ошибка при оптимизации автозагрузки: $_"
    }
}

# Проверка прав администратора
$isAdmin = [bool]([System.Security.Principal.WindowsIdentity]::GetCurrent().Groups -match "S-1-5-32-544")
if (-not $isAdmin) {
    Write-Host "Для работы скрипта необходимы права администратора. Запустите скрипт от имени администратора." -ForegroundColor Red
    Write-Log "Скрипт завершен из-за отсутствия прав администратора"
    exit 1
}

# Основная часть скрипта
try {
    Write-Host "======================================================" -ForegroundColor Green
    Write-Host "             ОПТИМИЗАЦИЯ WINDOWS                      " -ForegroundColor Green
    Write-Host "======================================================" -ForegroundColor Green
    
    Write-Log "Запуск скрипта оптимизации Windows"
    
    # Получение информации о системе
    $osInfo = Get-CimInstance -ClassName Win32_OperatingSystem
    $computerInfo = Get-CimInstance -ClassName Win32_ComputerSystem
    
    Write-Log "Информация о системе: $($osInfo.Caption), $($computerInfo.Manufacturer) $($computerInfo.Model)"
    
    # Создание точки восстановления системы
    Enable-ComputerRestore -Drive "C:\" -ErrorAction SilentlyContinue
    Checkpoint-Computer -Description "WindowsOptimizer - Перед оптимизацией" -RestorePointType "MODIFY_SETTINGS" -ErrorAction SilentlyContinue
    Write-Log "Создана точка восстановления системы"
    
    # Выполнение оптимизаций
    Optimize-Performance
    Clean-Temp-Files
    Disable-Unnecessary-Services
    Optimize-Startup
    
    # Оптимизация сетевых параметров
    netsh interface tcp set global autotuninglevel=normal
    netsh interface tcp set global chimney=enabled
    netsh interface tcp set global ecncapability=enabled
    Write-Log "Выполнена оптимизация сетевых параметров"
    
    # Дефрагментация диска
    if ((Get-PhysicalDisk | Where-Object MediaType -eq HDD) -ne $null) {
        Write-Log "Запуск дефрагментации HDD..."
        Optimize-Volume -DriveLetter C -Defrag -Verbose -ErrorAction SilentlyContinue
    } else {
        Write-Log "Обнаружен SSD - дефрагментация пропущена, запуск TRIM..."
        Optimize-Volume -DriveLetter C -ReTrim -Verbose -ErrorAction SilentlyContinue
    }
    
    # Обновление Windows Defender
    if (Get-Command Update-MpSignature -ErrorAction SilentlyContinue) {
        Write-Log "Обновление сигнатур Windows Defender..."
        Update-MpSignature -ErrorAction SilentlyContinue
        Write-Log "Сигнатуры Windows Defender обновлены"
    }
    
    # Завершение работы
    Write-Host "======================================================" -ForegroundColor Green
    Write-Host "      ОПТИМИЗАЦИЯ WINDOWS УСПЕШНО ЗАВЕРШЕНА          " -ForegroundColor Green
    Write-Host "======================================================" -ForegroundColor Green
    
    Write-Host "Выполненные оптимизации:" -ForegroundColor Yellow
    Write-Host " - Оптимизация производительности (графика, анимации, Superfetch)"
    Write-Host " - Отключение ненужных служб"
    Write-Host " - Очистка временных файлов и оптимизация диска"
    Write-Host " - Оптимизация автозагрузки"
    Write-Host " - Настройка сетевых параметров"
    
    Write-Log "Скрипт оптимизации Windows успешно завершен"
}
catch {
    Write-Host "======================================================" -ForegroundColor Red
    Write-Host "       ПРОИЗОШЛА ОШИБКА ПРИ ВЫПОЛНЕНИИ СКРИПТА       " -ForegroundColor Red
    Write-Host "======================================================" -ForegroundColor Red
    
    Write-Log "Критическая ошибка при выполнении скрипта: $_"
    
    Write-Host "Подробная информация об ошибке сохранена в лог-файле" -ForegroundColor Red
}

Write-Host "`nНажмите любую клавишу для завершения..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 