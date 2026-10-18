"""Tests for SQLite Persistence, Audit Trails, Daily Caps, and State Transitions."""

from datetime import date
import pytest
from database.models import Application, ApplicationStatus, EmploymentType
from database.repository import ApplicationRepository


def test_database_persistence_and_audit_history(tmp_path):
    """Verify application persistence and audit history logging (Verification Area 6)."""
    db_file = tmp_path / "test_db.db"
    repo = ApplicationRepository(db_path=db_file)

    app = Application(
        id="app-audit-01",
        employer="Zenith Software",
        job_title="Associate Python Developer",
        employment_type=EmploymentType.FULL_TIME.value,
        matching_score=88,
        selected_resume_version="RESUME_A",
        application_status=ApplicationStatus.DISCOVERED.value,
    )
    repo.add_application(app)

    # Verify retrieval
    stored = repo.get_application_by_id("app-audit-01")
    assert stored is not None
    assert stored.employer == "Zenith Software"
    assert stored.matching_score == 88

    # Check initial audit record
    history = repo.get_status_history("app-audit-01")
    assert len(history) == 1
    assert history[0].previous_status == "NONE"
    assert history[0].new_status == "DISCOVERED"


def test_valid_and_illegal_state_transitions(tmp_path):
    """Verify strict state machine rules and distinguish SUBMITTED from CONFIRMED (Area 14)."""
    db_file = tmp_path / "test_state.db"
    repo = ApplicationRepository(db_path=db_file)

    app = Application(
        id="app-state-01",
        employer="Apex Labs",
        job_title="Django Developer",
        application_status=ApplicationStatus.DISCOVERED.value,
    )
    repo.add_application(app)

    # Valid transition: DISCOVERED -> QUALIFIED
    assert repo.update_status("app-state-01", ApplicationStatus.QUALIFIED, reason_or_actor="Passed Filters")
    assert repo.get_application_by_id("app-state-01").application_status == "QUALIFIED"

    # Valid transition: QUALIFIED -> READY_FOR_APPLICATION
    assert repo.update_status("app-state-01", ApplicationStatus.READY_FOR_APPLICATION, reason_or_actor="Materials Staged")

    # Valid transition: READY_FOR_APPLICATION -> SUBMITTED (Distinct from APPLICATION_CONFIRMED)
    assert repo.update_status("app-state-01", ApplicationStatus.SUBMITTED, reason_or_actor="Form Dispatched")
    assert repo.get_application_by_id("app-state-01").application_status == "SUBMITTED"

    # Valid transition: SUBMITTED -> APPLICATION_CONFIRMED
    assert repo.update_status("app-state-01", ApplicationStatus.APPLICATION_CONFIRMED, reason_or_actor="Receipt Verified")
    assert repo.get_application_by_id("app-state-01").application_status == "APPLICATION_CONFIRMED"

    # Illegal transition: APPLICATION_CONFIRMED -> DISCOVERED (Must raise ValueError)
    with pytest.raises(ValueError, match="Illegal state transition"):
        repo.update_status("app-state-01", ApplicationStatus.DISCOVERED, reason_or_actor="Invalid Reset")


def test_separation_of_full_time_and_internships(tmp_path):
    """Verify full-time and internship records are separated in database queries and KPIs (Area 6)."""
    db_file = tmp_path / "test_kpis.db"
    repo = ApplicationRepository(db_path=db_file)

    # Add 2 full time and 1 internship
    repo.add_application(Application(id="ft-1", employer="A", job_title="T1", employment_type=EmploymentType.FULL_TIME.value))
    repo.add_application(Application(id="ft-2", employer="B", job_title="T2", employment_type=EmploymentType.FULL_TIME.value))
    repo.add_application(Application(id="int-1", employer="C", job_title="T3", employment_type=EmploymentType.INTERNSHIP.value))

    kpis = repo.get_kpi_summary()
    assert kpis["full_time_count"] == 2
    assert kpis["internship_count"] == 1


def test_daily_application_limit_enforcement(tmp_path):
    """Verify daily cap accurately counts submissions and supports limit checks (Area 10)."""
    db_file = tmp_path / "test_cap.db"
    repo = ApplicationRepository(db_path=db_file)

    today_str = date.today().isoformat()

    # Insert 10 submitted applications today
    for i in range(10):
        app = Application(
            id=f"cap-app-{i}",
            employer=f"Emp {i}",
            job_title=f"Dev {i}",
            application_status=ApplicationStatus.SUBMITTED.value,
            submission_timestamp=f"{today_str}T10:0{i}:00",
        )
        repo.add_application(app)

    # Verify count is 10
    assert repo.get_daily_submission_count() == 10

    # Next attempt check
    cap = 10
    can_submit_more = (repo.get_daily_submission_count() < cap)
    assert not can_submit_more, "Submission #11 must be blocked when daily limit is 10"
