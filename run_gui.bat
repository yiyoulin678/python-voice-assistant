@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "OLLAMA_ROOT=%CD%\third_party\ollama"
set "OLLAMA_HOME=%OLLAMA_ROOT%\data"
set "OLLAMA_MODELS=%OLLAMA_ROOT%\models"
set "PATH=%OLLAMA_ROOT%\bin;%PATH%"
if exist "%OLLAMA_ROOT%\bin\ollama.exe" (
    curl -s http://127.0.0.1:11434/api/tags >nul 2>&1
    if errorlevel 1 start "" /min "%OLLAMA_ROOT%\bin\ollama.exe" serve
)
for /f "delims=" %%i in ('python -c "import PyQt5, pathlib; print(pathlib.Path(PyQt5.__file__).parent / 'Qt5' / 'plugins' / 'platforms')"') do set "QT_QPA_PLATFORM_PLUGIN_PATH=%%i"
for /f "delims=" %%i in ('python -c "import PyQt5, pathlib; print(pathlib.Path(PyQt5.__file__).parent / 'Qt5' / 'bin')"') do set "PATH=%%i;%PATH%"
set QT_QPA_PLATFORM=windows
python main.py
if errorlevel 1 pause
