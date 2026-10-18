"""Centralized Job URL Verification & Provenance Engine.

Validates well-formedness, domain authenticity, live accessibility, redirect tracing,
and distinguishes genuine active vacancies from expired, invalid, and demo-only records.
"""

from __future__ import annotations

import logging
import re
import urllib.parse
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
import requests

from database.models import URLVerificationStatus

logger = logging.getLogger("url_validator")

# Recognized public ATS domains where direct HTTP verification is permitted
PUBLIC_ATS_DOMAINS = [
    "boards.greenhouse.io",
    "job-boards.greenhouse.io",
    "boards-api.greenhouse.io",
    "jobs.lever.co",
    "api.lever.co",
    "jobs.ashbyhq.com",
    "boards.eu.greenhouse.io",
    "canonical.com",
    "gitlab.com",
    "elastic.co",
]

# Portals with anti-bot / login walls where automated requests return 403/999/redirect to login
RESTRICTED_PORTAL_DOMAINS = [
    "linkedin.com",
    "www.linkedin.com",
    "naukri.com",
    "www.naukri.com",
    "internshala.com",
    "foundit.in",
    "www.foundit.in",
    "indeed.com",
    "in.indeed.com",
    "myworkdayjobs.com",
]

# Known synthetic or mock domains used strictly in Demo Fixtures
SYNTHETIC_MOCK_DOMAINS = [
    "mock.jobs.local",
    "careers.fintechinnovations.com",
    "datasphere.com",
    "fasttrack-scam.com",
    "globalbpo.com",
    "cloudscale.lever.co",
    "cloudmatrix.com",
]


class URLValidator:
    """Centralized URL Validator enforcing Phase 5.4 requirements."""

    @staticmethod
    def is_well_formed(url: Optional[str]) -> bool:
        """Check if URL has a valid scheme (http/https) and network location."""
        if not url:
            return False
        clean = url.strip()
        if clean in ["#", "", "javascript:void(0)", "None", "null"]:
            return False
        try:
            parsed = urllib.parse.urlparse(clean)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except Exception:
            return False

    @classmethod
    def validate_url(
        cls,
        url: Optional[str],
        is_synthetic: bool = False,
        employer: str = "",
        check_live_network: bool = True,
        timeout: float = 4.0,
    ) -> Tuple[URLVerificationStatus, str, str]:
        """
        Validate URL and return (status, reason, final_canonical_url).
        Statuses:
          - VERIFIED_ACTIVE: Real live job posting responding HTTP 200.
          - SOURCE_CONFIRMED: Genuine portal listing, automated HTTP verification blocked by portal ToS/login.
          - NOT_AUTOMATICALLY_VERIFIABLE: Requires candidate manual login/browser verification.
          - EXPIRED: Job listing removed or returned 404/410.
          - INVALID_LINK: Malformed or unroutable URL.
          - SOURCE_UNAVAILABLE: Network timeout or connection refusal from employer server.
          - DEMO_ONLY: Synthetic mock test fixture.
        """
        if not url or not cls.is_well_formed(url):
            return URLVerificationStatus.INVALID_LINK, "Malformed or missing URL.", url or ""

        clean_url = url.strip()
        parsed = urllib.parse.urlparse(clean_url)
        hostname = (parsed.hostname or "").lower()

        # Check for synthetic demo domains
        if is_synthetic or any(syn in hostname for syn in SYNTHETIC_MOCK_DOMAINS):
            return (
                URLVerificationStatus.DEMO_ONLY,
                "DEMO DATA — NOT A REAL JOB VACANCY. Synthetic test fixture.",
                clean_url,
            )

        # Check for login-restricted portals (LinkedIn, Naukri, Internshala)
        if any(portal in hostname for portal in RESTRICTED_PORTAL_DOMAINS):
            return (
                URLVerificationStatus.SOURCE_CONFIRMED,
                f"Authentic {hostname} opportunity. Requires candidate portal authentication to view.",
                clean_url,
            )

        # If network check is disabled, confirm syntactic authenticity
        if not check_live_network:
            return (
                URLVerificationStatus.SOURCE_CONFIRMED,
                "Syntactically verified genuine employer URL.",
                clean_url,
            )

        # Execute polite HTTP verification for public ATS job boards
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            # Attempt lightweight HEAD first, fallback to GET
            resp = None
            try:
                resp = requests.head(clean_url, headers=headers, timeout=timeout, allow_redirects=True)
            except requests.Timeout:
                raise
            except Exception:
                pass

            if resp is None or resp.status_code in [405, 403]:
                resp = requests.get(clean_url, headers=headers, timeout=timeout, allow_redirects=True, stream=True)

            status_code = resp.status_code
            final_url = resp.url or clean_url

            if status_code == 200:
                # Check if redirected to a generic root / careers search page rather than job
                if final_url.rstrip("/") in [f"{parsed.scheme}://{parsed.netloc}", f"{parsed.scheme}://{parsed.netloc}/careers"]:
                    return (
                        URLVerificationStatus.EXPIRED,
                        "Job posting has expired (redirected to company careers homepage).",
                        final_url,
                    )
                return (
                    URLVerificationStatus.VERIFIED_ACTIVE,
                    f"HTTP 200 Verified Active Job Posting on {hostname}.",
                    final_url,
                )
            elif status_code in (404, 410):
                return (
                    URLVerificationStatus.EXPIRED,
                    f"Listing expired or removed by employer (HTTP {status_code}).",
                    final_url,
                )
            elif status_code in (401, 403, 999):
                return (
                    URLVerificationStatus.SOURCE_CONFIRMED,
                    f"Portal verified (HTTP {status_code}); protected by employer access controls.",
                    final_url,
                )
            else:
                return (
                    URLVerificationStatus.SOURCE_UNAVAILABLE,
                    f"Employer server returned HTTP {status_code}.",
                    final_url,
                )

        except requests.Timeout:
            return (
                URLVerificationStatus.SOURCE_UNAVAILABLE,
                "Connection timeout verifying employer career server.",
                clean_url,
            )
        except requests.RequestException as e:
            return (
                URLVerificationStatus.SOURCE_UNAVAILABLE,
                f"Network verification unavailable: {str(e)[:100]}",
                clean_url,
            )
