@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set "OLLAMA_ROOT=%CD%\third_party\ollama"
set "OLLAMA_HOME=%OLLAMA_ROOT%\data"
set "OLLAMA_MODELS=%OLLAMA_ROOT%\models"
set "PATH=%OLLAMA_ROOT%\bin;%PATH%"

if not exist "%OLLAMA_ROOT%\bin\ollama.exe" (
    echo [错误] 未找到 ollama.exe，请先运行: powershell -File scripts\setup_ollama.ps1
    pause
    exit /b 1
)

mkdir "%OLLAMA_HOME%" 2>nul
mkdir "%OLLAMA_MODELS%" 2>nul

echo Ollama 目录: %OLLAMA_ROOT%
echo 模型目录: %OLLAMA_MODELS%
echo 启动服务 http://127.0.0.1:11434 ...

start "Ollama" /min "%OLLAMA_ROOT%\bin\ollama.exe" serve
timeout /t 3 /nobreak >nul
"%OLLAMA_ROOT%\bin\ollama.exe" list
