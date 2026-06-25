# IBM Disaster Management Tool

Backup, schedule, compress, encrypt, and ship database backups to multiple destinations.

## Install

**Linux / macOS**
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/AnAverageBeing/IBM-Disaster-Management-Tool/master/installer/install.sh)
```

**Windows (PowerShell)**
```powershell
iwr -useb https://raw.githubusercontent.com/AnAverageBeing/IBM-Disaster-Management-Tool/master/installer/install.ps1 | iex
```

Installs dependencies, clones the repo, creates a launcher, and opens the GUI.

### Options

| Flag | What it does |
|------|-------------|
| `--no-launch` | Install only, skip GUI |
| `--no-desktop` | No desktop shortcut |
| `--service` | Register systemd user service (Linux) |

## Features

- **8 engines** — MySQL, MariaDB, PostgreSQL, MongoDB, Redis, SQLite, MSSQL, Oracle
- **Compression** — Zstandard → tar.xz → 7z
- **Encryption** — AES-256-GCM
- **Scheduling** — interval (10m–monthly) or cron via APScheduler
- **Destinations** — local dir, Discord (auto-split at 25MB), GitHub (auto-creates `backups` repo)
- **Alerts** — Console, Discord, Email, Slack, Telegram
- **Verification** — SHA-256 checksums on every backup
- **Session management** — save, edit, delete, run, upload to GitHub
- **Background service** — survives reboot

## Backup layout

```
backups/databases/{type}/{SessionName_IP}/
└── YYYY-MM-DD_HH-MM-SS_UTC/
    ├── database.sql.zst
    ├── database.sql.zst.enc       # if encrypted
    ├── metadata.json
    ├── manifest.json
    ├── checksums.sha256
    └── logs.txt
```

## Headless

```bash
ibm-dmt --headless --config config.json
```
