"""Tests for 100-Point Matcher, Hard Eligibility Veto, and Deduplication."""

import pytest
from candidate_profile.loader import load_candidate_profile
from database.models import Application
from database.repository import ApplicationRepository
from duplicate_checker.deduplicator import DuplicateChecker, canonicalize_url
from job_matcher.scorer import JobScorer, DecisionBand
from job_parser.extractor import JobExtractor


def test_url_canonicalization():
    """Verify tracking tags are stripped while critical job IDs are preserved (Verification Area 4)."""
    # 1. URL with UTM tags and job ID
    raw_url = "https://careers.company.com/jobs/view?id=12345&utm_source=linkedin&utm_medium=feed&ref=email_alert"
    canon = canonicalize_url(raw_url)
    assert "id=12345" in canon
    assert "utm_source" not in canon
    assert "utm_medium" not in canon
    assert "ref" not in canon

    # 2. Lever posting with gh_jid
    raw_url_lever = "https://jobs.lever.co/techcorp/abcd-1234?source=naukri&gh_jid=998877"
    canon_lever = canonicalize_url(raw_url_lever)
    assert "gh_jid=998877" in canon_lever
    assert "source=naukri" not in canon_lever


def test_experience_ceiling_hard_veto():
    """Verify >2 years experience triggers deterministic hard veto (Verification Area 3)."""
    profile = load_candidate_profile()
    scorer = JobScorer(profile)

    # Job requiring 4-6 years of experience
    job_senior = JobExtractor.parse_job(
        title="Senior Python Backend Engineer",
        employer="Enterprise Corp",
        description="Must have 5+ years of experience with Python, Django, and distributed systems.",
    )
    res = scorer.evaluate_job(job_senior)
    assert res.is_vetoed
    assert res.decision_band == DecisionBand.REJECTED
    assert res.total_score == 0
    assert "2.0-year early-career ceiling" in res.veto_reason


def test_plsql_exclusion_hard_veto():
    """Verify mandatory PL/SQL and stored procedures trigger hard veto (Verification Area 3)."""
    profile = load_candidate_profile()
    scorer = JobScorer(profile)

    job_plsql = JobExtractor.parse_job(
        title="Oracle Database Developer",
        employer="Banking Tech",
        description="Mandatory requirement: Expert in Oracle PL/SQL, stored procedures, and triggers.",
    )
    res = scorer.evaluate_job(job_plsql)
    assert res.is_vetoed
    assert res.decision_band == DecisionBand.REJECTED
    assert "PL/SQL is excluded" in res.veto_reason


def test_pay_to_work_scam_veto():
    """Verify fraudulent/fee-demanding jobs are rejected immediately (Verification Area 5)."""
    profile = load_candidate_profile()
    scorer = JobScorer(profile)

    job_scam = JobExtractor.parse_job(
        title="Graduate Python Trainee",
        employer="Shady HR Solutions",
        description="100% placement guarantee! Selected candidates must deposit registration fee and training fee of Rs 20,000.",
    )
    res = scorer.evaluate_job(job_scam)
    assert res.is_vetoed
    assert res.decision_band == DecisionBand.REJECTED
    assert "fraudulent or fee-demanding" in res.veto_reason


def test_high_priority_100_point_scoring():
    """Verify entry-level Python/Django match achieves high score (>=85) (Verification Area 3)."""
    profile = load_candidate_profile()
    scorer = JobScorer(profile)

    job_perfect = JobExtractor.parse_job(
        title="Junior Python Full Stack Developer",
        employer="ScaleUp Tech",
        description=(
            "Entry-level Python Full Stack Developer (0-1 year exp). "
            "Stack: Python, Django, SQL database, HTML5, CSS3, JavaScript. "
            "Building web portals, user authentication, and REST APIs. Bengaluru based. Freshers welcome."
        ),
        location_raw="Bengaluru",
    )
    res = scorer.evaluate_job(job_perfect)
    assert not res.is_vetoed
    assert res.total_score >= 85
    assert res.decision_band == DecisionBand.HIGH_PRIORITY
    assert res.breakdown["technical_skill_alignment"] >= 25
    assert res.breakdown["location_work_arrangement"] == 10


def test_multi_key_deduplication(tmp_path):
    """Verify duplicate detection across URL, platform ID, and composite keys (Verification Area 4)."""
    db_file = tmp_path / "test_dedup.db"
    repo = ApplicationRepository(db_path=db_file)
    dedup = DuplicateChecker(repo)

    # Add initial job
    app = Application(
        id="test-app-001",
        employer="CloudMatrix",
        job_title="Python Developer",
        location="Bengaluru, Karnataka, India",
        job_url="https://cloudmatrix.com/jobs/py-01?utm_campaign=ad",
        canonical_url=canonicalize_url("https://cloudmatrix.com/jobs/py-01?utm_campaign=ad"),
        source_platform="naukri",
        external_job_id="NK-9988",
    )
    repo.add_application(app)

    # 1. Exact canonical URL duplicate
    res_url = dedup.check_duplicate(
        employer="CloudMatrix",
        job_title="Python Developer",
        location="Bengaluru, Karnataka, India",
        raw_url="https://cloudmatrix.com/jobs/py-01?utm_medium=email",
    )
    assert res_url.is_duplicate
    assert res_url.duplicate_type == "CANONICAL_URL"

    # 2. Platform + Job ID duplicate
    res_plat = dedup.check_duplicate(
        employer="Different Name",
        job_title="Different Title",
        location="Bengaluru",
        source_platform="naukri",
        external_job_id="NK-9988",
    )
    assert res_plat.is_duplicate
    assert res_plat.duplicate_type == "PLATFORM_JOB_ID"

    # 3. Composite key duplicate (Pvt Ltd normalization)
    res_comp = dedup.check_duplicate(
        employer="CloudMatrix Pvt Ltd",
        job_title="Python Developer",
        location="Bengaluru, Karnataka, India",
        source_platform="linkedin",
    )
    assert res_comp.is_duplicate
    assert res_comp.duplicate_type == "COMPOSITE_KEY"
