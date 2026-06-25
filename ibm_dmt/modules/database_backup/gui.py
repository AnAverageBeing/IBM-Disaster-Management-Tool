import json
import threading
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QFormLayout, QLineEdit,
    QComboBox, QCheckBox, QTextEdit, QScrollArea,
    QGridLayout, QFrame, QListWidget, QListWidgetItem,
    QProgressBar, QMessageBox, QFileDialog, QTabWidget,
    QSplitter, QSizePolicy, QAbstractItemView,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont
from ibm_dmt.core.logger import Logger
from ibm_dmt.core.config import Config
from ibm_dmt.core.credential_store import CredentialStore
from ibm_dmt.core.scheduler import Scheduler
from ibm_dmt.modules.database_backup.backup_engine import BackupEngine
from ibm_dmt.modules.database_backup.destinations.github import GitHubDestination


class DatabaseBackupWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._log = Logger.get_logger()
        self._config = Config()
        self._creds = CredentialStore()
        self._engine = BackupEngine()
        self._scheduler = Scheduler()
        self._detected_servers = []
        self._selected_databases = []
        self._init_ui()
        self._detect_databases()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        header = QHBoxLayout()
        title = QLabel("Database Backup Management")
        title.setObjectName("titleLabel")
        header.addWidget(title)
        header.addStretch()

        run_now_btn = QPushButton("Run Backup Now")
        run_now_btn.setObjectName("primaryButton")
        run_now_btn.clicked.connect(self._run_backup)
        header.addWidget(run_now_btn)

        save_btn = QPushButton("Save Session")
        save_btn.clicked.connect(self._save_session)
        header.addWidget(save_btn)

        layout.addLayout(header)

        content = QSplitter(Qt.Orientation.Horizontal)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 8, 0)

        server_group = QGroupBox("Database Server")
        server_layout = QFormLayout(server_group)

        self._detect_btn = QPushButton("Detect Installed Servers")
        self._detect_btn.clicked.connect(self._detect_databases)
        server_layout.addRow(self._detect_btn)

        self._server_list = QListWidget()
        self._server_list.setMaximumHeight(120)
        self._server_list.itemClicked.connect(self._on_server_selected)
        server_layout.addWidget(self._server_list)

        self._db_type_combo = QComboBox()
        self._db_type_combo.addItems([
            "mysql", "mariadb", "postgresql", "mongodb",
            "redis", "sqlite", "mssql", "oracle",
        ])
        server_layout.addRow("DB Type:", self._db_type_combo)

        host_layout = QHBoxLayout()
        self._host_input = QLineEdit("localhost")
        host_layout.addWidget(self._host_input)
        self._port_input = QLineEdit()
        self._port_input.setPlaceholderText("Port")
        self._port_input.setFixedWidth(100)
        host_layout.addWidget(self._port_input)
        server_layout.addRow("Host:Port:", host_layout)

        self._user_input = QLineEdit()
        self._user_input.setPlaceholderText("Username")
        server_layout.addRow("User:", self._user_input)

        self._pass_input = QLineEdit()
        self._pass_input.setPlaceholderText("Password")
        self._pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        server_layout.addRow("Password:", self._pass_input)

        connect_btn = QPushButton("Connect")
        connect_btn.clicked.connect(self._connect_to_server)
        server_layout.addRow(connect_btn)

        left_layout.addWidget(server_group)

        db_group = QGroupBox("Databases")
        db_layout = QVBoxLayout(db_group)
        self._db_list = QListWidget()
        self._db_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        db_layout.addWidget(self._db_list)

        db_input_layout = QHBoxLayout()
        self._db_input = QLineEdit()
        self._db_input.setPlaceholderText("Or enter databases comma-separated")
        db_input_layout.addWidget(self._db_input)

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all_dbs)
        db_input_layout.addWidget(select_all_btn)

        db_layout.addLayout(db_input_layout)
        left_layout.addWidget(db_group)

        content.addWidget(left_panel)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 0, 0, 0)

        config_group = QGroupBox("Backup Configuration")
        config_layout = QFormLayout(config_group)

        self._session_name = QLineEdit()
        self._session_name.setPlaceholderText("MyProductionBackup")
        config_layout.addRow("Session Name:", self._session_name)

        self._backup_type = QComboBox()
        self._backup_type.addItems(["full", "incremental", "differential"])
        config_layout.addRow("Backup Type:", self._backup_type)

        self._schedule = QComboBox()
        self._schedule.addItems(["manual", "10m", "30m", "1h", "6h", "24h", "weekly", "monthly", "cron"])
        self._schedule.currentTextChanged.connect(self._on_schedule_changed)
        config_layout.addRow("Schedule:", self._schedule)

        self._cron_input = QLineEdit()
        self._cron_input.setPlaceholderText("0 */6 * * *")
        self._cron_input.setVisible(False)
        config_layout.addRow("Cron Expression:", self._cron_input)

        self._compress_cb = QCheckBox("Enable compression (Zstandard)")
        self._compress_cb.setChecked(True)
        config_layout.addRow("", self._compress_cb)

        self._encrypt_cb = QCheckBox("Enable AES-256 encryption")
        config_layout.addRow("", self._encrypt_cb)

        right_layout.addWidget(config_group)

        dest_group = QGroupBox("Backup Destinations")
        dest_layout = QVBoxLayout(dest_group)

        self._local_cb = QCheckBox("Local Directory")
        self._local_cb.setChecked(True)
        dest_layout.addWidget(self._local_cb)

        local_path_layout = QHBoxLayout()
        self._local_path = QLineEdit(str(Path.home() / "backups"))
        local_path_layout.addWidget(self._local_path)
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(lambda: self._local_path.setText(
            QFileDialog.getExistingDirectory(self, "Select Backup Directory")
        ))
        local_path_layout.addWidget(browse_btn)
        dest_layout.addLayout(local_path_layout)

        self._discord_cb = QCheckBox("Discord Webhook")
        dest_layout.addWidget(self._discord_cb)

        self._discord_input = QLineEdit()
        self._discord_input.setPlaceholderText("https://discord.com/api/webhooks/...")
        dest_layout.addWidget(self._discord_input)

        self._github_cb = QCheckBox("GitHub Repository (auto-create 'backups' repo)")
        dest_layout.addWidget(self._github_cb)

        gh_layout = QHBoxLayout()
        self._gh_repo = QLineEdit("backups")
        gh_layout.addWidget(QLabel("Repo:"))
        gh_layout.addWidget(self._gh_repo)
        dest_layout.addLayout(gh_layout)

        test_gh_btn = QPushButton("Test GitHub Connection")
        test_gh_btn.clicked.connect(self._test_github)
        dest_layout.addWidget(test_gh_btn)

        gh_upload_btn = QPushButton("Upload Existing Session to GitHub")
        gh_upload_btn.clicked.connect(self._upload_session_to_github)
        dest_layout.addWidget(gh_upload_btn)

        right_layout.addWidget(dest_group)

        alerts_group = QGroupBox("Alerts")
        alerts_layout = QGridLayout(alerts_group)

        self._alert_console = QCheckBox("Console")
        self._alert_console.setChecked(True)
        alerts_layout.addWidget(self._alert_console, 0, 0)

        self._alert_discord = QCheckBox("Discord")
        alerts_layout.addWidget(self._alert_discord, 0, 1)

        self._alert_email = QCheckBox("Email")
        alerts_layout.addWidget(self._alert_email, 0, 2)

        self._alert_slack = QCheckBox("Slack")
        alerts_layout.addWidget(self._alert_slack, 1, 0)

        self._alert_telegram = QCheckBox("Telegram")
        alerts_layout.addWidget(self._alert_telegram, 1, 1)

        right_layout.addWidget(alerts_group)

        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        self._progress_bar = QProgressBar()
        self._progress_bar.setVisible(False)
        progress_layout.addWidget(self._progress_bar)

        self._log_output = QTextEdit()
        self._log_output.setReadOnly(True)
        self._log_output.setMaximumHeight(120)
        self._log_output.setPlaceholderText("Backup logs will appear here...")
        progress_layout.addWidget(self._log_output)

        right_layout.addWidget(progress_group)

        content.addWidget(right_panel)
        layout.addWidget(content)

    def _on_schedule_changed(self, text: str):
        self._cron_input.setVisible(text == "cron")

    def _detect_databases(self):
        self._detect_btn.setEnabled(False)
        self._detect_btn.setText("Detecting...")
        self._server_list.clear()

        def detect():
            try:
                self._detected_servers = self._engine.detect_databases()
                self._log.info(f"Detection complete: {len(self._detected_servers)} server(s) found")
            except Exception as e:
                self._log.error(f"Detection error: {e}")
                self._detected_servers = []

            self._detect_btn.setText("Re-detect")
            self._detect_btn.setEnabled(True)

            for s in self._detected_servers:
                item = QListWidgetItem(f"{s['display_name']} ({s['version'][:50]})")
                item.setData(Qt.ItemDataRole.UserRole, s)
                self._server_list.addItem(item)

            if not self._detected_servers:
                self._server_list.addItem("No database servers detected")

        thread = threading.Thread(target=detect, daemon=True)
        thread.start()

    def _on_server_selected(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            idx = self._db_type_combo.findText(data["name"])
            if idx >= 0:
                self._db_type_combo.setCurrentIndex(idx)
            self._port_input.setText(str(data.get("default_port", "")))

    def _connect_to_server(self):
        db_type = self._db_type_combo.currentText()
        host = self._host_input.text().strip()
        port_str = self._port_input.text().strip()
        port = int(port_str) if port_str else None
        user = self._user_input.text().strip()
        password = self._pass_input.text()

        connector_cls = BackupEngine.CONNECTORS.get(db_type)
        if not connector_cls:
            QMessageBox.warning(self, "Error", f"Unknown database type: {db_type}")
            return

        connector = connector_cls()
        if not connector.connect(host, port or connector.default_port, user, password):
            QMessageBox.warning(self, "Connection Failed",
                                f"Could not connect to {db_type} at {host}:{port}")
            return

        databases = connector.list_databases()
        self._db_list.clear()
        for db in databases:
            item = QListWidgetItem(db)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._db_list.addItem(item)

        if not databases:
            self._db_list.addItem("No user databases found")

        QMessageBox.information(self, "Connected",
                                f"Connected to {db_type}@{host}:{port}\nFound {len(databases)} database(s)")

    def _select_all_dbs(self):
        for i in range(self._db_list.count()):
            item = self._db_list.item(i)
            item.setCheckState(Qt.CheckState.Checked)

    def _get_selected_databases(self) -> list[str]:
        dbs = []
        for i in range(self._db_list.count()):
            item = self._db_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                dbs.append(item.text())

        manual = self._db_input.text().strip()
        if manual:
            dbs.extend([d.strip() for d in manual.split(",") if d.strip()])

        return dbs if dbs else ["all"]

    def _build_config(self) -> dict:
        db_type = self._db_type_combo.currentText()
        host = self._host_input.text().strip() or "localhost"
        port_str = self._port_input.text().strip()
        port = int(port_str) if port_str else None

        session_name = self._session_name.text().strip() or f"Backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        config = {
            "session_name": session_name,
            "db_type": db_type,
            "host": host,
            "port": port,
            "user": self._user_input.text().strip(),
            "password": self._pass_input.text(),
            "databases": self._get_selected_databases(),
            "backup_type": self._backup_type.currentText(),
            "schedule": {"interval": self._schedule.currentText()},
            "compress": self._compress_cb.isChecked(),
            "encrypt": self._encrypt_cb.isChecked(),
            "alerts": {
                "console": self._alert_console.isChecked(),
                "discord": self._alert_discord.isChecked(),
                "email": self._alert_email.isChecked(),
                "slack": self._alert_slack.isChecked(),
                "telegram": self._alert_telegram.isChecked(),
            },
            "destinations": [],
        }

        if self._schedule.currentText() == "cron":
            config["schedule"]["expression"] = self._cron_input.text().strip()

        if self._local_cb.isChecked():
            config["destinations"].append({
                "type": "local",
                "path": self._local_path.text().strip() or str(Path.home() / "backups"),
            })

        if self._discord_cb.isChecked() and self._discord_input.text().strip():
            config["destinations"].append({
                "type": "discord",
                "webhook_url": self._discord_input.text().strip(),
            })

        if self._github_cb.isChecked():
            config["destinations"].append({
                "type": "github",
                "repo": self._gh_repo.text().strip() or "backups",
            })

        return config

    def _run_backup(self):
        config = self._build_config()
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._log_output.clear()
        self._log_output.append(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Starting backup: {config['session_name']}")

        def run():
            try:
                result = self._engine.run_backup(config)
                self._log.info(f"Backup completed: {result['status']}")

                if result.get("errors"):
                    self._log_output.append(f"[ERROR] {len(result['errors'])} error(s) occurred")

                self._progress_bar.setValue(100)
                self._log_output.append(
                    f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] "
                    f"Backup {result['status']}: {config['session_name']}"
                )
            except Exception as e:
                self._log.error(f"Backup failed: {e}")
                self._log_output.append(f"[ERROR] {e}")
                self._progress_bar.setVisible(False)

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _save_session(self):
        config = self._build_config()
        sessions = self._config.get("sessions", {})
        sid = config["session_name"]

        config["created"] = datetime.now(timezone.utc).isoformat()
        config["status"] = "saved"
        sessions[sid] = config
        self._config.set("sessions", sessions)

        sched = config.get("schedule", {})
        if sched.get("interval", "manual") != "manual":
            self._scheduler.schedule_session(
                sid, sched,
                lambda: self._engine.run_backup(config)
            )

        QMessageBox.information(self, "Session Saved",
                                f"Session '{config['session_name']}' saved successfully")

    def _test_github(self):
        try:
            gh = GitHubDestination()
            if gh._authenticate() and gh._ensure_repo():
                QMessageBox.information(self, "GitHub OK",
                                        "Connected to GitHub. Repository 'backups' is ready.")
            else:
                QMessageBox.warning(self, "GitHub Error",
                                    "Could not authenticate with GitHub. Check your token.")
        except Exception as e:
            QMessageBox.critical(self, "GitHub Error", str(e))

    def _upload_session_to_github(self):
        try:
            gh = GitHubDestination()
            if not gh._authenticate() or not gh._ensure_repo():
                QMessageBox.critical(self, "GitHub Error",
                                     "Failed to authenticate or create repository")
                return

            sessions = self._config.get("sessions", {})
            if not sessions:
                QMessageBox.information(self, "No Sessions", "No saved sessions to upload")
                return

            session_names = list(sessions.keys())
            from PyQt6.QtWidgets import QInputDialog
            name, ok = QInputDialog.getItem(self, "Select Session",
                                            "Choose session to upload:", session_names, 0, False)
            if not ok or not name:
                return

            session = sessions[name]
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S_UTC")
            server_ip = session.get("host", "127.0.0.1")

            temp_dir = Path("/tmp") / "ibm_dmt_gh_upload" / timestamp
            temp_dir.mkdir(parents=True, exist_ok=True)

            manifest = {
                "session": session.get("session_name", name),
                "server": server_ip,
                "timestamp": timestamp,
                "db_type": session.get("db_type", "unknown"),
                "config": session,
                "uploaded_at": datetime.now(timezone.utc).isoformat(),
            }
            manifest_path = temp_dir / "session_config.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            metadata = {
                "db_type": session.get("db_type", "unknown"),
            }

            success = gh.upload(
                [str(manifest_path)],
                session.get("session_name", name),
                server_ip,
                timestamp,
                metadata,
            )

            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)

            if success:
                QMessageBox.information(self, "Upload Complete",
                    f"Session '{name}' uploaded to GitHub repository 'backups'")
            else:
                QMessageBox.warning(self, "Upload Issue",
                    "Some files may not have uploaded correctly")

        except Exception as e:
            QMessageBox.critical(self, "GitHub Error", str(e))
