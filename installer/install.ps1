param(
    [string]$InstallDir = "$env:USERPROFILE\.ibm-dmt",
    [switch]$NoDesktop,
    [switch]$Service,
    [switch]$NoLaunch
)

$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "IBM-DMT Installer"

function Info  { Write-Host "[INFO]  $args" -ForegroundColor Green }
function Warn  { Write-Host "[WARN]  $args" -ForegroundColor Yellow }
function Err   { Write-Host "[ERR]   $args" -ForegroundColor Red }
function Step  { Write-Host "`n-- $args --" -ForegroundColor White }

$venvPath    = Join-Path $InstallDir "venv"
$repoDir     = Join-Path $InstallDir "repo"
$launcherPath = Join-Path $InstallDir "ibm-dmt.bat"

Write-Host "IBM Disaster Management Tool Installer" -ForegroundColor Green

# Check Python
Step "Python"
try {
    $pyVer = python --version 2>&1
    Info "Found $pyVer"
} catch {
    Err "Python 3.10+ required. Download from https://python.org"
    exit 1
}

# Create venv
Step "Virtual environment"
python -m venv $venvPath
$pip = Join-Path $venvPath "Scripts\pip"
& $pip install --quiet --upgrade pip setuptools wheel
Info "Virtual environment ready"

# Core packages
Step "Core packages"
$core = @(
    "pyqt6","pyzstd","cryptography","requests","apscheduler",
    "pygithub","psutil","pydantic","platformdirs"
)
& $pip install --quiet $core 2>&1 | Out-Null
Info "Core installed"

# Database drivers (optional — each can fail independently)
Step "Database drivers"
$dbDrivers = @(
    "pymongo","redis","mysql-connector-python","psycopg2-binary","pymssql"
)
foreach ($pkg in $dbDrivers) {
    try {
        & $pip install --quiet $pkg 2>&1 | Out-Null
        Info "  $pkg OK"
    } catch {
        Warn "  $pkg skipped"
    }
}
# cx-Oracle — only attempt if Oracle client is likely installed
$oracleHome = [Environment]::GetEnvironmentVariable("ORACLE_HOME")
if ($oracleHome -and (Test-Path $oracleHome)) {
    try { & $pip install --quiet cx-oracle 2>&1 | Out-Null; Info "  cx-oracle OK" }
    catch { Warn "  cx-oracle skipped" }
} else {
    Warn "  cx-oracle skipped (Oracle Instant Client not detected)"
}

# Clone repo
Step "Repository"
if (Test-Path $repoDir) {
    try { Set-Location $repoDir; git pull --ff-only 2>&1 | Out-Null; Info "Updated" }
    catch { Warn "Update failed" }
} else {
    try {
        git clone --depth 1 "https://github.com/AnAverageBeing/IBM-Disaster-Management-Tool.git" $repoDir 2>&1 | Out-Null
        Info "Cloned"
    } catch {
        Err "Clone failed: $_"; exit 1
    }
}
try {
    & $pip install --quiet -e $repoDir 2>&1 | Out-Null
} catch { Warn "Editable install skipped" }

# Launcher
Step "Launcher"
$batContent = @"
@echo off
call "$venvPath\Scripts\activate"
cd /d "$repoDir" 2>nul
python -m ibm_dmt.main %*
"@
$batContent | Out-File -FilePath $launcherPath -Encoding ASCII -Force

$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$InstallDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$userPath;$InstallDir", "User")
}
Info "Launcher: $launcherPath"

# Desktop shortcut
if (-not $NoDesktop) {
    try {
        $wshell = New-Object -ComObject WScript.Shell
        $shortcut = $wshell.CreateShortcut("$env:USERPROFILE\Desktop\IBM-DMT.lnk")
        $shortcut.TargetPath = $launcherPath
        $shortcut.WorkingDirectory = $repoDir
        $shortcut.Description = "IBM Disaster Management Tool"
        $shortcut.Save()
        Info "Desktop shortcut created"
    } catch { Warn "Desktop shortcut skipped" }
}

Write-Host "`nIBM-DMT Installation complete" -ForegroundColor Green

if (-not $NoLaunch) {
    Write-Host "Launching GUI..." -ForegroundColor Yellow
    & $venvPath\Scripts\python.exe -m ibm_dmt.main
}
