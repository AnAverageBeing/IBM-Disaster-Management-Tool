# IBM Disaster Management Tool

Backup, schedule, compress, encrypt, and ship database backups to multiple destinations.

## Install & Launch

**Linux**
```bash
bash <(curl -s https://raw.githubusercontent.com/AnAverageBeing/IBM-Disaster-Management-Tool/master/installer/install.sh)
```

**Windows (PowerShell)**
```powershell
iwr -useb https://raw.githubusercontent.com/AnAverageBeing/IBM-Disaster-Management-Tool/master/installer/install.ps1 | iex
```

The installer clones the repo, installs dependencies, and opens the GUI.

### Flags

| Flag | Effect |
|------|--------|
| `--no-launch` | Install only, don't open GUI |
| `--no-desktop` | Skip desktop shortcut |
| `--service` | Register systemd user service (Linux) |

## Features

- **8 database engines** — MySQL, MariaDB, PostgreSQL, MongoDB, Redis, SQLite, MSSQL, Oracle
- **Compression** — Zstandard (preferred) → tar.xz → 7z
- **Encryption** — AES-256-GCM
- **Scheduling** — interval (10m–monthly) or cron via APScheduler
- **Destinations** — local directory, Discord (auto-split 25MB), GitHub (auto-creates `backups` repo)
- **Alerts** — Console, Discord, Email, Slack, Telegram
- **Verification** — SHA-256 checksums on every backup
- **Session management** — save, edit, delete, run, upload to GitHub
- **Background service** — survives reboot via systemd

## Backup structure

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

## Headless mode

```bash
ibm-dmt --headless --config config.json
```

## Project structure

```
ibm_dmt/
├── core/          # plugin system, scheduler, alerts, credential store, config
├── gui/           # PyQt6 dark-theme interface
├── modules/
│   └── database_backup/
│       ├── connectors/   # database engines
│       ├── destinations/ # local, discord, github
│       ├── backup_engine.py
│       ├── compression.py
│       ├── encryption.py
│       └── gui.py
└── main.py        # entry point
```
