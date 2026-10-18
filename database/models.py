"""Data Models and State Machine Enums for Job Applications."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class ApplicationStatus(str, Enum):
    """Canonical 14 Application State Machine Statuses."""
    DISCOVERED = "DISCOVERED"
    QUALIFIED = "QUALIFIED"
    REJECTED = "REJECTED"
    READY_FOR_APPLICATION = "READY_FOR_APPLICATION"
    AWAITING_MANUAL_ACTION = "AWAITING_MANUAL_ACTION"
    SUBMITTED = "SUBMITTED"
    APPLICATION_CONFIRMED = "APPLICATION_CONFIRMED"
    ASSESSMENT_RECEIVED = "ASSESSMENT_RECEIVED"
    INTERVIEW = "INTERVIEW"
    OFFER = "OFFER"
    REJECTED_BY_EMPLOYER = "REJECTED_BY_EMPLOYER"
    WITHDRAWN = "WITHDRAWN"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


# Valid transitions map enforcing strict state progression
VALID_STATE_TRANSITIONS: Dict[ApplicationStatus, List[ApplicationStatus]] = {
    ApplicationStatus.DISCOVERED: [
        ApplicationStatus.QUALIFIED,
        ApplicationStatus.REJECTED,
        ApplicationStatus.FAILED,
        ApplicationStatus.ARCHIVED,
    ],
    ApplicationStatus.QUALIFIED: [
        ApplicationStatus.READY_FOR_APPLICATION,
        ApplicationStatus.AWAITING_MANUAL_ACTION,
        ApplicationStatus.REJECTED,
        ApplicationStatus.FAILED,
    ],
    ApplicationStatus.READY_FOR_APPLICATION: [
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.AWAITING_MANUAL_ACTION,
        ApplicationStatus.FAILED,
        ApplicationStatus.WITHDRAWN,
    ],
    ApplicationStatus.AWAITING_MANUAL_ACTION: [
        ApplicationStatus.READY_FOR_APPLICATION,
        ApplicationStatus.SUBMITTED,
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.FAILED,
    ],
    ApplicationStatus.SUBMITTED: [
        ApplicationStatus.APPLICATION_CONFIRMED,
        ApplicationStatus.ASSESSMENT_RECEIVED,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.REJECTED_BY_EMPLOYER,
        ApplicationStatus.FAILED,
        ApplicationStatus.WITHDRAWN,
    ],
    ApplicationStatus.APPLICATION_CONFIRMED: [
        ApplicationStatus.ASSESSMENT_RECEIVED,
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED_BY_EMPLOYER,
        ApplicationStatus.WITHDRAWN,
    ],
    ApplicationStatus.ASSESSMENT_RECEIVED: [
        ApplicationStatus.INTERVIEW,
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED_BY_EMPLOYER,
        ApplicationStatus.WITHDRAWN,
    ],
    ApplicationStatus.INTERVIEW: [
        ApplicationStatus.INTERVIEW, # Multi-round interviews
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED_BY_EMPLOYER,
        ApplicationStatus.WITHDRAWN,
    ],
    ApplicationStatus.OFFER: [
        ApplicationStatus.WITHDRAWN,
        ApplicationStatus.ARCHIVED,
    ],
    ApplicationStatus.REJECTED: [
        ApplicationStatus.ARCHIVED,
    ],
    ApplicationStatus.REJECTED_BY_EMPLOYER: [
        ApplicationStatus.ARCHIVED,
    ],
    ApplicationStatus.WITHDRAWN: [
        ApplicationStatus.ARCHIVED,
    ],
    ApplicationStatus.FAILED: [
        ApplicationStatus.READY_FOR_APPLICATION,
        ApplicationStatus.AWAITING_MANUAL_ACTION,
        ApplicationStatus.ARCHIVED,
    ],
    ApplicationStatus.ARCHIVED: [],
}


class EmploymentType(str, Enum):
    FULL_TIME = "FULL_TIME"
    INTERNSHIP = "INTERNSHIP"
    TRAINEE = "TRAINEE"
    CONTRACT = "CONTRACT"
    UNKNOWN = "UNKNOWN"


@dataclass
class ApplicationStatusHistory:
    id: Optional[int] = None
    application_id: str = ""
    previous_status: str = ""
    new_status: str = ""
    changed_at_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    reason_or_actor: str = ""


class URLVerificationStatus(str, Enum):
    VERIFIED_ACTIVE = "VERIFIED_ACTIVE"
    SOURCE_CONFIRMED = "SOURCE_CONFIRMED"
    NOT_AUTOMATICALLY_VERIFIABLE = "NOT_AUTOMATICALLY_VERIFIABLE"
    EXPIRED = "EXPIRED"
    INVALID_LINK = "INVALID_LINK"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
    DEMO_ONLY = "DEMO_ONLY"


@dataclass
class Application:
    id: str
    employer: str
    job_title: str
    employment_type: str = EmploymentType.FULL_TIME.value
    job_description_summary: str = ""
    job_url: str = ""
    canonical_url: str = ""
    source_platform: str = ""
    external_job_id: str = ""
    location: str = "Bengaluru, Karnataka, India"
    work_arrangement: str = "On-site"
    posting_date: Optional[str] = None
    discovery_timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    matching_score: int = 0
    matching_explanation_json: str = "{}"
    required_skills_json: str = "[]"
    missing_skills_json: str = "[]"
    selected_resume_version: str = "RESUME_A"
    cover_letter_path: Optional[str] = None
    application_status: str = ApplicationStatus.DISCOVERED.value
    submission_timestamp: Optional[str] = None
    application_reference_number: Optional[str] = None
    manual_action_required_reason: Optional[str] = None
    last_verification_timestamp: Optional[str] = None
    error_log: Optional[str] = None
    recruiter_contact_json: str = "{}"
    is_synthetic: bool = False
    verification_status: str = URLVerificationStatus.SOURCE_CONFIRMED.value
    verification_method: str = "ATS_PUBLIC_API"
    job_availability_status: str = "ACTIVE"
    salary_range: Optional[str] = None
    min_experience_years: float = 0.0
    date_discovered: Optional[str] = None
    date_last_checked: Optional[str] = None

    def get_matching_explanation(self) -> Dict[str, Any]:
        try:
            return json.loads(self.matching_explanation_json)
        except Exception:
            return {}

    def get_required_skills(self) -> List[str]:
        try:
            return json.loads(self.required_skills_json)
        except Exception:
            return []

    def get_missing_skills(self) -> List[str]:
        try:
            return json.loads(self.missing_skills_json)
        except Exception:
            return []
