.SYNOPSIS
  Скрипт для оптимизации производительности Windows
.DESCRIPTION
  Выполняет различные настройки для повышения быстродействия системы,
  отключает ненужные службы и компоненты, очищает временные файлы.
  Создан с учетом характеристик системы на основе предоставленного скриншота.
.PARAMETER BackupPath
  Путь для сохранения бэкапа параметров
.EXAMPLE
  .\WindowsOptimizer.ps1 -BackupPath C:\Backup
#>

param (
  [string]$BackupPath = "C:\OptimizeBackup"
)

# Функция для бэкапа параметров реестра
function Backup-RegistrySettings {
  param([string]$RegPath, [string]$SaveName)
  
  if (!(Test-Path $BackupPath)) {
    New-Item -ItemType Directory -Path $BackupPath | Out-Null
  }

  $dateTime = Get-Date -Format "dd-MM-yy_HH-mm"
  $backupFile = "$BackupPath\$SaveName $dateTime.reg"
  
  Write-Host "Экспорт $RegPath в $backupFile" -ForegroundColor Green
  try {
    reg export $RegPath $backupFile | Out-Null
  }
  catch {
    Write-Warning "Ошибка экспорта $RegPath"
  }
}

# Проверка прав администратора
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (!($isAdmin)) {
  Write-Host "Ошибка: скрипт должен запускаться от имени администратора" -ForegroundColor Red
  Exit
}

# Лог файл 
$logFile = "C:\WindowsOptimizer.log"
"Windows optimization started at $(Get-Date)`n" | Out-File $logFile -Append

# Функция оптимизации производительности
function Optimize-Performance {
  # Оптимизация графики и анимаций
  try {
    Backup-RegistrySettings "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" "VisualEffectsBackup"

    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Name "VisualFXSetting" -Type DWord -Value 2  
    New-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Name "ListviewAlphaSelect" -PropertyType DWord -Value 0 -Force
    New-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Name "ListviewShadow" -PropertyType DWord -Value 0 -Force
    New-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects" -Name "TaskbarAnimations" -PropertyType DWord -Value 0 -Force
  }
  catch {
    Write-Warning "Ошибка при оптимизации графики"
    $_ | Out-File $logFile -Append
  }

  # Отключение Superfetch
  try {
    Backup-RegistrySettings "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters" "SuperfetchBackup"

    Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters" -Name "EnableSuperfetch" -Type DWord -Value 0
    Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management\PrefetchParameters" -Name "EnablePrefetcher" -Type DWord -Value 0
  }
  catch {
    Write-Warning "Ошибка отключения Superfetch"
    $_ | Out-File $logFile -Append
  }

  # Оптимизация файла подкачки
  try {
    Backup-RegistrySettings "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" "PagefileBackup"
    
    $mem = Get-WmiObject -Class Win32_OperatingSystem | Select-Object TotalVisibleMemorySize 
    $pageSize = 4096 + [Math]::Round($mem.TotalVisibleMemorySize/1MB) 
    $pageSize = [Math]::Min($pageSize, 32768)

    Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\Session Manager\Memory Management" -Name "PagingFiles" -Type MultiString -Value "C:\pagefile.sys $pageSize $pageSize"
  }
  catch {
    Write-Warning "Ошибка оптимизации файла подкачки"
    $_ | Out-File $logFile -Append
  }

  Write-Host "Оптимизация производительности выполнена" -ForegroundColor Green
}

# Функция отключения ненужных служб
function Disable-Unused-Services {
  $services = @(
    "XblAuthManager"            # Xbox Live Auth Manager
    "XblGameSave"               # Xbox Live Game Save 
    "XboxNetApiSvc"             # Xbox Live Networking Service
    "XboxGipSvc"                # Служба инфраструктуры GRID Xbox
    "diagnosticshub.standardcollector.service"    # Служба регистрации событий для диагностики Microsoft (для сбора телеметрии)
    "DiagTrack"                 # Диагностика Microsoft (сбор данных о работе ОС и ПО)
    "DcpSvc"                    # DataCollectionPublishingService (сбор данных об использовании)
    "dmwappushservice"          # Служба маршрутизатора push-сообщений WAP
    "lfsvc"                     # Служба геолокации    
    "FDResPub"                  # Хост-поставщик функции обнаружения
    "BcastDVRUserService_7cc0a" # Служба пользователя для сеансов GameDVR и вещания
    "SysMain"                   # Superfetch
  )

  foreach ($service in $services) {
    $servObj = Get-Service -Name $service -ErrorAction SilentlyContinue
    if ($servObj -and $servObj.StartType -ne "Disabled") {
      try {
        Set-Service $service -StartupType Disabled
        Stop-Service $service -Force -ErrorAction SilentlyContinue
        Write-Host "Служба $service отключена" -ForegroundColor Green  
      }
      catch {
        Write-Warning "Ошибка отключения службы $service"
        $_ | Out-File $logFile -Append
      }
    }
  }
}

# Функция очистки временных файлов
function Clean-Temp-Files {
  $tempFolders = @(
    "C:\Windows\Temp\*"
    "C:\Windows\Prefetch\*"
    "C:\Documents and Settings\*\Local Settings\temp\*"
    "C:\Users\*\Appdata\Local\Temp\*"
  )

  foreach ($folder in $tempFolders) {
    try {
      Remove-Item $folder -Recurse -Force -ErrorAction SilentlyContinue
    }
    catch {
      $_ | Out-File $logFile -Append
    }
  }

  Write-Host "Временные файлы очищены" -ForegroundColor Green
}

# Оптимизация производительности
Optimize-Performance

# Отключение ненужных служб
Disable-Unused-Services

# Очистка временных файлов
Clean-Temp-Files

# Дефрагментация диска
try {
  Write-Host "Запуск дефрагментации диска C:" -ForegroundColor Yellow
  Optimize-Volume -DriveLetter C -Verbose 
}
catch {
  Write-Warning "Ошибка дефрагментации диска"
  $_ | Out-File $logFile -Append
}

# Вывод информации 
Write-Host "`nВыполненные оптимизации:" -ForegroundColor Cyan
Write-Host " - Оптимизация производительности (графика, анимации, Superfetch)"
Write-Host " - Отключение ненужных служб"
Write-Host " - Очистка временных файлов и дефрагментация диска"
Write-Host "`nЛог сохранен в файле $logFile"

"Windows optimization finished at $(Get-Date)" | Out-File $logFile -Append
