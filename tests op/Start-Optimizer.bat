@echo off
chcp 65001 >nul
title Windows Optimization

:: Check administrator rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo This script requires administrator privileges.
    echo Please run this file as administrator.
    pause
    exit /b 1
)

echo Starting Windows optimization script...
echo ==========================================

:: Run PowerShell script with execution policy bypass
powershell -ExecutionPolicy Bypass -NoProfile -File "WindowsOptimizer.ps1"

echo ==========================================
echo Optimization script completed.
pause
