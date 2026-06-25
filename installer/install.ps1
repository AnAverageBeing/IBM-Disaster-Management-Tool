# IBM Disaster Management Tool Windows Installer
param(
    [string]$InstallDir = "$env:USERPROFILE\.ibm-dmt",
    [switch]$NoDesktop,
    [switch]$Service
)

$ErrorActionPreference = "Stop"
$Host.UI.RawUI.WindowTitle = "IBM-DMT Installer"

Write-Host "IBM Disaster Management Tool Installer" -ForegroundColor Green
Write-Host "========================================"
Write-Host ""

# Check Python
try {
    $pyVersion = python --version
    Write-Host "Found: $pyVersion" -ForegroundColor Green
} catch {
    Write-Host "Python 3.10+ is required. Download from https://python.org" -ForegroundColor Red
    exit 1
}

# Check pip
try {
    pip --version | Out-Null
} catch {
    python -m ensurepip
}

# Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Yellow
$venvPath = Join-Path $InstallDir "venv"
python -m venv $venvPath
$pip = Join-Path $venvPath "Scripts\pip"

# Install dependencies
Write-Host "Installing Python packages..." -ForegroundColor Yellow
& $pip install --upgrade pip
& $pip install pyqt6 pyzstd cryptography requests apscheduler pygithub psutil `
    pymongo redis mysql-connector-python psycopg2-binary pymssql `
    cx-oracle pydantic platformdirs

# Clone repo
Write-Host "Cloning repository..." -ForegroundColor Yellow
$repoDir = Join-Path $InstallDir "repo"
if (Test-Path $repoDir) {
    Set-Location $repoDir
    git pull
} else {
    git clone "https://github.com/AnAverageBeing/IBM-Disaster-Management-Tool.git" $repoDir
}

# Create launcher
$launcherPath = Join-Path $InstallDir "ibm-dmt.bat"
@"
@echo off
call "$venvPath\Scripts\activate"
python -m ibm_dmt.main %*
"@ | Out-File -FilePath $launcherPath -Encoding ASCII

# Add to PATH
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$InstallDir", "User")
    Write-Host "Added $InstallDir to PATH" -ForegroundColor Green
}

# Create shortcut
if (-not $NoDesktop) {
    $WshShell = New-Object -ComObject WScript.Shell
    $shortcut = $WshShell.CreateShortcut("$env:USERPROFILE\Desktop\IBM-DMT.lnk")
    $shortcut.TargetPath = $launcherPath
    $shortcut.WorkingDirectory = $repoDir
    $shortcut.Description = "IBM Disaster Management Tool"
    $shortcut.Save()
    Write-Host "Created desktop shortcut" -ForegroundColor Green
}

Write-Host ""
Write-Host "Installation Complete!" -ForegroundColor Green
Write-Host ""
Write-Host "  Run: ibm-dmt" -ForegroundColor White
Write-Host "  Config: $env:USERPROFILE\.config\ibm-dmt" -ForegroundColor White
