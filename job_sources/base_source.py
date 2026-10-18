"""Base Abstract Class for all Job Source Connectors."""

from __future__ import annotations

import logging
import random
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import requests

from job_parser.extractor import ParsedJob

logger = logging.getLogger("job_source")


class BaseJobSource(ABC):
    def __init__(self, platform_id: str, base_url: str, rate_limit_delay: float = 2.0):
        self.platform_id = platform_id
        self.base_url = base_url
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        })

    def polite_delay(self) -> None:
        """Sleep with random jitter to prevent bursting."""
        delay = self.rate_limit_delay + random.uniform(0.5, 1.5)
        time.sleep(delay)

    def safe_get(self, url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 15) -> Optional[requests.Response]:
        """Execute HTTP GET with exponential backoff and 429 detection."""
        backoff = 2.0
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                self.polite_delay()
                resp = self.session.get(url, params=params, timeout=timeout)
                if resp.status_code == 200:
                    return resp
                elif resp.status_code in [429, 503]:
                    logger.warning(f"[{self.platform_id}] HTTP {resp.status_code} received. Backing off {backoff}s (attempt {attempt}/{max_attempts})")
                    time.sleep(backoff)
                    backoff *= 2.0
                else:
                    logger.error(f"[{self.platform_id}] HTTP {resp.status_code} for {url}")
                    return None
            except Exception as e:
                logger.error(f"[{self.platform_id}] Connection error: {e}")
                time.sleep(backoff)
                backoff *= 2.0
        return None

    @abstractmethod
    def discover_jobs(self, query: str = "python developer", location: str = "Bengaluru", limit: int = 20) -> List[ParsedJob]:
        """Discover and return parsed jobs."""
        pass
