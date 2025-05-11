# Скрипт для запуска бота оптимизации
Write-Host "Запуск бота оптимизации Windows..." -ForegroundColor Cyan

# Устанавливаем текущую директорию
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $scriptPath

# Проверяем наличие файла бота
if (-not (Test-Path "optimization_bot.py")) {
    Write-Host "Ошибка: файл optimization_bot.py не найден в директории $scriptPath" -ForegroundColor Red
    exit 1
}

# Запускаем бота
try {
    Write-Host "Запуск бота..." -ForegroundColor Green
    python optimization_bot.py
}
catch {
    Write-Host "Ошибка при запуске бота: $_" -ForegroundColor Red
    exit 1
} 