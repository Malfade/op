@echo off
chcp 65001 > nul
echo Запуск бота оптимизации Windows...

REM Проверка наличия Python
where python > nul 2>&1
if %errorlevel% neq 0 (
    echo Ошибка: Python не установлен или не добавлен в PATH
    echo Установите Python с сайта https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Проверка наличия файла бота
if not exist optimization_bot.py (
    echo Ошибка: Файл optimization_bot.py не найден
    pause
    exit /b 1
)

REM Запуск скрипта
echo Запуск бота...
python optimization_bot.py

REM Если скрипт завершился с ошибкой
if %errorlevel% neq 0 (
    echo Бот завершил работу с ошибкой
    pause
    exit /b %errorlevel%
)

echo Бот завершил работу
pause 