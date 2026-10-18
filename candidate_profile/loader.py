"""Candidate Profile Loader with Zero-Fabrication Validation."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from dotenv import load_dotenv

# Load any .env variables if present
load_dotenv()

# The 13 Never-Guess Fields
NEVER_GUESS_FIELDS = [
    "email",
    "phone",
    "date_of_birth",
    "graduation_year",
    "internship_dates",
    "expected_salary",
    "notice_period",
    "current_employment_status",
    "work_authorization",
    "relocation_willingness",
    "years_of_experience",
    "legal_declarations",
    "sensitive_personal_data",
]


@dataclass
class ContactInfo:
    email: Optional[str] = None
    phone: Optional[str] = None
    current_location: str = "Bengaluru, Karnataka, India"
    postal_code: Optional[str] = None


@dataclass
class CandidateLinks:
    github: str = "https://github.com/kiranan2004-lgtm"
    linkedin: str = "https://www.linkedin.com/in/kiran-an-6a365137/"
    portfolio: str = "https://kiran2004portfolio.netlify.app/"


@dataclass
class EducationItem:
    degree: str
    institution: str
    cgpa: Optional[float] = 0.0
    percentage: Optional[str] = None
    graduation_year: Optional[int] = None
    status: str = "Completed / Final Year"


@dataclass
class TrainingItem:
    title: str
    institute: str
    location: str
    duration: str
    status: str
    modules: List[str] = field(default_factory=list)


@dataclass
class InternshipItem:
    organization: str
    role_title: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    responsibilities: List[str] = field(default_factory=list)
    verified_status: bool = False


@dataclass
class ProjectItem:
    id: str
    title: str
    stack: List[str]
    features: List[str]
    relevance: Dict[str, int] = field(default_factory=dict)


@dataclass
class CandidateProfile:
    full_name: str
    contact: ContactInfo
    links: CandidateLinks
    headline: str
    tier: str
    bio: str
    education: List[EducationItem]
    training: List[TrainingItem]
    internships: List[InternshipItem]
    skills: Dict[str, List[str]]
    exclusions_and_guardrails: Dict[str, Any]
    projects: List[ProjectItem]
    raw_data: Dict[str, Any] = field(default_factory=dict)

    def is_field_missing(self, field_name: str) -> bool:
        """Check if a specific critical field is missing or unverified."""
        if field_name == "email":
            return not bool(self.contact.email)
        elif field_name == "phone":
            return not bool(self.contact.phone)
        elif field_name == "graduation_year":
            return any(edu.graduation_year is None for edu in self.education)
        elif field_name == "internship_dates":
            return any(not intern.verified_status or not intern.start_date for intern in self.internships)
        elif field_name in ["expected_salary", "notice_period", "current_employment_status",
                            "work_authorization", "relocation_willingness", "years_of_experience",
                            "legal_declarations", "sensitive_personal_data", "date_of_birth"]:
            return True  # Defaults to unknown without explicit runtime candidate input
        return False


def get_default_config_path() -> Path:
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "config" / "candidate_profile.yaml"


def load_candidate_profile(config_path: Optional[Path | str] = None) -> CandidateProfile:
    """Load and parse the verified candidate profile from YAML with environment overrides."""
    path = Path(config_path) if config_path else get_default_config_path()
    if not path.exists():
        raise FileNotFoundError(f"Candidate profile configuration not found at {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    cand_data = data.get("candidate", {})
    contact_data = cand_data.get("contact", {})
    links_data = cand_data.get("links", {})
    summary_data = data.get("summary", {})

    # Check environment variable overrides for sensitive contact items
    env_email = os.getenv("CANDIDATE_EMAIL")
    env_phone = os.getenv("CANDIDATE_PHONE")

    contact = ContactInfo(
        email=env_email if env_email else contact_data.get("email"),
        phone=env_phone if env_phone else contact_data.get("phone"),
        current_location=contact_data.get("current_location", "Bengaluru, Karnataka, India"),
        postal_code=contact_data.get("postal_code"),
    )

    links = CandidateLinks(
        github=links_data.get("github", "https://github.com/kiranan2004-lgtm"),
        linkedin=links_data.get("linkedin", "https://www.linkedin.com/in/kiran-an-6a365137/"),
        portfolio=links_data.get("portfolio", "https://kiran2004portfolio.netlify.app/"),
    )

    education = [
        EducationItem(
            degree=e.get("degree", ""),
            institution=e.get("institution", ""),
            cgpa=float(e.get("cgpa")) if e.get("cgpa") is not None else None,
            percentage=e.get("percentage"),
            graduation_year=e.get("graduation_year"),
            status=e.get("status", "Completed / Final Year"),
        )
        for e in data.get("education", [])
    ]

    training = [
        TrainingItem(
            title=t.get("title", ""),
            institute=t.get("institute", ""),
            location=t.get("location", ""),
            duration=t.get("duration", ""),
            status=t.get("status", ""),
            modules=t.get("modules", []),
        )
        for t in data.get("training", [])
    ]

    internships = [
        InternshipItem(
            organization=i.get("organization", ""),
            role_title=i.get("role_title"),
            start_date=i.get("start_date"),
            end_date=i.get("end_date"),
            responsibilities=i.get("responsibilities", []),
            verified_status=bool(i.get("verified_status", False)),
        )
        for i in data.get("internships", [])
    ]

    projects = [
        ProjectItem(
            id=p.get("id", ""),
            title=p.get("title", ""),
            stack=p.get("stack", []),
            features=p.get("features", []),
            relevance=p.get("relevance", {}),
        )
        for p in data.get("projects", [])
    ]

    return CandidateProfile(
        full_name=cand_data.get("full_name", "Kiran A N"),
        contact=contact,
        links=links,
        headline=summary_data.get("headline", "Entry-Level Python Full Stack Developer"),
        tier=summary_data.get("tier", "Fresher / Early-Career Developer (0-2 Years)"),
        bio=summary_data.get("bio", ""),
        education=education,
        training=training,
        internships=internships,
        skills=data.get("skills", {}),
        exclusions_and_guardrails=data.get("exclusions_and_guardrails", {}),
        projects=projects,
        raw_data=data,
    )


def get_missing_candidate_fields(profile: CandidateProfile) -> List[Dict[str, str]]:
    """Return explicit list of missing candidate fields with reasons."""
    missing = []
    if not profile.contact.email:
        missing.append({"field": "email", "reason": "Candidate professional email address is not configured."})
    if not profile.contact.phone:
        missing.append({"field": "phone", "reason": "Candidate phone number is not configured."})

    for edu in profile.education:
        if ("B.E." in edu.degree or "Bachelor" in edu.degree) and edu.graduation_year is None:
            missing.append({
                "field": f"graduation_year ({edu.institution})",
                "reason": "Graduation year requires candidate confirmation.",
            })

    for intern in profile.internships:
        if not intern.verified_status or not intern.role_title:
            missing.append({
                "field": f"internship_details ({intern.organization})",
                "reason": "Exact role title and responsibilities must be verified before claiming on ATS resumes.",
            })

    return missing
