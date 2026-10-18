"""Live Job Discovery Connector for Real Technical Employers."""

from __future__ import annotations

import logging
from typing import List
from job_parser.extractor import JobExtractor, ParsedJob
from job_sources.base_source import BaseJobSource
from job_sources.connectors.greenhouse_connector import GreenhouseConnector

logger = logging.getLogger("live_discovery")

# Active tech employers with public Greenhouse ATS boards hiring in India / Remote
PUBLIC_ATS_EMPLOYERS = [
    ("canonical", "Canonical"),
    ("gitlab", "GitLab"),
    ("automattic", "Automattic"),
]


class LivePublicDiscoverySource(BaseJobSource):
    """Compliant public discovery connector for real live tech employer openings."""

    def __init__(self):
        super().__init__(
            platform_id="public_ats_discovery",
            base_url="https://boards-api.greenhouse.io",
            rate_limit_delay=1.0,
        )

    def discover_jobs(self, query: str = "python", location: str = "India", limit: int = 15) -> List[ParsedJob]:
        all_jobs: List[ParsedJob] = []

        for token, display_name in PUBLIC_ATS_EMPLOYERS:
            try:
                conn = GreenhouseConnector(board_token=token)
                found = conn.discover_jobs(query=query, location=location, limit=5)
                for j in found:
                    j.employer = display_name
                    all_jobs.append(j)
                    if len(all_jobs) >= limit:
                        break
            except Exception as e:
                logger.warning(f"Could not fetch public jobs for {display_name}: {e}")

            if len(all_jobs) >= limit:
                break

        return all_jobs
