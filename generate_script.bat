@echo off
echo Generating PowerShell optimizer script...

echo # Windows_Optimizer.ps1 > WindowsOptimizer.ps1
echo # Script for Windows optimization >> WindowsOptimizer.ps1
echo. >> WindowsOptimizer.ps1
echo # Check for administrator rights >> WindowsOptimizer.ps1
echo if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { >> WindowsOptimizer.ps1
echo     Write-Warning 'Please run this script as Administrator!' >> WindowsOptimizer.ps1
echo     break >> WindowsOptimizer.ps1
echo } >> WindowsOptimizer.ps1
echo. >> WindowsOptimizer.ps1
echo # Error handling >> WindowsOptimizer.ps1
echo try { >> WindowsOptimizer.ps1
echo     # Clean temporary files >> WindowsOptimizer.ps1
echo     Write-Host 'Cleaning temporary files...' -ForegroundColor Green >> WindowsOptimizer.ps1
echo     Remove-Item -Path $env:TEMP\* -Force -Recurse -ErrorAction SilentlyContinue >> WindowsOptimizer.ps1
echo     Remove-Item -Path C:\Windows\Temp\* -Force -Recurse -ErrorAction SilentlyContinue >> WindowsOptimizer.ps1
echo. >> WindowsOptimizer.ps1
echo     # Performance optimization >> WindowsOptimizer.ps1
echo     Write-Host 'Optimizing performance...' -ForegroundColor Green >> WindowsOptimizer.ps1
echo     powercfg -setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c # High Performance >> WindowsOptimizer.ps1
echo. >> WindowsOptimizer.ps1
echo     # Disable unnecessary services >> WindowsOptimizer.ps1
echo     Write-Host 'Disabling unnecessary services...' -ForegroundColor Green >> WindowsOptimizer.ps1
echo     Stop-Service -Name DiagTrack -Force -ErrorAction SilentlyContinue >> WindowsOptimizer.ps1
echo     Set-Service -Name DiagTrack -StartupType Disabled -ErrorAction SilentlyContinue >> WindowsOptimizer.ps1
echo. >> WindowsOptimizer.ps1
echo     Write-Host 'Optimization completed!' -ForegroundColor Green >> WindowsOptimizer.ps1
echo } catch { >> WindowsOptimizer.ps1
echo     Write-Warning "An error occurred: $_" >> WindowsOptimizer.ps1
echo } >> WindowsOptimizer.ps1

echo Creating optimized batch script...
echo @echo off > WindowsOptimizer.bat
echo echo Windows Optimizer Batch Script >> WindowsOptimizer.bat
echo echo ============================== >> WindowsOptimizer.bat
echo. >> WindowsOptimizer.bat
echo :: Check for administrator rights >> WindowsOptimizer.bat
echo net session ^>nul 2^>^&1 >> WindowsOptimizer.bat
echo if %%errorLevel%% neq 0 ( >> WindowsOptimizer.bat
echo     echo Please run this script as Administrator! >> WindowsOptimizer.bat
echo     pause >> WindowsOptimizer.bat
echo     exit >> WindowsOptimizer.bat
echo ) >> WindowsOptimizer.bat
echo. >> WindowsOptimizer.bat
echo echo Cleaning temporary files... >> WindowsOptimizer.bat
echo del /f /s /q %%temp%%\*.* 2^>nul >> WindowsOptimizer.bat
echo del /f /s /q C:\Windows\Temp\*.* 2^>nul >> WindowsOptimizer.bat
echo. >> WindowsOptimizer.bat
echo echo Optimization completed! >> WindowsOptimizer.bat
echo pause >> WindowsOptimizer.bat

echo Scripts generated successfully.
echo To run:
echo - WindowsOptimizer.bat for batch script
echo - powershell -ExecutionPolicy Bypass -NoProfile -File "WindowsOptimizer.ps1" for PowerShell script

echo.
echo Starting Windows optimization script...
echo ==========================================
powershell -ExecutionPolicy Bypass -NoProfile -File "WindowsOptimizer.ps1"
echo ==========================================
echo Optimization script completed.
pause 