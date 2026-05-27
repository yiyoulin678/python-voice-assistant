# 将 Ollama 安装到项目 third_party/ollama（便携版 CLI）
# 用法: powershell -ExecutionPolicy Bypass -File scripts/setup_ollama.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$OllamaRoot = Join-Path $Root "third_party\ollama"
$Bin = Join-Path $OllamaRoot "bin"
$Models = Join-Path $OllamaRoot "models"
$Data = Join-Path $OllamaRoot "data"
$Zip = Join-Path $OllamaRoot "ollama-windows-amd64.zip"
$Url = "https://github.com/ollama/ollama/releases/download/v0.24.0/ollama-windows-amd64.zip"
$Model = "qwen2.5:3b"

New-Item -ItemType Directory -Force -Path $Bin, $Models, $Data | Out-Null

if (-not (Test-Path (Join-Path $Bin "ollama.exe"))) {
    if (-not (Test-Path $Zip) -or ((Get-Item $Zip).Length -lt 1GB)) {
        Write-Host "下载 Ollama (~2GB)，请耐心等待..."
        python -c @"
import urllib.request, pathlib
url = '$Url'
out = pathlib.Path(r'$Zip')
urllib.request.urlretrieve(url, out)
print('下载完成', out.stat().st_size)
"@
    }
    Write-Host "解压到 $Bin ..."
    python -c @"
import zipfile, pathlib
zipfile.ZipFile(r'$Zip').extractall(r'$Bin')
print('解压完成')
"@
}

$env:OLLAMA_HOME = $Data
$env:OLLAMA_MODELS = $Models
$OllamaExe = Join-Path $Bin "ollama.exe"

# 若已有服务则直接拉模型
$running = $false
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -UseBasicParsing
    $running = $r.StatusCode -eq 200
} catch {}

if (-not $running) {
    Write-Host "启动 Ollama 服务..."
    Start-Process -FilePath $OllamaExe -ArgumentList "serve" -WindowStyle Minimized
    Start-Sleep -Seconds 4
}

Write-Host "拉取模型 $Model （约 2GB）..."
& $OllamaExe pull $Model

Write-Host ""
Write-Host "完成。模型在: $Models"
Write-Host "启动 GUI 前可执行: scripts\start_ollama.bat"
Write-Host "或直接用: run_gui.bat（会自动尝试启动 Ollama）"
