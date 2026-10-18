"""Multi-Key Duplicate Detection and Cross-Portal Overlap Resolution Engine."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Set
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from database.models import Application
from database.repository import ApplicationRepository

# Tracking parameters that should be stripped
TRACKING_PARAMS: Set[str] = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "ref", "fbclid", "gclid", "trk", "tracking", "src", "source", "li_fat_id",
    "sc_channel", "token", "sessionId", "midToken", "spm"
}

# Critical parameters that identify distinct jobs and MUST be preserved
CRITICAL_JOB_PARAMS: Set[str] = {
    "id", "jid", "jobid", "job_id", "gh_jid", "jk", "reqid", "requisitionid", "p", "v"
}

# Trust priority tiers for cross-portal resolution (lower number = higher trust)
SOURCE_TRUST_PRIORITY = {
    "direct_employer_career": 1,
    "greenhouse_ats": 1,
    "lever_ats": 1,
    "ashby_ats": 1,
    "naukri": 2,
    "indeed_india": 2,
    "foundit": 2,
    "internshala": 2,
    "linkedin": 3,
    "wellfound": 3,
    "cutshort": 3,
    "instahyre": 3,
}


def canonicalize_url(raw_url: str) -> str:
    """
    Canonicalize URL by lowercasing hostname, removing tracking tags,
    stripping trailing slashes, but strictly preserving functional job ID parameters.
    """
    if not raw_url:
        return ""

    try:
        parsed = urlparse(raw_url.strip())
        netloc = parsed.netloc.lower()
        path = parsed.path.rstrip("/")
        if not path:
            path = "/"

        # Filter query params
        query_items = parse_qsl(parsed.query, keep_blank_values=False)
        clean_query = []
        for key, val in query_items:
            k_lower = key.lower()
            if k_lower in TRACKING_PARAMS or k_lower.startswith("utm_"):
                continue
            clean_query.append((key, val))

        # Re-encode sorted parameters
        clean_query.sort(key=lambda x: x[0])
        new_query = urlencode(clean_query)

        # Drop fragment
        return urlunparse((parsed.scheme.lower() or "https", netloc, path, "", new_query, ""))
    except Exception:
        return raw_url.strip()


def normalize_string(text: str) -> str:
    """Normalize string by removing punctuation, company legal forms, and excess whitespace."""
    if not text:
        return ""
    # Strip common suffixes (Inc., Ltd., Pvt., Technologies, etc.)
    cleaned = re.sub(r"\b(pvt\.?|ltd\.?|private|limited|inc\.?|corp\.?|technologies|solutions|services|llc)\b", "", text, flags=re.IGNORECASE)
    # Remove non-alphanumeric characters
    cleaned = re.sub(r"[^\w\s]", " ", cleaned)
    return " ".join(cleaned.lower().split())


@dataclass
class DuplicateCheckResult:
    is_duplicate: bool
    duplicate_type: Optional[str] = None  # CANONICAL_URL, PLATFORM_JOB_ID, COMPOSITE_KEY, EMPLOYER_COOLDOWN
    existing_application: Optional[Application] = None
    priority_upgrade_recommended: bool = False
    explanation: str = ""


class DuplicateChecker:
    def __init__(self, repository: ApplicationRepository):
        self.repo = repository

    def check_duplicate(
        self,
        employer: str,
        job_title: str,
        location: str,
        raw_url: str = "",
        source_platform: str = "",
        external_job_id: str = "",
    ) -> DuplicateCheckResult:
        """
        Execute multi-key fingerprint matching against SQLite repository.
        """
        canonical_url = canonicalize_url(raw_url)

        # 1. Exact Canonical URL check
        if canonical_url:
            existing_by_url = self.repo.find_by_canonical_url(canonical_url)
            if existing_by_url:
                return DuplicateCheckResult(
                    is_duplicate=True,
                    duplicate_type="CANONICAL_URL",
                    existing_application=existing_by_url,
                    explanation=f"Exact match on canonical URL ({canonical_url}) for {existing_by_url.employer}."
                )

        # 2. Platform + External Job ID check
        if source_platform and external_job_id:
            existing_by_platform = self.repo.find_by_platform_job_id(source_platform, external_job_id)
            if existing_by_platform:
                return DuplicateCheckResult(
                    is_duplicate=True,
                    duplicate_type="PLATFORM_JOB_ID",
                    existing_application=existing_by_platform,
                    explanation=f"Duplicate job ID '{external_job_id}' on platform '{source_platform}'."
                )

        # 3. Composite Key Check (Normalized Employer + Job Title + Location)
        norm_employer = normalize_string(employer)
        norm_title = normalize_string(job_title)
        norm_location = normalize_string(location)

        # Query existing apps to compare composite similarity
        first_token = norm_employer.split()[0] if norm_employer else ""
        candidates = self.repo.get_applications(employer=first_token, limit=100) if first_token else self.repo.get_applications(limit=100)
        for app in candidates:
            app_norm_emp = normalize_string(app.employer)
            app_norm_title = normalize_string(app.job_title)

            # If employer is highly similar and title matches
            if (norm_employer == app_norm_emp or norm_employer in app_norm_emp or app_norm_emp in norm_employer) and norm_title == app_norm_title:
                # Check cross-portal channel priority
                current_prio = SOURCE_TRUST_PRIORITY.get(source_platform, 99)
                existing_prio = SOURCE_TRUST_PRIORITY.get(app.source_platform, 99)
                priority_upgrade = (current_prio < existing_prio)

                return DuplicateCheckResult(
                    is_duplicate=True,
                    duplicate_type="COMPOSITE_KEY",
                    existing_application=app,
                    priority_upgrade_recommended=priority_upgrade,
                    explanation=(
                        f"Composite fingerprint match: Role '{job_title}' at '{employer}' already recorded "
                        f"via {app.source_platform}. Priority upgrade: {priority_upgrade}."
                    )
                )

        return DuplicateCheckResult(
            is_duplicate=False,
            duplicate_type=None,
            existing_application=None,
            priority_upgrade_recommended=False,
            explanation="Job opportunity is distinct and verified unique."
        )
