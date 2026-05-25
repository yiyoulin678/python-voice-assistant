@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo === 推送到 github.com/Mut5uki/python-voice-assistant ===
echo.

git status
echo.
echo [1] 推送 main 分支...
git push -u origin main
if errorlevel 1 goto err

echo.
echo [2] 推送 feature 分支（用于 PR）...
git push -u origin feature/list-audio-devices
if errorlevel 1 goto err

echo.
echo 完成。请在浏览器打开创建 PR:
echo https://github.com/Mut5uki/python-voice-assistant/compare/main...feature/list-audio-devices?expand=1
goto end

:err
echo 推送失败，请检查网络、GitHub 登录（git credential）后重试。
pause
exit /b 1

:end
pause
