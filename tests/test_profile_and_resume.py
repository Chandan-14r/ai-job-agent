"""Tests for Candidate Profile Loading, Guardrails, Resume Generation, and Variant Selection."""

import os
from pathlib import Path
import pytest

from candidate_profile.loader import load_candidate_profile, get_missing_candidate_fields
from candidate_profile.resume_verifier import verify_profile_against_guardrails
from job_parser.extractor import JobExtractor, JobCategory
from job_matcher.scorer import JobScorer
from resume_generator.builder_docx import generate_docx_resume, ResumeVariant
from resume_generator.builder_pdf import generate_pdf_resume
from resume_generator.cover_letter import generate_cover_letter


def test_profile_loading_and_missing_fields_detection():
    """Verify profile loads accurately and flags unverified/missing fields (Verification Area 1 & 12)."""
    profile = load_candidate_profile()
    assert profile.full_name == "Kiran A N"
    assert profile.contact.current_location == "Bengaluru, Karnataka, India"
    assert "Python" in profile.skills["programming_languages"]
    assert "Django" in profile.skills["backend"]
    assert "SQL" in profile.skills["databases"]

    # Verify missing fields are detected strictly under Zero Fabrication Policy
    missing = get_missing_candidate_fields(profile)
    missing_keys = [m["field"] for m in missing]

    # Phone, email, and graduation year must be flagged if not provided
    assert any("email" in k for k in missing_keys)
    assert any("phone" in k for k in missing_keys)
    assert any("graduation_year" in k for k in missing_keys)

    # Prinston Smart Engineer internship is verified from the uploaded resume
    assert len(profile.internships) > 0
    assert profile.internships[0].organization == "Prinston Smart Engineer"
    assert profile.internships[0].verified_status is True


def test_guardrail_enforcement_against_forbidden_claims():
    """Verify that unverified/forbidden technologies are strictly flagged."""
    profile = load_candidate_profile()

    # Clean profile text
    clean_text = "Experienced in Python, Django, SQL, HTML, CSS, JavaScript."
    res_clean = verify_profile_against_guardrails(profile, clean_text)
    assert res_clean.is_valid

    # Forbidden claims should trigger violations
    forbidden_text = "Proficient in Java, C++, React, and Oracle PL/SQL stored procedures."
    res_forbidden = verify_profile_against_guardrails(profile, forbidden_text)
    assert not res_forbidden.is_valid
    assert any("Java" in v for v in res_forbidden.violations)
    assert any("PL/SQL" in v for v in res_forbidden.violations)
    assert any("React" in v for v in res_forbidden.violations)


def test_resume_variant_selection():
    """Verify correct selection of RESUME_A, RESUME_B, and RESUME_C across categories (Area 2)."""
    profile = load_candidate_profile()
    scorer = JobScorer(profile)

    # 1. Full-Stack Job -> RESUME_A
    job_fs = JobExtractor.parse_job(
        title="Junior Full Stack Developer",
        employer="WebCorp",
        description="Looking for Python, Django, HTML, CSS, JavaScript full-stack engineer.",
    )
    res_fs = scorer.evaluate_job(job_fs)
    assert res_fs.recommended_resume_version == "RESUME_A"

    # 2. Pure Backend Job -> RESUME_B
    job_be = JobExtractor.parse_job(
        title="Python Backend Developer",
        employer="DataCore",
        description="Core Python, Django ORM, REST APIs, JSON serialization, and SQL database.",
    )
    res_be = scorer.evaluate_job(job_be)
    assert res_be.recommended_resume_version == "RESUME_B"

    # 3. SQL / Database Developer -> RESUME_C
    job_db = JobExtractor.parse_job(
        title="SQL Developer",
        employer="Analytics Inc",
        description="Writing complex SQL queries, multi-table joins, subqueries, and aggregations.",
    )
    res_db = scorer.evaluate_job(job_db)
    assert res_db.recommended_resume_version == "RESUME_C"


def test_resume_generation_docx_and_pdf(tmp_path):
    """Verify DOCX and PDF resume generation produces valid files without layout corruption."""
    profile = load_candidate_profile()

    for variant in [ResumeVariant.RESUME_A, ResumeVariant.RESUME_B, ResumeVariant.RESUME_C]:
        docx_file = generate_docx_resume(profile, variant=variant, output_dir=tmp_path)
        pdf_file = generate_pdf_resume(profile, variant=variant, output_dir=tmp_path)

        assert os.path.exists(docx_file)
        assert os.path.exists(pdf_file)
        assert os.path.getsize(docx_file) > 1000
        assert os.path.getsize(pdf_file) > 1000


def test_cover_letter_generation(tmp_path):
    """Verify factual cover letter generation for Category A/B/C/D without fabrication."""
    profile = load_candidate_profile()
    job = JobExtractor.parse_job(
        title="Entry-Level Python Developer",
        employer="Innovatech Bengaluru",
        description="Python, Django, SQL web developer role.",
    )

    cl = generate_cover_letter(profile, job, output_dir=tmp_path)
    assert os.path.exists(cl.file_path)
    assert "Innovatech Bengaluru" in cl.text
    assert "Stock Market Analysis" in cl.text
    assert "7.98" in cl.text
    assert "JSS Academy of Technical Education" in cl.text
