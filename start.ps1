# Mutsuki launcher (UTF-8 safe, handles paths with + or spaces)
$ErrorActionPreference = 'Stop'

$PrjRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$PrjRoot = [System.IO.Path]::GetFullPath($PrjRoot)

$env:MUTSUKI_PRJ_ROOT = $PrjRoot
$env:SAKURA_PRJ_ROOT = $PrjRoot

if ($PrjRoot -match '[^\x20-\x7E]') {
    Write-Host '[ERROR] Project path must be ASCII-only (PySide6 requirement).'
    Write-Host "        Current: $PrjRoot"
    Write-Host '        Example: D:\mutsuki'
    Read-Host 'Press Enter to exit'
    exit 1
}

$pythonw = Join-Path $PrjRoot 'runtime\pythonw.exe'
$python = Join-Path $PrjRoot 'runtime\python.exe'
if (Test-Path -LiteralPath $pythonw) {
    $PythonExe = $pythonw
} elseif (Test-Path -LiteralPath $python) {
    $PythonExe = $python
} else {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) {
        Write-Host '[ERROR] Python not found. Run install.bat first.'
        Read-Host 'Press Enter to exit'
        exit 1
    }
    $PythonExe = $cmd.Source
}

$hfHome = Join-Path $PrjRoot 'runtime\hf-cache'
New-Item -ItemType Directory -Force -Path $hfHome | Out-Null
$env:HF_HOME = $hfHome
$env:SENTENCE_TRANSFORMERS_HOME = $hfHome

Set-Location -LiteralPath $PrjRoot
& $PythonExe (Join-Path $PrjRoot 'main.py')
$code = $LASTEXITCODE
if ($code -ne 0) {
    Write-Host "[ERROR] Mutsuki exited with code $code"
    Read-Host 'Press Enter to exit'
}
exit $code
