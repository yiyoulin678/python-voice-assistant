# CosyVoice 依赖（在 VoiceAssistant 目录执行）
# 用法: powershell -ExecutionPolicy Bypass -File scripts/install_cosyvoice_deps.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot + "\.."

Write-Host "安装 CosyVoice 运行依赖..."
pip install setuptools wheel Cython -q
pip install "torchaudio==2.8.0" -q
pip install conformer==0.3.2 HyperPyYAML==1.2.2 inflect==7.3.1 librosa==0.10.2 `
  onnxruntime==1.18.0 pyworld==0.3.4 soundfile==0.12.1 omegaconf==2.3.0 diffusers==0.29.0 `
  modelscope==1.20.0 hydra-core wget gdown pyworld==0.3.4
pip install "ruamel.yaml<0.18" -q

Write-Host "完成。请确认 third_party/CosyVoice 与 CosyVoice2-0.5B 模型已就绪。"
Write-Host "测试: python scripts/cosyvoice_speak.py --text 你好 --ref resources/voice_ref/reference.wav ..."
