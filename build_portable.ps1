param(
    [string]$Python = "python",
    [string]$AppName = "OfflineFaceHackathon"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host "Building portable Windows package for $AppName"

if (-not (Test-Path "app.py")) {
    throw "Run this script from the project folder that contains app.py."
}

if (-not (Test-Path "models")) {
    Write-Warning "models/ folder is missing. The EXE will run in fallback mode, but ONNX model-size claims cannot be verified."
}

& $Python --version
if ($LASTEXITCODE -ne 0) {
    throw "Python was not found. Install Python 3.11+ for the build machine only. Judges/friends do not need Python after the EXE is built."
}

if (-not (Test-Path ".venv-build")) {
    & $Python -m venv .venv-build
}

$VenvPython = Join-Path $ProjectRoot ".venv-build\Scripts\python.exe"
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r requirements.txt pyinstaller

$addData = @()
if (Test-Path "database") {
    $addData += @("--add-data", "database;database")
}
if (Test-Path "models") {
    $addData += @("--add-data", "models;models")
}
if (Test-Path "docs") {
    $addData += @("--add-data", "docs;docs")
}
if (Test-Path "react-native-compat") {
    $addData += @("--add-data", "react-native-compat;react-native-compat")
}

& $VenvPython -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --name $AppName `
    --collect-all cv2 `
    --collect-all onnxruntime `
    @addData `
    app.py

$DistDir = Join-Path $ProjectRoot "dist\$AppName"
$RunBat = Join-Path $DistDir "RUN_DEMO.bat"
@"
@echo off
cd /d "%~dp0"
echo Offline Face Hackathon Demo
echo.
echo 1. Register: %~dp0$AppName.exe register --name "Your Name"
echo 2. Verify:   %~dp0$AppName.exe verify
echo 3. Profile:  %~dp0$AppName.exe profile
echo.
$AppName.exe profile
echo.
pause
"@ | Set-Content -Path $RunBat -Encoding ASCII

Write-Host ""
Write-Host "Portable package created:"
Write-Host $DistDir
Write-Host ""
Write-Host "Share the whole folder, not only the EXE."
