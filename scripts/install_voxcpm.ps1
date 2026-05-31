# VoxCPM 安装（在 VoiceAssistant 目录执行）
# 用法: powershell -ExecutionPolicy Bypass -File scripts/install_voxcpm.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot + "\.."

$repo = Join-Path (Get-Location) "third_party\VoxCPM"
if (-not (Test-Path $repo)) {
    Write-Host "未找到 third_party/VoxCPM，正在克隆..."
    git clone --depth 1 https://github.com/OpenBMB/VoxCPM.git $repo
    if ($LASTEXITCODE -ne 0) {
        Write-Host "GitHub 直连失败，尝试镜像..."
        git clone --depth 1 https://gitclone.com/github.com/OpenBMB/VoxCPM.git $repo
    }
}

Write-Host "从本地源码安装 voxcpm..."
pip install -e $repo

Write-Host "完成。自检: python scripts/check_voxcpm.py"
