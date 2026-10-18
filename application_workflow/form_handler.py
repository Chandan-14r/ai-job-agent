"""Application Form Handler enforcing Zero-Guessing and Halt & Notify Protocols."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from candidate_profile.loader import CandidateProfile, NEVER_GUESS_FIELDS


@dataclass
class FormValidationResult:
    can_auto_submit: bool
    halt_reason: Optional[str] = None
    missing_fields: List[str] = field(default_factory=list)
    populated_fields: Dict[str, Any] = field(default_factory=dict)
    candidate_next_step: Optional[str] = None


class ApplicationFormHandler:
    def __init__(self, profile: CandidateProfile):
        self.profile = profile

    def prepare_and_validate_form(
        self,
        required_form_fields: Optional[List[str]] = None,
        contains_captcha: bool = False,
        contains_otp: bool = False,
        requires_legal_attestation: bool = False,
        portal_manual_only: bool = False,
    ) -> FormValidationResult:
        """
        Validate application form against Kiran A N's verified profile data.
        Enforces Zero-Guessing: immediately halts if any mandatory unknown item is requested.
        """
        if portal_manual_only:
            return FormValidationResult(
                can_auto_submit=False,
                halt_reason="PLATFORM_MANUAL_ONLY",
                candidate_next_step="This platform restricts automated submissions. Please submit directly via the prepared link using your tailored resume."
            )

        if contains_captcha:
            return FormValidationResult(
                can_auto_submit=False,
                halt_reason="CAPTCHA_DETECTED",
                candidate_next_step="A CAPTCHA/bot challenge was detected on the portal. Please complete the verification challenge manually."
            )

        if contains_otp:
            return FormValidationResult(
                can_auto_submit=False,
                halt_reason="OTP_VERIFICATION_REQUIRED",
                candidate_next_step="A one-time SMS/Email OTP verification prompt was encountered. Complete authentication manually."
            )

        if requires_legal_attestation:
            return FormValidationResult(
                can_auto_submit=False,
                halt_reason="LEGAL_DECLARATION_REVIEW",
                candidate_next_step="The application contains legal declarations or background attestations requiring candidate personal review."
            )

        # Baseline mandatory fields for any job application
        req_fields = required_form_fields or ["full_name", "email", "phone"]
        missing = []
        populated = {}

        # 1. Full Name
        populated["full_name"] = self.profile.full_name

        # 2. Email Address
        if not self.profile.contact.email:
            missing.append("email")
        else:
            populated["email"] = self.profile.contact.email

        # 3. Phone Number
        if not self.profile.contact.phone:
            missing.append("phone")
        else:
            populated["phone"] = self.profile.contact.phone

        # 4. Links
        populated["github"] = self.profile.links.github
        populated["linkedin"] = self.profile.links.linkedin
        populated["portfolio"] = self.profile.links.portfolio

        # 5. Location
        populated["location"] = self.profile.contact.current_location

        # Check requested fields against the 13 Never-Guess items
        for f in req_fields:
            clean_f = f.lower().strip()
            if "salary" in clean_f or "ctc" in clean_f:
                missing.append("expected_salary")
            elif "notice" in clean_f:
                missing.append("notice_period")
            elif "relocate" in clean_f:
                missing.append("relocation_willingness")
            elif "dob" in clean_f or "birth" in clean_f:
                missing.append("date_of_birth")
            elif "graduation" in clean_f and any(e.graduation_year is None for e in self.profile.education):
                missing.append("graduation_year")

        if missing:
            unique_missing = list(set(missing))
            halt_reason = f"MISSING_MANDATORY_FIELDS: {', '.join(unique_missing)}"
            next_step = (
                f"Candidate input required for: {', '.join(unique_missing)}. "
                "Update config/candidate_profile.yaml or complete this application manually."
            )
            return FormValidationResult(
                can_auto_submit=False,
                halt_reason=halt_reason,
                missing_fields=unique_missing,
                populated_fields=populated,
                candidate_next_step=next_step,
            )

        return FormValidationResult(
            can_auto_submit=True,
            halt_reason=None,
            missing_fields=[],
            populated_fields=populated,
            candidate_next_step=None,
        )
