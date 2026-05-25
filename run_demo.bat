@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo 当前目录: %CD%
echo.
python -m ai.demo_cli %*
if errorlevel 1 pause
