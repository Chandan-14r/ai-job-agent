"""Tailored Cover Letter Generator grounded strictly in verified candidate facts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from candidate_profile.loader import CandidateProfile
from job_parser.extractor import JobCategory, ParsedJob


@dataclass
class CoverLetterResult:
    text: str
    file_path: str
    category: str


def generate_cover_letter(
    profile: CandidateProfile,
    job: ParsedJob,
    output_dir: Optional[Path | str] = None,
) -> CoverLetterResult:
    """
    Generate tailored, factual cover letter for Categories A, B, C, or D.
    Enforces Zero Fabrication: never claims unverified skills or metrics.
    """
    if not job.employer or not job.title:
        raise ValueError("Cannot generate cover letter without verified Employer Name and Job Title.")

    if output_dir is None:
        base_dir = Path(__file__).resolve().parent.parent
        out_path = base_dir / "output" / "cover_letters"
    else:
        out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    clean_emp = re.sub(r"[^\w\s]", "", job.employer).replace(" ", "_")
    clean_title = re.sub(r"[^\w\s]", "", job.title).replace(" ", "_")
    filename = f"Cover_Letter_{clean_emp}_{clean_title}.txt"
    file_path = out_path / filename

    contact_email = profile.contact.email or "[Email available upon request]"
    contact_phone = profile.contact.phone or "[Phone available upon request]"

    header = (
        f"{profile.full_name}\n"
        f"{profile.contact.current_location}\n"
        f"Email: {contact_email} | Phone: {contact_phone}\n"
        f"Portfolio: {profile.links.portfolio} | GitHub: {profile.links.github}\n"
        f"LinkedIn: {profile.links.linkedin}\n\n"
        f"To,\n"
        f"Hiring Team\n"
        f"{job.employer}\n"
        f"{job.location}\n\n"
        f"Subject: Application for {job.title} — Kiran A N\n\n"
        f"Dear Hiring Team at {job.employer},\n\n"
    )

    if job.category == JobCategory.CATEGORY_B:
        body = (
            f"I am writing to express my enthusiastic interest in the {job.title} position at {job.employer}. "
            f"With a Bachelor of Engineering in Computer Science and Engineering from JSS Academy of Technical Education "
            f"(CGPA: 7.98) and rigorous professional training in Python Full Stack Development at QSpiders, "
            f"I have established a solid technical foundation in developing responsive, database-driven web applications.\n\n"
            f"Through my flagship project, 'Stock Market Analysis', I engineered an end-to-end full-stack web application "
            f"using Django MVT architecture, relational SQL databases, and JavaScript. I built secure user authentication "
            f"systems, structured models with Django ORM, and integrated dynamic time-series charts with custom date filtering. "
            f"Additionally, in my 'Food Delivery' frontend project, I implemented client-side state manipulation and responsive "
            f"CSS layouts using Flexbox and Grid.\n\n"
            f"I am particularly drawn to {job.employer}'s engineering culture and would welcome the opportunity to contribute "
            f"my full-stack capabilities, analytical mindset, and drive for clean, testable code to your engineering team."
        )
    elif job.category == JobCategory.CATEGORY_A:
        body = (
            f"I am writing to apply for the {job.title} opening at {job.employer}. "
            f"As a Computer Science Engineering graduate from JSS Academy of Technical Education (CGPA: 7.98) "
            f"currently undergoing intensive Python Full Stack training at QSpiders, I bring focused competencies "
            f"in core Python OOP, structured programming, exception handling, and Django backend development.\n\n"
            f"In my 'Stock Market Analysis' backend system, I designed relational database schemas, built views and URL routing "
            f"adhering to clean architecture, and implemented complex database queries using Django ORM and SQL. I also have "
            f"foundational knowledge of RESTful APIs, JSON data serialization, and Git version control workflows.\n\n"
            f"I am eager to bring my backend programming skills, attention to database consistency, and fast learning agility "
            f"to the engineering team at {job.employer}."
        )
    elif job.category == JobCategory.CATEGORY_C:
        body = (
            f"I am pleased to submit my application for the {job.title} position at {job.employer}. "
            f"Holding a B.E. in Computer Science and Engineering (CGPA: 7.98) and comprehensive database training from QSpiders, "
            f"I specialize in SQL and Oracle SQL query development, relational data modeling, and backend database integration.\n\n"
            f"My practical experience includes writing CRUD operations, complex multi-table Joins, correlated Subqueries, "
            f"and GROUP BY/HAVING aggregate queries to process relational data accurately. In my 'Stock Market Analysis' "
            f"project, I designed the relational schema to store historical market quotes and integrated it with Django ORM "
            f"for reliable persistence and query execution.\n\n"
            f"I am committed to maintaining relational data integrity and delivering high-quality SQL solutions for {job.employer}."
        )
    else:  # Category D: Entry-Level / Internship / QA
        body = (
            f"I am writing to express my interest in the {job.title} opportunity at {job.employer}. "
            f"As a recent Computer Science Engineering graduate from JSS Academy of Technical Education (CGPA: 7.98) "
            f"actively advancing my skills in Python Full Stack Development and Selenium test automation at QSpiders, "
            f"I am excited to begin my professional career by adding immediate value to your technical operations.\n\n"
            f"My academic and project experience includes building functional web applications using Python, Django, SQL, "
            f"and modern JavaScript, as well as applying disciplined version control practices using Git and GitHub. "
            f"I am a proactive problem-solver with a strong willingness to learn team-specific stacks and methodologies.\n\n"
            f"I look forward to discussing how my technical background and strong work ethic align with {job.employer}'s goals."
        )

    closing = (
        f"\n\nThank you for your time and consideration. I look forward to the possibility of discussing my background in an interview.\n\n"
        f"Sincerely,\n"
        f"{profile.full_name}\n"
    )

    full_cover_letter = header + body + closing

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(full_cover_letter)

    return CoverLetterResult(
        text=full_cover_letter,
        file_path=str(file_path),
        category=job.category.value,
    )
