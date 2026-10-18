"""Render Cloud Anti-Sleep Keep-Alive Engine.

Render free tier web services spin down after 15 minutes of inactivity.
This background thread pings the service's /healthz endpoint every 10 minutes
(via RENDER_EXTERNAL_URL or KEEP_ALIVE_URL) to maintain 24/7 continuous uptime.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Optional
import requests

logger = logging.getLogger("keep_alive")

_keep_alive_thread: Optional[threading.Thread] = None
_keep_alive_stop_event = threading.Event()


def start_keep_alive_pinger(
    target_url: Optional[str] = None,
    interval_seconds: int = 600,
) -> Optional[threading.Thread]:
    """Start anti-sleep self-pinger thread if cloud URL is configured."""
    global _keep_alive_thread, _keep_alive_stop_event

    url = target_url or os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("KEEP_ALIVE_URL")
    if not url:
        logger.info("No RENDER_EXTERNAL_URL or KEEP_ALIVE_URL configured. Local mode: keep-alive pinger inactive.")
        return None

    if _keep_alive_thread and _keep_alive_thread.is_alive():
        logger.info("Keep-alive pinger is already active.")
        return _keep_alive_thread

    # Normalize URL
    if not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"
    clean_url = url.rstrip("/")
    health_endpoint = f"{clean_url}/healthz"

    _keep_alive_stop_event.clear()

    def _ping_loop():
        logger.info(f"Keep-alive anti-sleep pinger started for {health_endpoint} (interval: {interval_seconds}s)")
        # Wait initial 60 seconds before first ping
        time.sleep(60)

        while not _keep_alive_stop_event.is_set():
            try:
                headers = {"User-Agent": "AntigravityJobAgent-KeepAlive/2.5"}
                resp = requests.get(health_endpoint, headers=headers, timeout=15)
                logger.info(f"[Keep-Alive] Pinged {health_endpoint} - Status: {resp.status_code}")
            except Exception as e:
                logger.warning(f"[Keep-Alive] Self-ping warning (service may still be starting): {e}")

            # Sleep in 1-second chunks to respond quickly to stop event
            waited = 0
            while waited < interval_seconds and not _keep_alive_stop_event.is_set():
                time.sleep(1)
                waited += 1

    _keep_alive_thread = threading.Thread(target=_ping_loop, daemon=True, name="RenderAntiSleepPinger")
    _keep_alive_thread.start()
    return _keep_alive_thread


def stop_keep_alive_pinger():
    """Halt the keep-alive thread."""
    global _keep_alive_stop_event, _keep_alive_thread
    _keep_alive_stop_event.set()
    if _keep_alive_thread and _keep_alive_thread.is_alive():
        _keep_alive_thread.join(timeout=2)
    logger.info("Keep-alive pinger stopped.")
