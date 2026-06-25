import json
import hashlib
import socket
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from ibm_dmt.core.logger import Logger
from ibm_dmt.core.alert_manager import AlertManager
from ibm_dmt.core.scheduler import Scheduler
from ibm_dmt.modules.database_backup.compression import Compressor
from ibm_dmt.modules.database_backup.encryption import Encryptor
from ibm_dmt.modules.database_backup.connectors import (
    MySQLConnector, MariaDBConnector, PostgreSQLConnector,
    MongoDBConnector, RedisConnector, SQLiteConnector,
    MSSQLConnector, OracleConnector,
)
from ibm_dmt.modules.database_backup.destinations import (
    LocalDestination, DiscordDestination, GitHubDestination,
)


class BackupEngine:
    CONNECTORS = {
        "mysql": MySQLConnector,
        "mariadb": MariaDBConnector,
        "postgresql": PostgreSQLConnector,
        "mongodb": MongoDBConnector,
        "redis": RedisConnector,
        "sqlite": SQLiteConnector,
        "mssql": MSSQLConnector,
        "oracle": OracleConnector,
    }

    def __init__(self):
        self._log = Logger.get_logger()
        self._alerts = AlertManager()
        self._scheduler = Scheduler()
        self._compressor = Compressor()
        self._encryptor = Encryptor()

    def run_backup(self, config: dict) -> dict:
        session_name = config.get("session_name", "Unnamed")
        db_type = config.get("db_type", "")
        databases = config.get("databases", [])
        backup_type = config.get("backup_type", "full")
        encrypt = config.get("encrypt", False)
        encryption_key = config.get("encryption_key")
        destinations = config.get("destinations", [])
        host = config.get("host", "localhost")
        port = config.get("port")
        user = config.get("user", "")
        password = config.get("password", "")

        server_ip = self._get_server_ip()
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S_UTC")
        db_label = db_type if db_type else "unknown"

        results = {
            "session_name": session_name,
            "server_ip": server_ip,
            "timestamp": timestamp,
            "db_type": db_label,
            "status": "running",
            "files": [],
            "errors": [],
            "started_at": datetime.now(timezone.utc).isoformat(),
        }

        self._alerts.emit("backup_started", {
            "title": f"Backup Started: {session_name}",
            "message": f"Starting {backup_type} backup of {len(databases)} database(s) on {db_label}",
            "event": "started",
            "timestamp": timestamp,
        })

        connector_cls = self.CONNECTORS.get(db_type)
        if not connector_cls:
            err = f"Unsupported database type: {db_type}"
            results["errors"].append(err)
            results["status"] = "failed"
            self._alerts.emit("backup_failure", {"title": "Backup Failed", "message": err, "event": "failure"})
            return results

        connector = connector_cls()
        if not connector.connect(host, port or connector.default_port, user, password):
            err = f"Failed to connect to {db_label} at {host}:{port}"
            results["errors"].append(err)
            results["status"] = "failed"
            self._alerts.emit("backup_failure", {"title": "Backup Failed", "message": err, "event": "failure"})
            return results

        if not databases or databases == ["all"]:
            databases = connector.list_databases()
            if not databases:
                databases = ["all"]

        temp_dir = Path("/tmp") / "ibm_dmt_backups" / timestamp
        temp_dir.mkdir(parents=True, exist_ok=True)

        metadata = {
            "session_name": session_name,
            "db_type": db_label,
            "db_version": connector.get_server_version(),
            "server_ip": server_ip,
            "backup_type": backup_type,
            "databases": databases,
            "timestamp": timestamp,
            "compression": "zstd",
            "encrypted": encrypt,
        }

        total = len(databases)
        for i, db in enumerate(databases):
            self._alerts.emit("progress", {
                "title": "Backup Progress",
                "message": f"Backing up {db} ({i+1}/{total})",
                "progress": (i + 1) / total * 100,
                "event": "progress",
            })

            try:
                dump_path = str(temp_dir / f"{db}.sql")
                connector.dump(db, dump_path, backup_type, host, port, user, password)
                results["files"].append(dump_path)
            except Exception as e:
                err = f"Failed to dump {db}: {e}"
                results["errors"].append(err)
                self._alerts.emit("backup_failure", {"title": f"Dump Failed: {db}", "message": err, "event": "failure"})
                continue

        for i, file_path in enumerate(results["files"][:]):
            try:
                compressed = self._compressor.compress(file_path)
                results["files"][i] = compressed
                Path(file_path).unlink(missing_ok=True)
            except Exception as e:
                err = f"Compression failed for {file_path}: {e}"
                results["errors"].append(err)
                continue

            if encrypt:
                try:
                    encrypted = self._encryptor.encrypt_file(compressed, key=encryption_key)
                    results["files"][i] = encrypted
                    Path(compressed).unlink(missing_ok=True)
                    metadata["encrypted"] = True
                except Exception as e:
                    err = f"Encryption failed: {e}"
                    results["errors"].append(err)

        all_files = results["files"]
        checksums = {}
        for fp in all_files:
            checksums[Path(fp).name] = self._sha256(fp)

        checksum_path = temp_dir / "checksums.sha256"
        with open(checksum_path, "w") as f:
            for name, cksum in checksums.items():
                f.write(f"{cksum}  {name}\n")
        all_files.append(str(checksum_path))

        manifest = {
            "session": session_name,
            "server": server_ip,
            "timestamp": timestamp,
            "db_type": db_label,
            "backup_type": backup_type,
            "files": [Path(fp).name for fp in all_files],
            "checksums": checksums,
        }
        manifest_path = temp_dir / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        all_files.append(str(manifest_path))

        metadata_path = temp_dir / "metadata.json"
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        all_files.append(str(metadata_path))

        log_path = self._write_log(results, temp_dir)
        all_files.append(log_path)

        for dest_config in destinations:
            dest_type = dest_config.get("type", "local")
            try:
                dest = self._create_destination(dest_type, dest_config)
                success = dest.upload(
                    all_files, session_name, server_ip, timestamp, metadata
                )
                if success:
                    self._alerts.emit("upload_success", {
                        "title": f"Uploaded to {dest_type}",
                        "message": f"Backup uploaded to {dest_type}",
                        "event": "success",
                        "timestamp": timestamp,
                    })
                else:
                    self._alerts.emit("upload_failure", {
                        "title": f"Upload Failed: {dest_type}",
                        "message": f"Failed to upload to {dest_type}",
                        "event": "upload_failure",
                    })
            except Exception as e:
                self._alerts.emit("upload_failure", {
                    "title": f"Upload Error: {dest_type}",
                    "message": str(e),
                    "event": "upload_failure",
                })

        for fp in all_files:
            if Path(fp).exists():
                cksum = self._sha256(fp)
                if cksum != checksums.get(Path(fp).name):
                    results["errors"].append(f"Verification failed for {fp}")
                    self._alerts.emit("verification_failure", {
                        "title": "Verification Failed",
                        "message": f"SHA-256 mismatch for {Path(fp).name}",
                        "event": "verification_failure",
                    })

        results["status"] = "completed" if not results["errors"] else "completed_with_errors"
        results["completed_at"] = datetime.now(timezone.utc).isoformat()

        self._alerts.emit("backup_success" if results["status"] == "completed" else "backup_failure", {
            "title": f"Backup {results['status'].title()}: {session_name}",
            "message": f"Backup of {len(databases)} database(s) on {db_label} completed",
            "event": "success" if results["status"] == "completed" else "failure",
            "timestamp": timestamp,
        })

        self._cleanup_temp(temp_dir, all_files)
        return results

    def _create_destination(self, dest_type: str, config: dict):
        if dest_type == "local":
            return LocalDestination(config.get("path"))
        elif dest_type == "discord":
            return DiscordDestination(config.get("webhook_url"))
        elif dest_type == "github":
            return GitHubDestination(config.get("token"), config.get("repo", "backups"))
        raise ValueError(f"Unknown destination type: {dest_type}")

    def _get_server_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _sha256(self, file_path: str) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def _write_log(self, results: dict, temp_dir: Path) -> str:
        log_path = str(temp_dir / "logs.txt")
        with open(log_path, "w") as f:
            f.write(f"IBM-DMT Backup Log\n")
            f.write(f"{'='*60}\n")
            f.write(f"Session: {results['session_name']}\n")
            f.write(f"Server: {results['server_ip']}\n")
            f.write(f"Timestamp: {results['timestamp']}\n")
            f.write(f"DB Type: {results['db_type']}\n")
            f.write(f"Status: {results['status']}\n")
            f.write(f"{'='*60}\n\n")
            if results["files"]:
                f.write("Files:\n")
                for fp in results["files"]:
                    f.write(f"  - {fp}\n")
            if results["errors"]:
                f.write("\nErrors:\n")
                for err in results["errors"]:
                    f.write(f"  - {err}\n")
        return log_path

    def _cleanup_temp(self, temp_dir: Path, keep_files: list[str]) -> None:
        for fp in keep_files:
            try:
                Path(fp).unlink(missing_ok=True)
            except Exception:
                pass
        try:
            temp_dir.rmdir()
        except Exception:
            pass

    def detect_databases(self) -> list[dict]:
        detected = []
        for name, cls in self.CONNECTORS.items():
            try:
                connector = cls()
                if connector.detect():
                    detected.append({
                        "name": name,
                        "display_name": connector.display_name,
                        "version": connector.get_server_version(),
                        "default_port": connector.default_port,
                    })
            except Exception as e:
                self._log.error(f"Detection failed for {name}: {e}")
        return detected
