# Скрипт для запуска бота оптимизации Windows
Write-Host "Запуск бота оптимизации Windows..." -ForegroundColor Cyan

# Проверка наличия Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Используется: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Ошибка: Python не установлен или не добавлен в PATH" -ForegroundColor Red
    Write-Host "Установите Python с сайта https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Проверка наличия файла бота
if (-not (Test-Path -Path "optimization_bot.py")) {
    Write-Host "Ошибка: Файл optimization_bot.py не найден" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Запуск бота
try {
    Write-Host "Запуск бота..." -ForegroundColor Cyan
    python optimization_bot.py
} catch {
    Write-Host "Произошла ошибка при запуске бота: $_" -ForegroundColor Red
    Read-Host "Нажмите Enter для выхода"
    exit 1
}

# Если скрипт завершился успешно
if ($LASTEXITCODE -eq 0) {
    Write-Host "Бот завершил работу" -ForegroundColor Green
} else {
    Write-Host "Бот завершил работу с ошибкой (код $LASTEXITCODE)" -ForegroundColor Red
}

Read-Host "Нажмите Enter для выхода" 