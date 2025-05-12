# Encoding: UTF-8
# PowerShell script to run the optimization script with proper rights
$OutputEncoding = [System.Text.Encoding]::UTF8

# Путь к лог-файлу
$LogPath = "$env:TEMP\WindowsOptimizer_Log.txt"

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

# Check administrator rights
function Test-Administrator {
    $user = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($user)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Функция отображения прогресса
function Show-Progress {
    param (
        [string]$Activity,
        [int]$PercentComplete
    )
    
    Write-Progress -Activity $Activity -PercentComplete $PercentComplete
    Write-Host "[$($Activity)]: $PercentComplete%" -ForegroundColor Cyan
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
        & .\WindowsOptimizer.ps1
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
