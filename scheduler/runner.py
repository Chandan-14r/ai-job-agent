"""Background Job Discovery Scheduler and Periodic Report Runner."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger("job_scheduler")

_global_scheduler: Optional[BackgroundJobScheduler] = None


class BackgroundJobScheduler:
    def __init__(
        self,
        run_discovery_fn: Callable[[], Any],
        interval_minutes: int = 720,
        initial_delay_seconds: int = 15,
    ):
        self.run_discovery_fn = run_discovery_fn
        self.interval_seconds = interval_minutes * 60
        self.initial_delay_seconds = initial_delay_seconds
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.is_running = False
        self.run_count = 0
        self.last_run_time: Optional[str] = None
        self.next_run_time: Optional[str] = None
        self.last_status: str = "INITIALIZED"
        self.last_error: Optional[str] = None

    def start(self) -> None:
        """Start the background scheduler thread."""
        global _global_scheduler
        if self.is_running:
            logger.info("Scheduler already active.")
            return

        self._stop_event.clear()
        self.is_running = True
        _global_scheduler = self
        self._thread = threading.Thread(target=self._loop, daemon=True, name="JobDiscoveryScheduler")
        self._thread.start()
        logger.info(
            f"Background Job Discovery Scheduler started (Interval: {self.interval_seconds // 60}m, "
            f"Initial delay: {self.initial_delay_seconds}s)."
        )

    def stop(self) -> None:
        """Safely halt the scheduler."""
        if not self.is_running:
            return
        self._stop_event.set()
        self.is_running = False
        self.last_status = "STOPPED"
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        logger.info("Background Job Discovery Scheduler safely stopped.")

    def get_status(self) -> Dict[str, Any]:
        """Return runtime diagnostic telemetry for the scheduler."""
        return {
            "is_running": self.is_running,
            "interval_minutes": self.interval_seconds // 60,
            "run_count": self.run_count,
            "last_run_time": self.last_run_time,
            "next_run_time": self.next_run_time,
            "last_status": self.last_status,
            "last_error": self.last_error,
        }

    def _execute_cycle(self) -> None:
        now_dt = datetime.utcnow()
        self.last_run_time = now_dt.isoformat() + "Z"
        next_dt = now_dt + timedelta(seconds=self.interval_seconds)
        self.next_run_time = next_dt.isoformat() + "Z"
        self.last_status = "RUNNING"
        try:
            self.run_discovery_fn()
            self.run_count += 1
            self.last_status = "COMPLETED"
            self.last_error = None
        except Exception as e:
            self.last_status = "ERROR"
            self.last_error = str(e)
            logger.error(f"Error during scheduled discovery cycle: {e}")

    def _loop(self) -> None:
        if self.initial_delay_seconds > 0:
            logger.info(f"Background scheduler waiting {self.initial_delay_seconds}s before initial harvest...")
            waited = 0
            while waited < self.initial_delay_seconds and not self._stop_event.is_set():
                time.sleep(1)
                waited += 1

        if not self._stop_event.is_set():
            logger.info("Triggering initial discovery run in background scheduler...")
            self._execute_cycle()

        while not self._stop_event.is_set():
            waited = 0
            while waited < self.interval_seconds and not self._stop_event.is_set():
                time.sleep(1)
                waited += 1

            if not self._stop_event.is_set():
                logger.info("Running recurring scheduled discovery cycle...")
                self._execute_cycle()


def get_global_scheduler() -> Optional[BackgroundJobScheduler]:
    global _global_scheduler
    return _global_scheduler


def get_default_scheduler(
    run_fn: Callable[[], Any],
    interval_minutes: int = 360,
    initial_delay_seconds: int = 15,
) -> BackgroundJobScheduler:
    return BackgroundJobScheduler(
        run_discovery_fn=run_fn,
        interval_minutes=interval_minutes,
        initial_delay_seconds=initial_delay_seconds,
    )

