import json
from datetime import datetime, timezone
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QSplitter, QWidget,
    QTextEdit, QGroupBox, QFormLayout, QLineEdit,
    QComboBox, QCheckBox, QFileDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal
from ibm_dmt.core.config import Config
from ibm_dmt.core.logger import Logger
from ibm_dmt.core.credential_store import CredentialStore
from ibm_dmt.modules.database_backup.backup_engine import BackupEngine


class SessionManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._log = Logger.get_logger()
        self._config = Config()
        self._engine = BackupEngine()
        self._creds = CredentialStore()
        self.setWindowTitle("Manage Sessions")
        self.setMinimumSize(900, 600)
        self._init_ui()
        self._load_sessions()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        title = QLabel("Backup Sessions")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        subtitle = QLabel("Manage, edit, or delete previously created backup sessions")
        subtitle.setObjectName("subtitleLabel")
        layout.addWidget(subtitle)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels([
            "Session Name", "DB Type", "Schedule", "Last Run", "Status",
            "Destinations", "Created"
        ])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        layout.addWidget(self._table)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._load_sessions)
        btn_layout.addWidget(refresh_btn)

        edit_btn = QPushButton("Edit Selected")
        edit_btn.setObjectName("primaryButton")
        edit_btn.clicked.connect(self._edit_session)
        btn_layout.addWidget(edit_btn)

        delete_btn = QPushButton("Delete Selected")
        delete_btn.setObjectName("dangerButton")
        delete_btn.clicked.connect(self._delete_session)
        btn_layout.addWidget(delete_btn)

        run_btn = QPushButton("Run Now")
        run_btn.clicked.connect(self._run_session_now)
        btn_layout.addWidget(run_btn)

        btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_layout.addWidget(close_btn)

        layout.addLayout(btn_layout)

    def _load_sessions(self):
        self._table.setRowCount(0)
        sessions = self._config.get("sessions", {})
        if not sessions:
            self._table.setRowCount(1)
            self._table.setItem(0, 0, QTableWidgetItem("No sessions found"))
            self._table.setSpan(0, 0, 1, 7)
            return

        row = 0
        for session_id, session in sorted(sessions.items(),
                                          key=lambda x: x[1].get("created", ""), reverse=True):
            self._table.insertRow(row)
            self._table.setItem(row, 0, QTableWidgetItem(session.get("session_name", session_id)))
            self._table.setItem(row, 1, QTableWidgetItem(session.get("db_type", "")))
            sched = session.get("schedule", {})
            sched_str = sched.get("interval") or sched.get("expression", "manual")
            self._table.setItem(row, 2, QTableWidgetItem(sched_str))
            self._table.setItem(row, 3, QTableWidgetItem(session.get("last_run", "Never")))
            self._table.setItem(row, 4, QTableWidgetItem(session.get("status", "idle")))
            dests = ", ".join(d.get("type", "") for d in session.get("destinations", []))
            self._table.setItem(row, 5, QTableWidgetItem(dests if dests else "None"))
            created = session.get("created", "")
            if created:
                try:
                    dt = datetime.fromisoformat(created)
                    created = dt.strftime("%Y-%m-%d %H:%M")
                except Exception:
                    pass
            self._table.setItem(row, 6, QTableWidgetItem(created))

            item = QTableWidgetItem(session_id)
            item.setHidden(True)
            self._table.setItem(row, 0, item)
            # Restore visible name
            self._table.setItem(row, 0, QTableWidgetItem(session.get("session_name", session_id)))
            row += 1

    def _get_selected_session(self) -> dict:
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a session first")
            return {}
        session_id_item = self._table.item(row, 0)
        if not session_id_item:
            return {}

        sessions = self._config.get("sessions", {})
        for sid, session in sessions.items():
            if session.get("session_name") == session_id_item.text() or sid == session_id_item.text():
                session["_id"] = sid
                return session
        return {}

    def _edit_session(self):
        session = self._get_selected_session()
        if not session:
            return

        dialog = EditSessionDialog(session, self)
        if dialog.exec():
            self._load_sessions()

    def _delete_session(self):
        session = self._get_selected_session()
        if not session:
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete session '{session.get('session_name')}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            sessions = self._config.get("sessions", {})
            sid = session.get("_id", session.get("session_name"))
            sessions.pop(sid, None)
            self._config.set("sessions", sessions)
            self._load_sessions()

    def _run_session_now(self):
        session = self._get_selected_session()
        if not session:
            return

        try:
            import threading
            result = {"status": "running"}
            self._log.info(f"Running session: {session.get('session_name')}")

            def run():
                self._engine.run_backup(session)

            thread = threading.Thread(target=run, daemon=True)
            thread.start()
            QMessageBox.information(self, "Backup Started",
                                    f"Backup session '{session.get('session_name')}' started in background")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start backup: {e}")


class EditSessionDialog(QDialog):
    def __init__(self, session: dict, parent=None):
        super().__init__(parent)
        self._session = session
        self.setWindowTitle(f"Edit Session: {session.get('session_name', '')}")
        self.setMinimumSize(500, 400)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        form = QFormLayout()
        form.setSpacing(12)

        self._name_input = QLineEdit(self._session.get("session_name", ""))
        form.addRow("Session Name:", self._name_input)

        self._db_type = QComboBox()
        self._db_type.addItems(["mysql", "mariadb", "postgresql", "mongodb", "redis", "sqlite", "mssql", "oracle"])
        current_db = self._session.get("db_type", "")
        idx = self._db_type.findText(current_db)
        if idx >= 0:
            self._db_type.setCurrentIndex(idx)
        form.addRow("Database Type:", self._db_type)

        self._host_input = QLineEdit(self._session.get("host", "localhost"))
        form.addRow("Host:", self._host_input)

        self._port_input = QLineEdit(str(self._session.get("port", "")))
        form.addRow("Port:", self._port_input)

        self._user_input = QLineEdit(self._session.get("user", ""))
        form.addRow("Username:", self._user_input)

        self._databases_input = QLineEdit(", ".join(self._session.get("databases", [])))
        form.addRow("Databases (comma-sep):", self._databases_input)

        self._backup_type = QComboBox()
        self._backup_type.addItems(["full", "incremental", "differential"])
        bt = self._session.get("backup_type", "full")
        idx = self._backup_type.findText(bt)
        if idx >= 0:
            self._backup_type.setCurrentIndex(idx)
        form.addRow("Backup Type:", self._backup_type)

        self._schedule = QComboBox()
        self._schedule.addItems(["manual", "10m", "30m", "1h", "6h", "24h", "weekly", "monthly", "cron"])
        sched = self._session.get("schedule", {}).get("interval", "manual")
        idx = self._schedule.findText(sched)
        if idx >= 0:
            self._schedule.setCurrentIndex(idx)
        form.addRow("Schedule:", self._schedule)

        self._encrypt_cb = QCheckBox("Enable AES-256 encryption")
        self._encrypt_cb.setChecked(self._session.get("encrypt", False))
        form.addRow("", self._encrypt_cb)

        layout.addLayout(form)
        layout.addStretch()

        btn_layout = QHBoxLayout()

        upload_github_btn = QPushButton("Upload to GitHub")
        upload_github_btn.setObjectName("primaryButton")
        upload_github_btn.clicked.connect(self._upload_to_github)
        btn_layout.addWidget(upload_github_btn)

        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save Changes")
        save_btn.setObjectName("primaryButton")
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        layout.addLayout(btn_layout)

    def _upload_to_github(self):
        try:
            from ibm_dmt.modules.database_backup.destinations.github import GitHubDestination
            gh = GitHubDestination()
            if not gh._authenticate() or not gh._ensure_repo():
                QMessageBox.critical(self, "GitHub Error", "Failed to authenticate or create repo")
                return

            session_name = self._name_input.text().strip() or self._session.get("session_name", "unknown")
            server_ip = self._session.get("server_ip", "127.0.0.1")
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S_UTC")

            metadata = {
                "db_type": self._db_type.currentText(),
                "session_name": session_name,
            }

            backup_dir = Path("/tmp") / "ibm_dmt_upload" / timestamp
            backup_dir.mkdir(parents=True, exist_ok=True)

            manifest = {
                "session": session_name,
                "server": server_ip,
                "timestamp": timestamp,
                "db_type": metadata["db_type"],
                "status": "manual_upload",
            }
            manifest_path = backup_dir / "manifest.json"
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            success = gh.upload(
                [str(manifest_path)], session_name, server_ip, timestamp, metadata
            )

            if success:
                QMessageBox.information(self, "GitHub Upload",
                    f"Session metadata uploaded to GitHub repo 'backups'")
            else:
                QMessageBox.warning(self, "Upload Issue",
                    "Some files may not have uploaded correctly")

            import shutil
            shutil.rmtree(backup_dir, ignore_errors=True)

        except Exception as e:
            QMessageBox.critical(self, "GitHub Error", str(e))

    def _save(self):
        sessions_cfg = Config()
        all_sessions = sessions_cfg.get("sessions", {})
        sid = self._session.get("_id", self._session.get("session_name"))

        db_str = self._databases_input.text().strip()
        databases = [d.strip() for d in db_str.split(",") if d.strip()]

        all_sessions[sid] = {
            "session_name": self._name_input.text().strip() or sid,
            "db_type": self._db_type.currentText(),
            "host": self._host_input.text().strip() or "localhost",
            "port": int(self._port_input.text().strip()) if self._port_input.text().strip() else None,
            "user": self._user_input.text().strip(),
            "databases": databases,
            "backup_type": self._backup_type.currentText(),
            "schedule": {"interval": self._schedule.currentText()},
            "encrypt": self._encrypt_cb.isChecked(),
            "destinations": self._session.get("destinations", []),
            "updated": datetime.now(timezone.utc).isoformat(),
        }
        if "created" in self._session:
            all_sessions[sid]["created"] = self._session["created"]

        sessions_cfg.set("sessions", all_sessions)
        self.accept()
