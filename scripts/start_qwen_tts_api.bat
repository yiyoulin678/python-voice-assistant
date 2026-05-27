@echo off
chcp 65001 >nul
set "ROOT=D:\Game\Qwen_TTS\qwen_tts_webui-licyk-20260525-nightly\qwen_tts_webui-licyk-20260525"
set "PY=%ROOT%\python\python.exe"
set "MODELSCOPE_CACHE=%ROOT%\cache\modelscope"
set "PYTHONPATH=%ROOT%\core"
cd /d "%ROOT%"
echo 启动 Qwen TTS API（若7860占用会自动换端口，请以控制台/浏览器为准）
"%PY%" -m qwen_tts_webui --api --nowebui --no-inbrowser --skip-check --server-port 7861
pause
