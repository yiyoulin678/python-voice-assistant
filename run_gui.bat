@echo off
chcp 65001 >nul
cd /d "%~dp0"
for /f "delims=" %%i in ('python -c "import PyQt5, pathlib; print(pathlib.Path(PyQt5.__file__).parent / 'Qt5' / 'plugins' / 'platforms')"') do set "QT_QPA_PLATFORM_PLUGIN_PATH=%%i"
for /f "delims=" %%i in ('python -c "import PyQt5, pathlib; print(pathlib.Path(PyQt5.__file__).parent / 'Qt5' / 'bin')"') do set "PATH=%%i;%PATH%"
set QT_QPA_PLATFORM=windows
python main.py
if errorlevel 1 pause
