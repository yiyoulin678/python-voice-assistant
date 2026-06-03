@echo off

setlocal

set "ROOT=%~dp0.."

set "GS_DIR="



for /d %%D in ("%ROOT%\data\tts_bundles\installed\*") do (

  if exist "%%D\api_v2.py" (

    set "GS_DIR=%%D"

    goto :found

  )

  for /d %%I in ("%%D\*") do (

    if exist "%%I\api_v2.py" (

      set "GS_DIR=%%I"

      goto :found

    )

  )

)



if exist "%ROOT%\..\..\Game\GPT-SoVITS\GPT-SoVITS-v2pro-20250604\api_v2.py" (

  set "GS_DIR=%ROOT%\..\..\Game\GPT-SoVITS\GPT-SoVITS-v2pro-20250604"

)



:found

if not defined GS_DIR (

  echo 未找到 GPT-SoVITS 整包（需要 api_v2.py + runtime\python.exe）。

  echo 权重在 data\models\GPT_SoVITS，但 API 服务需整合包：

  echo   - 在 Mutsuki 设置里下载 TTS 整合包到 data\tts_bundles\installed

  echo   - 或把整包解压到上述目录，或修改本 bat 中的路径。

  pause

  exit /b 1

)



cd /d "%GS_DIR%"

echo 使用目录: %GS_DIR%

echo 正在启动 GPT-SoVITS API（端口 9880），首次加载模型可能需 1～2 分钟…

start "GPT-SoVITS-API" "%GS_DIR%\runtime\python.exe" api_v2.py

echo 已在新窗口启动。确认无报错后，再运行 Mutsuki 桌宠。

pause

