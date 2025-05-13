# Скрипт запуска бота оптимизации Windows в PowerShell
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -Path $ScriptPath

Write-Host "Запуск бота оптимизации Windows..." -ForegroundColor Green
Write-Host "========================================"

try {
    python optimization_bot.py
}
catch {
    Write-Host "Ошибка при запуске бота: $_" -ForegroundColor Red
}
finally {
    Write-Host "========================================"
    Write-Host "Бот остановлен." -ForegroundColor Yellow
    Write-Host "Нажмите любую клавишу для выхода..." -ForegroundColor Cyan
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} 