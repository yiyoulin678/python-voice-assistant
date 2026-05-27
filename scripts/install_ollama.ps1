# 安装并拉取 Ollama + qwen2.5:3b（需管理员网络）
# 用法: powershell -ExecutionPolicy Bypass -File scripts/install_ollama.ps1

$ErrorActionPreference = "Stop"
$model = "qwen2.5:3b"

function Find-OllamaExe {
    $candidates = @(
        "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
        "$env:ProgramFiles\Ollama\ollama.exe"
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return $p }
    }
    $cmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    return $null
}

$ollama = Find-OllamaExe
if (-not $ollama) {
    Write-Host "未检测到 Ollama，尝试 winget 安装..."
    winget install -e --id Ollama.Ollama --accept-package-agreements --accept-source-agreements
    $ollama = Find-OllamaExe
    if (-not $ollama) {
        Write-Host "安装后仍未找到 ollama.exe。请手动从 https://ollama.com 安装，然后重新运行本脚本。"
        exit 1
    }
}

Write-Host "使用: $ollama"
Write-Host "拉取模型 $model （约 2GB，请耐心等待）..."
& $ollama pull $model
Write-Host "完成。请保持 Ollama 在后台运行，然后在 VoiceAssistant 目录执行:"
Write-Host "  python scripts/check_ollama.py"
