@echo off
setlocal EnableExtensions
cd /d "%~dp0"
rem Delegate to VBS so double-clicking does not leave a CMD window open.
wscript //nologo "%~dp0start.vbs"
exit /b 0
