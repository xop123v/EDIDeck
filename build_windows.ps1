<#
PowerShell build script for EDIDeck
Usage:
  Open PowerShell, navigate to project root and run:
    .\build_windows.ps1
#>

param(
    [string]$venvPath = ".\venv",
    [string]$pythonExe = "$venvPath\Scripts\python.exe",
    [string]$pyinstallerExe = "$venvPath\Scripts\pyinstaller.exe",
    [string]$specFile = "edideck.spec",
    [string]$distName = "EDIDeck",
    [switch]$recreateVenv = $false,
    [string]$innoSetupCompiler = ""  # path to ISCC.exe if you want to build installer
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Ensure-Venv {
    param($venvPath, $recreate)

    if ((Test-Path $venvPath) -and (-not $recreate)) {
        Write-Host "Virtualenv exists at $venvPath"
        return
    }
    if ((Test-Path $venvPath) -and $recreate) {
        Write-Host "Removing existing venv..."
        Remove-Item -Recurse -Force $venvPath
    }
    Write-Host "Creating virtual environment..."
    python -m venv $venvPath
}

function Run {
    param($cmd)
    Write-Host ">> $cmd"
    & cmd /c $cmd
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $cmd"
    }
}

# 1. Create/ensure venv
Ensure-Venv -venvPath $venvPath -recreate:$recreateVenv

# 2. Activate venv (use python from venv directly)
if (-not (Test-Path $pythonExe)) {
    throw "Python executable not found at $pythonExe. Check venvPath or create venv manually."
}

# 3. Upgrade pip and install requirements + pyinstaller
Write-Host "Installing dependencies into venv..."
& $pythonExe -m pip install --upgrade pip setuptools wheel
& $pythonExe -m pip install -r requirements.txt
& $pythonExe -m pip install pyinstaller==5.9.0

# 4. Clean previous builds
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }
if (Test-Path "$distName.exe") { Remove-Item -Force "$distName.exe" -ErrorAction SilentlyContinue }

# 5. Run PyInstaller with spec if exists, else default command
if (Test-Path $specFile) {
    Write-Host "Running PyInstaller with spec: $specFile"
    & $pythonExe -m PyInstaller $specFile
} else {
    Write-Host "Running PyInstaller with default options"
    & $pythonExe -m PyInstaller --noconfirm --onefile --windowed --name $distName main.py
}

# 6. Post-build checks
if (Test-Path "dist\$distName.exe") {
    Write-Host "Build succeeded: dist\$distName.exe"
} else {
    throw "Build failed: dist\$distName.exe not found"
}

Write-Host "Done."
