@echo off
chcp 65001 >nul
title Запуск бота оптимизации Windows

echo Запуск бота оптимизации Windows...
echo ========================================

cd %~dp0
python optimization_bot.py

echo ========================================
echo Бот остановлен.
pause 