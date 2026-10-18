"""Greenhouse ATS Public API Connector."""

from __future__ import annotations

import logging
from typing import List, Optional

from job_parser.extractor import JobExtractor, ParsedJob
from job_sources.base_source import BaseJobSource

logger = logging.getLogger("greenhouse_connector")


class GreenhouseConnector(BaseJobSource):
    """
    Compliant public Greenhouse API connector.
    Reads open job postings from public boards without private scraping or anti-bot bypass.
    """
    def __init__(self, board_token: str = "canonical"):
        super().__init__(
            platform_id="greenhouse_ats",
            base_url="https://boards-api.greenhouse.io/v1/boards",
            rate_limit_delay=1.5,
        )
        self.board_token = board_token

    def discover_jobs(self, query: str = "python", location: str = "Bengaluru", limit: int = 20) -> List[ParsedJob]:
        url = f"{self.base_url}/{self.board_token}/jobs?content=true"
        resp = self.safe_get(url)
        if not resp:
            return []

        try:
            data = resp.json()
            raw_jobs = data.get("jobs", [])
            results = []

            for rj in raw_jobs:
                title = rj.get("title", "")
                content = rj.get("content", "")
                ext_id = str(rj.get("id", ""))
                job_url = rj.get("absolute_url", "")
                updated_at = rj.get("updated_at")
                offices = rj.get("offices", [])
                loc_str = ", ".join([o.get("name", "") for o in offices]) or "Bengaluru, Karnataka, India"

                # Check if query matches title or content
                q_lower = query.lower()
                if q_lower in title.lower() or q_lower in content.lower():
                    parsed = JobExtractor.parse_job(
                        title=title,
                        employer=self.board_token.capitalize(),
                        description=content,
                        job_url=job_url,
                        external_job_id=ext_id,
                        source_platform="greenhouse_ats",
                        posting_date=updated_at,
                        location_raw=loc_str,
                    )
                    results.append(parsed)
                    if len(results) >= limit:
                        break

            return results
        except Exception as e:
            logger.error(f"Error parsing Greenhouse feed: {e}")
            return []
