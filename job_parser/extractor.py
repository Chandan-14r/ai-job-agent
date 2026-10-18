"""Job Information Extractor and Categorization Engine."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class JobCategory(str, Enum):
    CATEGORY_A = "CATEGORY_A"  # Python Development / Backend
    CATEGORY_B = "CATEGORY_B"  # Full-Stack Development
    CATEGORY_C = "CATEGORY_C"  # SQL & Database Development
    CATEGORY_D = "CATEGORY_D"  # Related Entry-Level & Internships (or QA Selenium)
    EXCLUDED = "EXCLUDED"      # Unrelated IT Support, BPO, Sales, etc.
    UNKNOWN = "UNKNOWN"


@dataclass
class ParsedJob:
    title: str
    employer: str
    category: JobCategory
    location: str = "Bengaluru, Karnataka, India"
    work_arrangement: str = "On-site"  # On-site, Hybrid, Remote
    employment_type: str = "FULL_TIME"  # FULL_TIME, INTERNSHIP, TRAINEE, CONTRACT
    min_experience_years: float = 0.0
    max_experience_years: Optional[float] = None
    extracted_skills: List[str] = field(default_factory=list)
    missing_skills: List[str] = field(default_factory=list)
    salary_range: Optional[str] = None
    min_salary_lpa: Optional[float] = None
    max_salary_lpa: Optional[float] = None
    posting_date: Optional[str] = None
    job_url: str = ""
    external_job_id: str = ""
    source_platform: str = ""
    summary: str = ""
    raw_text: str = ""
    scam_flags: List[str] = field(default_factory=list)
    is_fresher_eligible: bool = True
    requires_experience_veto: bool = False
    is_synthetic: bool = False
    verification_status: str = "SOURCE_CONFIRMED"


# Regular expressions for experience extraction
EXP_PATTERNS = [
    r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
    r"(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?(?:experience|exp)",
    r"(?:experience|exp)\s*:\s*(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)",
    r"(?:experience|exp)\s*:\s*(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)",
]

# Strict role exclusions (BPO, tech support, telemarketing, data entry, sales, designers, managers, directors, non-target roles)
EXCLUDED_ROLES_PATTERN = re.compile(
    r"\b("
    r"tech(?:nical)?\s+support|helpdesk|desktop\s+support|bpo|kpo|call\s+center|"
    r"customer\s+(?:support|care|service|executive)|telecaller|telesales|sales\s+executive|"
    r"business\s+development|bde|data\s+entry|hardware\s+networking|system\s+administrator|"
    r"ui[/-]?ux|ux[/-]?ui|graphic\s+designer|web\s+designer|creative\s+designer|visual\s+designer|"
    r"product\s+designer|ui\s+designer|ux\s+designer|animator|illustrator|fashion\s+designer|interior\s+designer|"
    r"director|engineering\s+manager|project\s+manager|product\s+manager|program\s+manager|general\s+manager|"
    r"scrum\s+master|team\s+lead|vice\s+president|vp\s+|chief|cto|ceo|head\s+of|"
    r"devops|sre|site\s+reliability|cloud\s+architect|solutions\s+architect|infrastructure\s+engineer|"
    r"field\s+engineer|sales\s+engineer|solutions\s+engineer|incident\s+response|security\s+operations|"
    r"ios\s+developer|android\s+developer|flutter\s+developer|swift\s+developer|embedded\s+engineer|firmware\s+engineer|"
    r"content\s+writer|copywriter|digital\s+marketing|seo\s+executive|recruiter|human\s+resources|hr\s+executive|"
    r"accountant|financial\s+analyst"
    r")\b",
    re.IGNORECASE,
)

# Scam / Pay-to-Work warning patterns
SCAM_PATTERNS = [
    (r"\b(registration\s+fee|training\s+fee|processing\s+fee|security\s+deposit|refundable\s+deposit)\b", "Pay-to-work / Fee demanded"),
    (r"\b(pay\s+(?:rs\.?|inr|usd)\s*\d+)\b", "Upfront payment requested"),
    (r"\b(100%\s+placement\s+fee|pay\s+after\s+placement\s+deposit)\b", "Commercial placement fee indicator"),
    (r"\b(send\s+bank\s+details|send\s+otp|share\s+credit\s+card)\b", "Sensitive banking credentials requested"),
]

# Known skill vocabulary for matching
TECH_SKILLS_MAP = {
    "python": "Python",
    "django": "Django",
    "sql": "SQL",
    "oracle": "Oracle SQL",
    "javascript": "JavaScript",
    "js": "JavaScript",
    "es6": "JavaScript",
    "html": "HTML5",
    "html5": "HTML5",
    "css": "CSS3",
    "css3": "CSS3",
    "git": "Git",
    "github": "GitHub",
    "rest": "REST APIs",
    "restful": "REST APIs",
    "api": "REST APIs",
    "selenium": "Selenium",
    "docker": "Docker",
    "aws": "AWS",
    "react": "React",
    "angular": "Angular",
    "vue": "Vue",
    "node": "Node.js",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "pl/sql": "PL/SQL",
    "plsql": "PL/SQL",
    "stored procedures": "Stored Procedures",
    "triggers": "Triggers",
    "nosql": "NoSQL",
    "mongodb": "MongoDB",
    "java": "Java",
    "c++": "C++",
}


class JobExtractor:
    @staticmethod
    def categorize_job(title: str, description: str = "") -> JobCategory:
        """Categorize job into Category A, B, C, D, or EXCLUDED."""
        clean_title = title.lower().strip()

        # Hard Exclusion Check
        if EXCLUDED_ROLES_PATTERN.search(clean_title):
            return JobCategory.EXCLUDED

        # Category D: Internships / Trainees / QA Automation
        if any(w in clean_title for w in ["intern", "trainee", "get", "graduate trainee", "qa automation", "selenium"]):
            return JobCategory.CATEGORY_D

        # Category B: Full-Stack Development
        if any(w in clean_title for w in ["full stack", "full-stack", "fullstack", "graduate software engineer",
                                          "entry-level software", "entry level software", "associate software developer"]):
            return JobCategory.CATEGORY_B

        # Category C: SQL & Database Development
        if any(w in clean_title for w in ["sql developer", "database developer", "database application", "oracle sql"]):
            return JobCategory.CATEGORY_C

        # Category A: Python Development
        if any(w in clean_title for w in ["python", "django", "backend"]):
            return JobCategory.CATEGORY_A

        # Fallback check on description
        if "django" in description.lower() or "python" in description.lower():
            return JobCategory.CATEGORY_A

        return JobCategory.UNKNOWN

    @staticmethod
    def extract_experience_range(text: str) -> Tuple[float, Optional[float], bool]:
        """
        Extract min and max experience in years from job text.
        Returns: (min_years, max_years, is_fresher_eligible)
        """
        clean = text.lower()
        # Fresher indicators
        fresher_flag = bool(re.search(
            r"\b(fresher|freshers|0\s*years?|entry\s*level|graduate|2024\s*batch|2025\s*batch|2026\s*batch|no\s*experience)\b",
            clean
        ))

        for pattern in EXP_PATTERNS:
            match = re.search(pattern, clean)
            if match:
                groups = match.groups()
                if len(groups) == 2 and groups[1] is not None:
                    min_exp = float(groups[0])
                    max_exp = float(groups[1])
                    return min_exp, max_exp, (min_exp == 0 or fresher_flag)
                elif len(groups) >= 1:
                    exp_val = float(groups[0])
                    return exp_val, None, (exp_val == 0 or fresher_flag)

        if fresher_flag:
            return 0.0, 1.0, True

        return 0.0, None, True

    @staticmethod
    def detect_scams(text: str) -> List[str]:
        """Detect any fraudulent, fee-demanding, or pay-to-work terms."""
        flags = []
        for pattern, explanation in SCAM_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                flags.append(explanation)
        return flags

    @staticmethod
    def extract_work_arrangement(text: str, location_str: str = "") -> Tuple[str, str]:
        """Determine location and work arrangement (On-site, Hybrid, Remote)."""
        loc_input = (location_str or "").strip().lower()
        text_lower = (text or "").lower()
        combined = f"{loc_input} {text_lower}"

        arrangement = "On-site"
        if "remote" in combined or "work from home" in combined or "wfh" in combined:
            arrangement = "Remote"
        elif "hybrid" in combined:
            arrangement = "Hybrid"

        # Determine location: prioritize explicit location_str over body text
        target = loc_input if loc_input else text_lower

        if "bengaluru" in target or "bangalore" in target:
            loc = "Bengaluru, Karnataka, India"
        elif "mysuru" in target or "mysore" in target:
            loc = "Mysuru, Karnataka, India"
        elif "hyderabad" in target:
            loc = "Hyderabad, Telangana, India"
        elif "pune" in target:
            loc = "Pune, Maharashtra, India"
        elif "chennai" in target:
            loc = "Chennai, Tamil Nadu, India"
        elif "mumbai" in target:
            loc = "Mumbai, Maharashtra, India"
        elif any(c in target for c in ["delhi", "noida", "gurgaon", "gurugram"]):
            loc = "NCR, India"
        elif "kolkata" in target:
            loc = "Kolkata, West Bengal, India"
        elif "ahmedabad" in target:
            loc = "Ahmedabad, Gujarat, India"
        elif "kochi" in target or "cochin" in target or "kerala" in target:
            loc = "Kochi, Kerala, India"
        elif arrangement == "Remote":
            loc = "Remote (India)"
        elif location_str.strip():
            loc = location_str.strip()
        else:
            loc = "Bengaluru, Karnataka, India"

        return loc, arrangement

    @staticmethod
    def extract_skills(text: str) -> List[str]:
        """Extract detected technical skills from job text."""
        normalized = text.lower()
        detected: Set[str] = set()
        for key, clean_name in TECH_SKILLS_MAP.items():
            pattern = r"\b" + re.escape(key) + r"\b"
            if re.search(pattern, normalized):
                detected.add(clean_name)
        return sorted(list(detected))

    @staticmethod
    def extract_salary(text: str, salary_raw: str = "") -> Tuple[Optional[float], Optional[float], Optional[str]]:
        """
        Extract min and max salary in LPA (Lakhs Per Annum) from salary string or job text.
        Handles:
          - LPA / Lakhs ranges: "3.5 - 5.5 LPA", "4 LPA - 6 LPA", "4.5 Lakhs to 7 Lakhs", "4L - 6L"
          - Single LPA figures: "5 LPA", "4.5 Lakhs", "6 Lacs P.A."
          - Monthly notations: "₹ 35,000 - ₹ 50,000 / month", "₹ 40,000 per month" (converted to annual LPA * 12)
          - Annual Rupee notations: "₹ 2,50,000 - ₹ 3,50,000 P.A.", "₹ 5,00,000 P.A."
        Returns: (min_salary_lpa, max_salary_lpa, normalized_salary_range_str)
        """
        combined = f"{salary_raw} {text}".strip()
        if not combined:
            return None, None, None

        # Pattern 1: LPA / Lakhs Range, e.g. "3 - 5 LPA", "3.5 LPA - 5.5 LPA", "4 to 6.5 Lakhs", "4L - 6L"
        lpa_range = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lac|lacs|l\b)?\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lac|lacs|l\b)",
            combined,
            re.IGNORECASE,
        )
        if lpa_range:
            min_lpa = float(lpa_range.group(1))
            max_lpa = float(lpa_range.group(2))
            return min_lpa, max_lpa, f"{min_lpa} - {max_lpa} LPA"

        # Pattern 2: Single LPA / Lakhs figure, e.g. "5 LPA", "4.5 Lakhs", "6 Lacs"
        single_lpa = re.search(
            r"(?:rs\.?|inr|₹)?\s*(\d+(?:\.\d+)?)\s*(?:lpa|lakhs?|lac|lacs|l\b)(?:\s*(?:p\.?a\.?|per\s+annum|annually))?",
            combined,
            re.IGNORECASE,
        )
        if single_lpa:
            val = float(single_lpa.group(1))
            return val, val, f"{val} LPA"

        # Pattern 3: Monthly Rupee Range / Single (e.g. "₹ 25,000 - 35,000 / month", "₹ 40,000 per month", "30000 pm")
        monthly_range = re.search(
            r"(?:rs\.?|inr|₹)?\s*(\d[\d,]{3,6})\s*(?:-|to)\s*(?:rs\.?|inr|₹)?\s*(\d[\d,]{3,6})\s*(?:/\s*month|per\s+month|p\.?m\.?|/mo\b|pm\b)",
            combined,
            re.IGNORECASE,
        )
        if monthly_range:
            try:
                m1 = float(monthly_range.group(1).replace(",", ""))
                m2 = float(monthly_range.group(2).replace(",", ""))
                min_lpa = round((m1 * 12) / 100000.0, 2)
                max_lpa = round((m2 * 12) / 100000.0, 2)
                return min_lpa, max_lpa, f"{min_lpa} - {max_lpa} LPA"
            except Exception:
                pass

        monthly_single = re.search(
            r"(?:rs\.?|inr|₹)\s*(\d[\d,]{3,6})\s*(?:/\s*month|per\s+month|p\.?m\.?|/mo\b|pm\b)",
            combined,
            re.IGNORECASE,
        )
        if monthly_single:
            try:
                m = float(monthly_single.group(1).replace(",", ""))
                val_lpa = round((m * 12) / 100000.0, 2)
                return val_lpa, val_lpa, f"{val_lpa} LPA"
            except Exception:
                pass

        # Pattern 4: Annual Rupee notation, e.g. "₹ 3,50,000 - ₹ 5,50,000" or "350000 - 550000"
        rupee_range = re.search(
            r"(?:rs\.?|inr|₹)?\s*(\d[\d,]{4,})\s*(?:-|to)\s*(?:rs\.?|inr|₹)?\s*(\d[\d,]{4,})",
            combined,
            re.IGNORECASE,
        )
        if rupee_range:
            try:
                v1 = float(rupee_range.group(1).replace(",", ""))
                v2 = float(rupee_range.group(2).replace(",", ""))
                if v1 >= 100000:
                    min_lpa = round(v1 / 100000.0, 2)
                    max_lpa = round(v2 / 100000.0, 2)
                    return min_lpa, max_lpa, f"{min_lpa} - {max_lpa} LPA"
            except Exception:
                pass

        single_rupee = re.search(
            r"(?:rs\.?|inr|₹)\s*(\d[\d,]{4,})\s*(?:p\.?a\.?|per\s+annum|annually)?",
            combined,
            re.IGNORECASE,
        )
        if single_rupee:
            try:
                v = float(single_rupee.group(1).replace(",", ""))
                if v >= 100000:
                    val_lpa = round(v / 100000.0, 2)
                    return val_lpa, val_lpa, f"{val_lpa} LPA"
            except Exception:
                pass

        if salary_raw and salary_raw.lower() not in ["not disclosed", "confidential", "competitive", "best in industry"]:
            return None, None, salary_raw.strip()

        return None, None, None

    @classmethod
    def parse_job(
        cls,
        title: str,
        employer: str,
        description: str,
        job_url: str = "",
        external_job_id: str = "",
        source_platform: str = "",
        posting_date: Optional[str] = None,
        location_raw: str = "",
        salary_raw: str = "",
        is_synthetic: bool = False,
        verification_status: Optional[str] = None,
    ) -> ParsedJob:
        full_text = f"{title}\n{employer}\n{description}"
        category = cls.categorize_job(title, description)
        min_exp, max_exp, fresher_eligible = cls.extract_experience_range(description)
        scams = cls.detect_scams(full_text)
        location, arrangement = cls.extract_work_arrangement(description, location_raw)
        skills = cls.extract_skills(full_text)
        min_sal, max_sal, sal_range = cls.extract_salary(description, salary_raw)

        # Experience veto: If minimum experience required is strictly greater than 2 years
        requires_exp_veto = (min_exp > 2.0)

        # Determine employment type
        emp_type = "FULL_TIME"
        clean_title = title.lower()
        if "intern" in clean_title:
            emp_type = "INTERNSHIP"
        elif "trainee" in clean_title:
            emp_type = "TRAINEE"
        elif "contract" in clean_title or "freelance" in clean_title:
            emp_type = "CONTRACT"

        # Brief summary
        summary = description[:300].strip() + ("..." if len(description) > 300 else "")

        # Default verification status
        v_status = verification_status or ("DEMO_ONLY" if is_synthetic else "SOURCE_CONFIRMED")

        return ParsedJob(
            title=title.strip(),
            employer=employer.strip(),
            category=category,
            location=location,
            work_arrangement=arrangement,
            employment_type=emp_type,
            min_experience_years=min_exp,
            max_experience_years=max_exp,
            extracted_skills=skills,
            salary_range=sal_range,
            min_salary_lpa=min_sal,
            max_salary_lpa=max_sal,
            posting_date=posting_date,
            job_url=job_url,
            external_job_id=external_job_id,
            source_platform=source_platform,
            summary=summary,
            raw_text=description,
            scam_flags=scams,
            is_fresher_eligible=fresher_eligible,
            requires_experience_veto=requires_exp_veto,
            is_synthetic=is_synthetic,
            verification_status=v_status,
        )
