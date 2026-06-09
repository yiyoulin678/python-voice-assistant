# Mutsuki launcher (UTF-8 safe, handles paths with + or spaces)
param(
    [switch]$Hidden
)

$ErrorActionPreference = 'Stop'

$PrjRoot = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$PrjRoot = [System.IO.Path]::GetFullPath($PrjRoot)

$env:MUTSUKI_PRJ_ROOT = $PrjRoot
$env:SAKURA_PRJ_ROOT = $PrjRoot

function Write-StartupError {
    param(
        [string]$Message
    )
    $logDir = Join-Path $PrjRoot 'data\logs'
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $logPath = Join-Path $logDir 'startup.log'
    $line = "[{0}] {1}" -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'), $Message
    Add-Content -LiteralPath $logPath -Value $line -Encoding UTF8
    if ($Hidden) {
        Add-Type -AssemblyName PresentationFramework
        [System.Windows.MessageBox]::Show(
            "$Message`n`nSee log: $logPath",
            'Mutsuki Startup Error',
            'OK',
            'Error'
        ) | Out-Null
    } else {
        Write-Host $Message
        Read-Host 'Press Enter to exit'
    }
}

if ($PrjRoot -match '[^\x20-\x7E]') {
    Write-StartupError @"
[ERROR] Project path must be ASCII-only (PySide6 requirement).
        Current: $PrjRoot
        Example: D:\mutsuki
"@
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
        Write-StartupError '[ERROR] Python not found. Run install.bat first.'
        exit 1
    }
    $PythonExe = $cmd.Source
}

$hfHome = Join-Path $PrjRoot 'runtime\hf-cache'
New-Item -ItemType Directory -Force -Path $hfHome | Out-Null
$env:HF_HOME = $hfHome
$env:SENTENCE_TRANSFORMERS_HOME = $hfHome

Set-Location -LiteralPath $PrjRoot
$mainPy = Join-Path $PrjRoot 'main.py'
$process = Start-Process -FilePath $PythonExe -ArgumentList @($mainPy) -WorkingDirectory $PrjRoot -Wait -PassThru
$code = $process.ExitCode
if ($null -eq $code) {
    $code = 0
}
if ($code -ne 0) {
    Write-StartupError "[ERROR] Mutsuki exited with code $code"
}
exit $code
