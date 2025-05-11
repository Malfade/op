@echo off
title Windows Optimizer
color 0A
setlocal enabledelayedexpansion

:: Проверка прав администратора
NET FILE 1>NUL 2>NUL
if '%errorlevel%' == '0' ( goto START ) else ( goto ELEVATE )

:ELEVATE
echo ======================================================
echo              НЕОБХОДИМЫ ПРАВА АДМИНИСТРАТОРА
echo ======================================================
echo.
echo Для запуска оптимизации необходимы права администратора.
echo Сейчас будет выполнен запрос на повышение привилегий.
echo.
echo Нажмите любую клавишу для продолжения...
pause > nul

echo Запрос прав администратора...
powershell -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
exit /b

:START
echo ======================================================
echo              ЗАПУСК ОПТИМИЗАЦИИ WINDOWS
echo ======================================================
echo.
echo Сейчас будет запущен скрипт оптимизации Windows.
echo Процесс может занять некоторое время. Не закрывайте окно.
echo.

:: Проверка наличия файла скрипта
if not exist "%~dp0WindowsOptimizer.ps1" (
    color 0C
    echo ОШИБКА: Файл скрипта WindowsOptimizer.ps1 не найден в папке:
    echo %~dp0
    echo.
    echo Убедитесь, что файл скрипта находится в той же папке, что и данный bat-файл.
    echo.
    goto END
)

echo Запуск скрипта оптимизации...
echo.

:: Запуск PowerShell скрипта с обходом политики выполнения
powershell -ExecutionPolicy Bypass -File "%~dp0WindowsOptimizer.ps1"

:: Проверка результата выполнения скрипта
if %errorlevel% neq 0 (
    color 0C
    echo.
    echo ОШИБКА: Скрипт завершился с ошибкой (код %errorlevel%).
    echo Проверьте лог-файл в папке WindowsOptimizer_Logs для получения подробной информации.
    echo.
)

:END
echo.
echo Нажмите любую клавишу для завершения...
pause > nul
exit /b 