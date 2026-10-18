"""Candidate Profile Verifier & Guardrail Enforcement Engine."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Set
from .loader import CandidateProfile


@dataclass
class ProfileVerificationResult:
    is_valid: bool
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    verified_skills: Set[str] = field(default_factory=set)


def get_all_verified_skills(profile: CandidateProfile) -> Set[str]:
    """Compile a flattened set of all verified skills in lowercase."""
    verified = set()
    for category, skill_list in profile.skills.items():
        for skill in skill_list:
            verified.add(skill.lower().strip())
    # Add common shorthand representations
    if "python" in verified:
        verified.update(["py", "python 3", "python3", "core python"])
    if "javascript" in verified:
        verified.update(["js", "ecmascript", "es6", "es6+"])
    if "sql" in verified:
        verified.update(["relational database", "rdbms", "oracle sql"])
    if "django" in verified:
        verified.update(["django orm", "django mvt"])
    if "html5" in verified:
        verified.update(["html", "semantic html"])
    if "css3" in verified:
        verified.update(["css", "flexbox", "grid", "css grid"])
    return verified


def verify_profile_against_guardrails(profile: CandidateProfile, text_to_check: str = "") -> ProfileVerificationResult:
    """
    Ensure no forbidden technologies, unverified claims, or fabricated experience exist
    in generated resume text or application form fields.
    """
    violations = []
    warnings = []
    verified_skills = get_all_verified_skills(profile)

    exclusions = profile.exclusions_and_guardrails
    forbidden_languages = exclusions.get("strictly_excluded_languages", ["Java", "C++", "Go", "Rust", "TypeScript"])
    forbidden_backend = exclusions.get("strictly_excluded_backend", ["FastAPI", "Flask", "Celery", "Microservices"])
    forbidden_frontend = exclusions.get("strictly_excluded_frontend", ["React", "Angular", "Vue"])
    forbidden_db = exclusions.get("strictly_excluded_database", [
        "PL/SQL", "Stored Procedures", "Triggers", "Database Indexing Optimization", "NoSQL", "MongoDB"
    ])

    all_forbidden = []
    all_forbidden.extend([(tech, "Programming Language") for tech in forbidden_languages])
    all_forbidden.extend([(tech, "Backend Tech") for tech in forbidden_backend])
    all_forbidden.extend([(tech, "Frontend Framework") for tech in forbidden_frontend])
    all_forbidden.extend([(tech, "Advanced/Unverified DB Tech") for tech in forbidden_db])

    if text_to_check:
        normalized_text = " " + text_to_check.lower() + " "
        for tech, category in all_forbidden:
            # Word boundary regex check
            pattern = r"\b" + re.escape(tech.lower()) + r"\b"
            if re.search(pattern, normalized_text):
                violations.append(
                    f"CRITICAL VIOLATION: Forbidden claim '{tech}' ({category}) found in candidate materials. "
                    "Kiran A N's verified profile strictly excludes this technology."
                )

    # Check internships verification
    for intern in profile.internships:
        if not intern.verified_status:
            warnings.append(
                f"Internship at '{intern.organization}' has unverified status and missing dates/role. "
                "Must be excluded from resume generation until confirmed."
            )

    return ProfileVerificationResult(
        is_valid=len(violations) == 0,
        violations=violations,
        warnings=warnings,
        verified_skills=verified_skills,
    )
