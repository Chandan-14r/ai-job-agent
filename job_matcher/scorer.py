"""Deterministic 100-Point Job Rubric Scoring Engine with Hard Eligibility Veto."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from candidate_profile.loader import CandidateProfile
from candidate_profile.resume_verifier import get_all_verified_skills
from job_parser.extractor import ParsedJob, JobCategory, EXCLUDED_ROLES_PATTERN


class DecisionBand(str, Enum):
    HIGH_PRIORITY = "HIGH_PRIORITY"   # 85 - 100
    GOOD_MATCH = "GOOD_MATCH"         # 75 - 84
    REVIEW_QUEUE = "REVIEW_QUEUE"     # 60 - 74
    REJECTED = "REJECTED"             # 0 - 59


@dataclass
class MatchScoreResult:
    total_score: int
    decision_band: DecisionBand
    is_vetoed: bool
    veto_reason: Optional[str]
    breakdown: Dict[str, int]
    breakdown_explanations: List[str]
    recommended_resume_version: str  # RESUME_A, RESUME_B, RESUME_C
    required_verified_skills: List[str]
    missing_critical_skills: List[str]

    def to_json(self) -> str:
        return json.dumps({
            "total_score": self.total_score,
            "decision_band": self.decision_band.value,
            "is_vetoed": self.is_vetoed,
            "veto_reason": self.veto_reason,
            "breakdown": self.breakdown,
            "breakdown_explanations": self.breakdown_explanations,
            "recommended_resume_version": self.recommended_resume_version,
            "required_verified_skills": self.required_verified_skills,
            "missing_critical_skills": self.missing_critical_skills,
        }, indent=2)


class JobScorer:
    def __init__(self, profile: CandidateProfile):
        self.profile = profile
        self.verified_skills = get_all_verified_skills(profile)

    def evaluate_job(self, job: ParsedJob) -> MatchScoreResult:
        """
        Evaluate parsed job against Kiran A N's verified profile using
        the 100-point deterministic rubric and hard veto gate.
        """
        breakdown = {
            "technical_skill_alignment": 0,    # Max 35
            "project_relevance": 0,            # Max 20
            "experience_eligibility_fit": 0,   # Max 15
            "location_work_arrangement": 0,    # Max 10
            "posting_recency": 0,              # Max 10
            "career_fit_responsibilities": 0,  # Max 10
        }
        explanations = []

        # --- 1. Hard Eligibility Veto Gate ---
        # A. Role Category Veto
        if job.category == JobCategory.EXCLUDED or EXCLUDED_ROLES_PATTERN.search(job.title):
            return self._build_veto_result(
                f"Hard Veto: Role '{job.title}' is an excluded non-target category (Designer / Manager / Director / Support / Infra / Sales)."
            )

        # Ensure role is relevant to developer / engineering career track
        dev_keywords = [
            "developer", "engineer", "programmer", "full stack", "fullstack", "full-stack",
            "backend", "python", "django", "software", "database", "sql", "trainee", "intern",
            "qa", "automation", "sde", "associate"
        ]
        title_lower = job.title.lower()
        if not any(k in title_lower for k in dev_keywords):
            return self._build_veto_result(
                f"Hard Veto: Role title '{job.title}' does not align with candidate's software developer profile."
            )

        # Strict Seniority Veto for Early-Career Fresher Candidate (Kiran A N: 0-2 Years)
        seniority_patterns = [
            r"\bsenior\b", r"\bsr\.?\b", r"\bsr\s+", r"\blead\b", r"\bprincipal\b", r"\barchitect\b",
            r"\bstaff\b", r"\bmanager\b", r"\bdirector\b", r"\bvp\b", r"\bhead\s+of\b",
            r"\bexpert\b", r"\bspecialist\b", r"\bconsultant\b",
            r"\b[3-9]\s*\+?\s*years?\b", r"\b[3-9]\s*(?:-|to)\s*\d+\s*years?\b",
            r"\b5-12\b", r"\b3-8\b", r"\b4-8\b", r"\b5\+\b", r"\b3\+\b", r"\b4\+\b",
        ]
        for spat in seniority_patterns:
            if re.search(spat, title_lower):
                return self._build_veto_result(
                    f"Hard Veto: Role title '{job.title}' mandates senior/lead experience, exceeding candidate's 2.0-year early-career ceiling."
                )

        # Experience Mention in Description Veto (> 2.0 years)
        jd_lower = job.raw_text.lower()
        senior_exp_match = re.search(r"\b([3-9]|\d{2})\s*\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)\b", jd_lower)
        if senior_exp_match:
            exp_found = senior_exp_match.group(1)
            return self._build_veto_result(
                f"Hard Veto: Job description mandates {exp_found}+ years of experience, exceeding candidate's 0-2 year profile."
            )

        # B. Experience Ceiling Veto (>2.0 years mandatory)
        if job.requires_experience_veto or job.min_experience_years > 2.0:
            return self._build_veto_result(
                f"Hard Veto: Role mandates {job.min_experience_years} years of experience, exceeding the 2.0-year early-career ceiling."
            )

        # C. Scam / Pay-to-Work Veto
        if job.scam_flags:
            return self._build_veto_result(
                f"Hard Veto: Potential fraudulent or fee-demanding opening detected: {', '.join(job.scam_flags)}"
            )

        # D. Critical Exclusions Veto (PL/SQL Stored Procedures, Java, C++, React, etc. if mandatory)
        jd_lower = job.raw_text.lower()
        forbidden_techs = [
            ("pl/sql", "Mandatory PL/SQL is excluded. Candidate demonstrated standard SQL/Oracle SQL queries only."),
            ("stored procedure", "Stored procedures expertise is excluded from verified profile."),
            ("trigger", "Triggers expertise is excluded from verified profile."),
            ("indexing optimization", "Database indexing optimization is excluded from verified profile."),
        ]
        for term, reason in forbidden_techs:
            if re.search(r"\b" + re.escape(term) + r"\b", jd_lower):
                # If term is explicitly listed as a primary/mandatory requirement
                if any(w in jd_lower for w in ["mandatory", "must have", "required", "essential"]):
                    return self._build_veto_result(f"Hard Veto: {reason}")

        # Check for mandatory other languages not in stack
        unverified_languages = ["java", "c++", "golang", "rust", "ruby"]
        for lang in unverified_languages:
            pattern = r"\b" + re.escape(lang) + r"\b"
            if re.search(pattern, jd_lower) and not any(k in jd_lower for k in ["python", "django"]):
                # Role is purely for another programming language
                return self._build_veto_result(f"Hard Veto: Mandatory tech stack '{lang.upper()}' is not in candidate's verified skills.")

        # Check if job title explicitly specifies non-target language without Python
        non_target_title_langs = [
            (r"\bruby\b", "Ruby"),
            (r"\bgolang\b", "Go / Golang"),
            (r"\bgo\b", "Go"),
            (r"\bc\+\+\b", "C++"),
            (r"\bc#\b", "C#"),
            (r"\b\.net\b", ".NET"),
            (r"\bjava\b", "Java"),
            (r"\bphp\b", "PHP"),
            (r"\bswift\b", "Swift"),
            (r"\bkotlin\b", "Kotlin"),
            (r"\brust\b", "Rust"),
        ]
        for pat, lang_name in non_target_title_langs:
            if re.search(pat, title_lower) and not any(k in title_lower for k in ["python", "django"]):
                return self._build_veto_result(
                    f"Hard Veto: Role is dedicated to '{lang_name}', which is not in candidate's verified Python stack."
                )

        # E. Salary Floor Veto (Min 4.0 LPA)
        sal_min = job.min_salary_lpa
        sal_max = job.max_salary_lpa
        if sal_max is None and job.salary_range:
            from job_parser.extractor import JobExtractor
            sal_min, sal_max, _ = JobExtractor.extract_salary(job.salary_range)

        # Unpaid / Zero stipend veto
        sal_str_lower = (job.salary_range or "").lower()
        if "unpaid" in sal_str_lower or "no stipend" in sal_str_lower or "free internship" in sal_str_lower or (sal_max is not None and sal_max == 0.0):
            return self._build_veto_result("Hard Veto: Unpaid or zero-compensation role rejected. Minimum salary floor is 4.0 LPA.")

        if sal_max is not None and sal_max < 4.0:
            return self._build_veto_result(
                f"Hard Veto: Stated salary ({job.salary_range or f'{sal_max} LPA'}) is below candidate's minimum floor of 4.0 LPA."
            )
        elif sal_max is None and sal_min is not None and sal_min < 4.0:
            return self._build_veto_result(
                f"Hard Veto: Stated salary ({job.salary_range or f'{sal_min} LPA'}) is below candidate's minimum floor of 4.0 LPA."
            )

        # F. Strict Location Filter (Bengaluru, Mysuru, or Remote / Work From Home)
        loc_clean = (job.location or "").lower()
        arrangement = (job.work_arrangement or "").lower()

        is_remote = arrangement == "remote" or "remote" in loc_clean or "work from home" in loc_clean or "wfh" in loc_clean
        is_bengaluru = "bengaluru" in loc_clean or "bangalore" in loc_clean
        is_mysuru = "mysuru" in loc_clean or "mysore" in loc_clean

        if not (is_remote or is_bengaluru or is_mysuru):
            return self._build_veto_result(
                f"Hard Veto: Location '{job.location}' ({job.work_arrangement}) is outside candidate's strict locations (Bengaluru, Mysuru, Remote/WFH)."
            )

        # --- 2. Dimension 1: Technical Skill Alignment (Max 35 points) ---
        score_tech, matched_skills, missing_skills = self._score_technical_skills(job)
        breakdown["technical_skill_alignment"] = score_tech
        explanations.append(
            f"Technical Skills Alignment: {score_tech}/35 pts (Matched: {len(matched_skills)} skills; Missing: {len(missing_skills)})"
        )

        # --- 3. Dimension 2: Project Relevance (Max 20 points) ---
        score_proj, proj_note = self._score_project_relevance(job)
        breakdown["project_relevance"] = score_proj
        explanations.append(f"Completed Project Relevance: {score_proj}/20 pts ({proj_note})")

        # --- 4. Dimension 3: Experience & Eligibility Fit (Max 15 points) ---
        score_exp, exp_note = self._score_experience_eligibility(job)
        breakdown["experience_eligibility_fit"] = score_exp
        explanations.append(f"Experience & Eligibility Fit: {score_exp}/15 pts ({exp_note})")

        # --- 5. Dimension 4: Location & Work Arrangement (Max 10 points) ---
        score_loc, loc_note = self._score_location(job)
        breakdown["location_work_arrangement"] = score_loc
        explanations.append(f"Location & Work Arrangement: {score_loc}/10 pts ({loc_note})")

        # --- 6. Dimension 5: Posting Recency (Max 10 points) ---
        score_rec, rec_note = self._score_recency(job)
        breakdown["posting_recency"] = score_rec
        explanations.append(f"Posting Recency: {score_rec}/10 pts ({rec_note})")

        # --- 7. Dimension 6: Responsibilities & Career Fit (Max 10 points) ---
        score_career, career_note = self._score_career_fit(job)
        breakdown["career_fit_responsibilities"] = score_career
        explanations.append(f"Career Growth & Fit: {score_career}/10 pts ({career_note})")

        total_score = sum(breakdown.values())
        decision_band = self._get_decision_band(total_score)
        resume_version = self._select_resume_version(job)

        return MatchScoreResult(
            total_score=total_score,
            decision_band=decision_band,
            is_vetoed=False,
            veto_reason=None,
            breakdown=breakdown,
            breakdown_explanations=explanations,
            recommended_resume_version=resume_version,
            required_verified_skills=matched_skills,
            missing_critical_skills=missing_skills,
        )

    def _score_technical_skills(self, job: ParsedJob) -> Tuple[int, List[str], List[str]]:
        matched = []
        missing = []

        if not job.extracted_skills:
            # Fallback evaluation based on title
            if job.category in [JobCategory.CATEGORY_A, JobCategory.CATEGORY_B]:
                return 25, ["Python", "Django", "SQL"], []
            return 20, ["SQL"], []

        # Core candidate stack
        core_keys = {"Python", "Django", "SQL", "JavaScript", "HTML5", "CSS3", "Git", "REST APIs", "Selenium"}

        for skill in job.extracted_skills:
            if skill in core_keys:
                matched.append(skill)
            else:
                missing.append(skill)

        # Base calculation: percentage of matched skills
        ratio = len(matched) / max(len(job.extracted_skills), 1)
        base_points = int(ratio * 30)

        # Bonus if Python and Django/SQL are specifically present
        if "Python" in matched and ("Django" in matched or "SQL" in matched):
            base_points = min(35, base_points + 5)

        return min(35, max(5, base_points)), matched, missing

    def _score_project_relevance(self, job: ParsedJob) -> Tuple[int, str]:
        # Kiran has Stock Market Analysis (Django/SQL) and Food Delivery (JS Frontend)
        desc_lower = job.raw_text.lower()
        points = 10
        notes = []

        if "django" in desc_lower or "orm" in desc_lower or "backend" in desc_lower or "stock" in desc_lower:
            points += 6
            notes.append("Strong alignment with Stock Market Analysis Django Full Stack project")
        if "javascript" in desc_lower or "frontend" in desc_lower or "ui" in desc_lower:
            points += 4
            notes.append("Alignment with Food Delivery interactive frontend project")

        if not notes:
            notes.append("General full stack / backend web engineering principles apply")

        return min(20, points), "; ".join(notes)

    def _score_experience_eligibility(self, job: ParsedJob) -> Tuple[int, str]:
        # Kiran has 0 professional years, B.E. CSE (CGPA 7.98), Full Stack Training
        if job.is_fresher_eligible or job.min_experience_years == 0.0:
            return 15, "Full points: Fresher / 0 years experience explicitly eligible"
        elif job.min_experience_years <= 1.0:
            return 12, "High fit: 0-1 year experience requirement"
        elif job.min_experience_years <= 2.0:
            return 8, "Acceptable fit: 1-2 years experience requirement"
        return 0, "Outside experience target"

    def _score_location(self, job: ParsedJob) -> Tuple[int, str]:
        if job.work_arrangement == "Remote":
            return 10, "Full points: Remote / Work From Home (India-eligible)"
        loc_clean = job.location.lower()
        if "bengaluru" in loc_clean or "bangalore" in loc_clean:
            return 10, "Full points: Bengaluru primary target location"
        if "mysuru" in loc_clean or "mysore" in loc_clean:
            return 10, "Full points: Mysuru target location"
        return 2, f"Secondary / other city ({job.location}) without verified remote status"

    def _score_recency(self, job: ParsedJob) -> Tuple[int, str]:
        if not job.posting_date:
            return 8, "Recent posting (active listing discovered)"

        try:
            # Parse posting date if in ISO or standard format
            dt = datetime.fromisoformat(job.posting_date.replace("Z", "+00:00"))
            age = (datetime.utcnow() - dt.replace(tzinfo=None)).total_seconds() / 3600.0
            if age <= 48:
                return 10, "Fresh posting (<48 hours)"
            elif age <= 168: # 7 days
                return 8, "Posting within past 7 days"
            elif age <= 720: # 30 days
                return 5, "Posting within past 30 days"
            return 2, "Older posting (>30 days)"
        except Exception:
            return 8, "Active listing"

    def _score_career_fit(self, job: ParsedJob) -> Tuple[int, str]:
        if job.category == JobCategory.CATEGORY_B:
            return 10, "Optimal career progression: Full-Stack Engineering role"
        elif job.category == JobCategory.CATEGORY_A:
            return 10, "Optimal career progression: Python / Backend Engineering role"
        elif job.category == JobCategory.CATEGORY_C:
            return 8, "Target database / SQL development role"
        elif job.category == JobCategory.CATEGORY_D:
            return 7, "Quality entry-level / internship foundation"
        return 4, "General technology role"

    def _get_decision_band(self, score: int) -> DecisionBand:
        if score >= 85:
            return DecisionBand.HIGH_PRIORITY
        elif score >= 75:
            return DecisionBand.GOOD_MATCH
        elif score >= 60:
            return DecisionBand.REVIEW_QUEUE
        return DecisionBand.REJECTED

    def _select_resume_version(self, job: ParsedJob) -> str:
        """Select RESUME_A, RESUME_B, or RESUME_C based on role requirements."""
        if job.category == JobCategory.CATEGORY_C:
            return "RESUME_C"

        if job.category == JobCategory.CATEGORY_B:
            return "RESUME_A"

        if job.category == JobCategory.CATEGORY_A:
            # Check frontend weight in job text
            jd = job.raw_text.lower()
            frontend_keywords = ["html", "css", "javascript", "frontend", "ui", "ux", "templates"]
            frontend_count = sum(1 for kw in frontend_keywords if kw in jd)
            if frontend_count >= 2:
                return "RESUME_A"
            return "RESUME_B"

        return "RESUME_A"

    def _build_veto_result(self, reason: str) -> MatchScoreResult:
        return MatchScoreResult(
            total_score=0,
            decision_band=DecisionBand.REJECTED,
            is_vetoed=True,
            veto_reason=reason,
            breakdown={
                "technical_skill_alignment": 0,
                "project_relevance": 0,
                "experience_eligibility_fit": 0,
                "location_work_arrangement": 0,
                "posting_recency": 0,
                "career_fit_responsibilities": 0,
            },
            breakdown_explanations=[reason],
            recommended_resume_version="RESUME_A",
            required_verified_skills=[],
            missing_critical_skills=[],
        )
