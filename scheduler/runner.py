"""Background Job Discovery Scheduler and Periodic Report Runner."""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger("job_scheduler")


class BackgroundJobScheduler:
    def __init__(self, run_discovery_fn: Callable[[], Any], interval_minutes: int = 60):
        self.run_discovery_fn = run_discovery_fn
        self.interval_seconds = interval_minutes * 60
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.is_running = False

    def start(self) -> None:
        """Start the background scheduler thread."""
        if self.is_running:
            logger.info("Scheduler already active.")
            return

        self._stop_event.clear()
        self.is_running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="JobDiscoveryScheduler")
        self._thread.start()
        logger.info(f"Background Job Discovery Scheduler started with interval {self.interval_seconds // 60} minutes.")

    def stop(self) -> None:
        """Safely halt the scheduler."""
        if not self.is_running:
            return
        self._stop_event.set()
        self.is_running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        logger.info("Background Job Discovery Scheduler safely stopped.")

    def _loop(self) -> None:
        # Run immediately upon start
        try:
            logger.info("Triggering initial discovery run in background scheduler...")
            self.run_discovery_fn()
        except Exception as e:
            logger.error(f"Error in scheduler initial discovery run: {e}")

        while not self._stop_event.is_set():
            # Wait for interval or stop event in 1s increments
            waited = 0
            while waited < self.interval_seconds and not self._stop_event.is_set():
                time.sleep(1)
                waited += 1

            if not self._stop_event.is_set():
                try:
                    logger.info("Running scheduled discovery cycle...")
                    self.run_discovery_fn()
                except Exception as e:
                    logger.error(f"Error executing scheduled discovery cycle: {e}")


def get_default_scheduler(run_fn: Callable[[], Any], interval_minutes: int = 60) -> BackgroundJobScheduler:
    return BackgroundJobScheduler(run_discovery_fn=run_fn, interval_minutes=interval_minutes)
