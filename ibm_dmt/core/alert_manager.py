import json
import smtplib
import ssl
from email.mime.text import MIMEText
from typing import Any, Callable
from ibm_dmt.core.logger import Logger
from ibm_dmt.core.config import Config
from ibm_dmt.core.credential_store import CredentialStore


class AlertManager:
    _instance = None
    _handlers: dict[str, list[Callable]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup()
        return cls._instance

    def _setup(self):
        self._log = Logger.get_logger()
        self._config = Config()
        self._creds = CredentialStore()

    def on(self, event: str, handler: Callable) -> None:
        if event not in self._handlers:
            self._handlers[event] = []
        self._handlers[event].append(handler)

    def emit(self, event: str, data: dict = None) -> None:
        if event not in self._handlers:
            return
        for handler in self._handlers[event]:
            try:
                handler(data or {})
            except Exception as e:
                self._log.error(f"Alert handler failed for {event}: {e}")

    def send_console(self, data: dict) -> None:
        level = data.get("level", "INFO")
        message = data.get("message", "")
        self._log.logger.log(
            getattr(self._log.logger, level.upper(), 20), f"[ALERT] {message}"
        )

    def send_discord(self, data: dict) -> None:
        webhook_url = self._config.get("alerts.discord_webhook")
        if not webhook_url:
            return
        import requests
        color_map = {"success": 3066993, "failure": 15158332, "started": 3447003,
                     "progress": 15844367, "verification_failure": 15158332,
                     "upload_failure": 15158332, "low_disk_space": 16776960}
        embed = {
            "title": data.get("title", "Backup Alert"),
            "description": data.get("message", ""),
            "color": color_map.get(data.get("event", ""), 3447003),
            "timestamp": data.get("timestamp", ""),
        }
        payload = {"embeds": [embed]}
        try:
            import requests
            requests.post(webhook_url, json=payload, timeout=10)
        except Exception as e:
            self._log.error(f"Discord alert failed: {e}")

    def send_email(self, data: dict) -> None:
        smtp_config = self._config.get("alerts.email", {})
        if not smtp_config.get("enabled"):
            return

        msg = MIMEText(data.get("message", ""))
        msg["Subject"] = data.get("title", "IBM-DMT Alert")
        msg["From"] = smtp_config["from"]
        msg["To"] = smtp_config["to"]

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_config["host"], smtp_config.get("port", 587)) as server:
                server.starttls(context=context)
                server.login(smtp_config["user"],
                             self._creds.get("smtp").get("password", ""))
                server.send_message(msg)
        except Exception as e:
            self._log.error(f"Email alert failed: {e}")

    def send_slack(self, data: dict) -> None:
        webhook_url = self._config.get("alerts.slack_webhook")
        if not webhook_url:
            return
        import requests
        payload = {
            "text": f"*{data.get('title', 'Backup Alert')}*\n{data.get('message', '')}"
        }
        try:
            import requests
            requests.post(webhook_url, json=payload, timeout=10)
        except Exception as e:
            self._log.error(f"Slack alert failed: {e}")

    def send_telegram(self, data: dict) -> None:
        bot_token = self._creds.get("telegram").get("bot_token", "")
        chat_id = self._creds.get("telegram").get("chat_id", "")
        if not bot_token or not chat_id:
            return
        import requests
        text = f"*{data.get('title', 'Backup Alert')}*\n{data.get('message', '')}"
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        try:
            import requests
            requests.post(url, json={"chat_id": chat_id, "text": text,
                                     "parse_mode": "Markdown"}, timeout=10)
        except Exception as e:
            self._log.error(f"Telegram alert failed: {e}")

    def register_default_handlers(self) -> None:
        self.on("console", self.send_console)
        self.on("discord", self.send_discord)
        self.on("email", self.send_email)
        self.on("slack", self.send_slack)
        self.on("telegram", self.send_telegram)
