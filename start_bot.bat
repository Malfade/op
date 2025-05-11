@echo off
chcp 65001 >nul
title Запуск бота оптимизации Windows

echo Запуск бота оптимизации Windows...

REM Переходим в директорию скрипта
cd /d "%~dp0"

REM Проверяем наличие файла бота
if not exist "optimization_bot.py" (
    echo Ошибка: файл optimization_bot.py не найден
    pause
    exit /b 1
)

REM Запускаем бота
echo Запуск бота...
python optimization_bot.py

pause 