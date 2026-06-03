# Mutsuki dependency installer (UTF-8 safe)
$ErrorActionPreference = 'Stop'

$PrjRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$PrjRoot = [System.IO.Path]::GetFullPath($PrjRoot)

$env:MUTSUKI_PRJ_ROOT = $PrjRoot
$env:SAKURA_PRJ_ROOT = $PrjRoot

Write-Host '========================================'
Write-Host '  Mutsuki dependency install'
Write-Host '========================================'
Write-Host ''

if ($PrjRoot -match '[^\x20-\x7E]') {
    Write-Host '[ERROR] Project path must be ASCII-only (PySide6 requirement).'
    Write-Host "        Current: $PrjRoot"
    Read-Host 'Press Enter to exit'
    exit 1
}

$python = Join-Path $PrjRoot 'runtime\python.exe'
if (Test-Path -LiteralPath $python) {
    $PythonExe = $python
    Write-Host '[OK] Using runtime\python.exe'
} else {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Write-Host '[ERROR] Python not found. Install Python or use full release package.'
        Read-Host 'Press Enter to exit'
        exit 1
    }
    $PythonExe = $cmd.Source
    Write-Host '[OK] Using system Python'
}

$requirements = Join-Path $PrjRoot 'requirements.txt'
if (-not (Test-Path -LiteralPath $requirements)) {
    Write-Host '[ERROR] requirements.txt not found'
    Read-Host 'Press Enter to exit'
    exit 1
}

Write-Host ''
Write-Host '[1/2] Installing Python packages...'
Write-Host ''

& $PythonExe -m pip install -r $requirements `
    -i https://mirrors.aliyun.com/pypi/simple `
    --extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple `
    --extra-index-url https://pypi.org/simple
if ($LASTEXITCODE -ne 0) {
    Write-Host ''
    Write-Host '[ERROR] pip install failed. Check network and retry.'
    Read-Host 'Press Enter to exit'
    exit 1
}

Write-Host ''
Write-Host '[2/2] Verifying PySide6 + Playwright...'
& $PythonExe -c "import PySide6; import playwright; print('[OK] PySide6 + Playwright ready')"
if ($LASTEXITCODE -ne 0) {
    Write-Host '[WARN] Verification failed; see output above.'
}

Write-Host ''
Write-Host '========================================'
Write-Host '  Done. Double-click start.bat to run'
Write-Host '========================================'
Read-Host 'Press Enter to exit'
