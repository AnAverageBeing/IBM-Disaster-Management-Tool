import json
from datetime import datetime, timezone
from typing import Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from ibm_dmt.core.config import Config
from ibm_dmt.core.logger import Logger


class Scheduler:
    _instance = None
    _scheduler: BackgroundScheduler = None
    _jobs: dict = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup()
        return cls._instance

    def _setup(self):
        self._scheduler = BackgroundScheduler()
        self._scheduler.start()
        self._config = Config()
        self._log = Logger.get_logger()
        self._restore_jobs()

    def _restore_jobs(self):
        sessions = self._config.get("scheduled_sessions", {})
        for session_id, info in sessions.items():
            try:
                callback_path = info.get("callback")
                if callback_path:
                    self._log.info(f"Restored scheduled session: {session_id}")
            except Exception as e:
                self._log.error(f"Failed to restore session {session_id}: {e}")

    def schedule_session(self, session_id: str, schedule_config: dict,
                         callback: Callable) -> None:
        trigger = self._parse_schedule(schedule_config)
        if trigger is None:
            return

        job = self._scheduler.add_job(
            callback,
            trigger,
            id=session_id,
            replace_existing=True,
            name=f"backup_{session_id}",
        )
        self._jobs[session_id] = job

        sessions = self._config.get("scheduled_sessions", {})
        sessions[session_id] = {
            "schedule": schedule_config,
            "created": datetime.now(timezone.utc).isoformat(),
        }
        self._config.set("scheduled_sessions", sessions)
        self._log.info(f"Scheduled session {session_id} with {schedule_config}")

    def remove_session(self, session_id: str) -> None:
        if session_id in self._jobs:
            self._scheduler.remove_job(session_id)
            del self._jobs[session_id]
        sessions = self._config.get("scheduled_sessions", {})
        sessions.pop(session_id, None)
        self._config.set("scheduled_sessions", sessions)

    def update_session(self, session_id: str, schedule_config: dict,
                       callback: Callable) -> None:
        self.remove_session(session_id)
        self.schedule_session(session_id, schedule_config, callback)

    def _parse_schedule(self, config: dict) -> Optional[object]:
        schedule_type = config.get("type", "interval")

        if schedule_type == "cron":
            return CronTrigger.from_crontab(config["expression"])

        intervals = {
            "10m": IntervalTrigger(minutes=10),
            "30m": IntervalTrigger(minutes=30),
            "1h": IntervalTrigger(hours=1),
            "6h": IntervalTrigger(hours=6),
            "24h": IntervalTrigger(hours=24),
            "weekly": IntervalTrigger(weeks=1),
            "monthly": IntervalTrigger(weeks=4),
        }
        return intervals.get(config.get("interval"))

    def get_scheduled_sessions(self) -> dict:
        return self._jobs

    def stop(self):
        self._scheduler.shutdown(wait=False)
