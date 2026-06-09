@echo off
setlocal EnableExtensions
cd /d "%~dp0"
rem Debug launcher: keeps CMD open and shows startup errors in the console.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
exit /b %ERRORLEVEL%
