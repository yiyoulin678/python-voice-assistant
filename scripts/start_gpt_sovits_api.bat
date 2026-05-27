@echo off
chcp 65001 >nul
set "GS_ROOT=D:\Game\GPT-SoVITS\GPT-SoVITS-v2pro-20250604"
if not exist "%GS_ROOT%\api_v2.py" (
    echo 未找到 api_v2.py: %GS_ROOT%
    pause
    exit /b 1
)
cd /d "%GS_ROOT%"
set "PY=python"
if exist "%GS_ROOT%\runtime\python.exe" set "PY=%GS_ROOT%\runtime\python.exe"
echo 启动 GPT-SoVITS API http://127.0.0.1:9880
echo 首次加载模型约 1-3 分钟，出现 Uvicorn running 即成功
start "GPT-SoVITS-API" "%PY%" api_v2.py -a 127.0.0.1 -p 9880
echo 已在独立窗口启动，可关闭本窗口
timeout /t 5
pause
