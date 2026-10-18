"""Tests for Workflow Pipeline, Permission Matrix Enforcement, and CAPTCHA/Manual Routing."""

import pytest
from candidate_profile.loader import load_candidate_profile
from database.models import ApplicationStatus
from database.repository import ApplicationRepository
from job_sources.permission_matrix import PlatformPermissionMatrix, is_auto_apply_permitted
from job_sources.connectors.synthetic_source import SyntheticJobSource
from application_workflow.engine import ApplicationEngine
from application_workflow.form_handler import ApplicationFormHandler
from telegram_notifications.notifier import TelegramNotifier


def test_platform_permission_matrix_enforcement():
    """Verify auto-apply is blocked on MANUAL_ONLY and ASSISTED_ONLY platforms (Verification Area 13)."""
    matrix = PlatformPermissionMatrix()

    # LinkedIn strictly prohibits automated applying
    assert matrix.get_apply_mode("linkedin") == "MANUAL_ONLY"
    assert not matrix.is_auto_apply_permitted("linkedin")

    # Workday requires manual logins/MFA
    assert matrix.get_apply_mode("workday_ats") == "MANUAL_ONLY"
    assert not matrix.is_auto_apply_permitted("workday_ats")

    # Greenhouse public ATS permits auto apply when authorized
    assert matrix.get_apply_mode("greenhouse_ats") == "AUTHORIZED_AUTO_APPLY"
    assert matrix.is_auto_apply_permitted("greenhouse_ats")


def test_captcha_and_manual_intervention_routing():
    """Verify CAPTCHA and OTP challenges halt automation and route to manual queue (Area 11)."""
    profile = load_candidate_profile()
    form_handler = ApplicationFormHandler(profile)

    # CAPTCHA challenge
    res_captcha = form_handler.prepare_and_validate_form(contains_captcha=True)
    assert not res_captcha.can_auto_submit
    assert res_captcha.halt_reason == "CAPTCHA_DETECTED"
    assert "CAPTCHA/bot challenge" in res_captcha.candidate_next_step

    # OTP prompt
    res_otp = form_handler.prepare_and_validate_form(contains_otp=True)
    assert not res_otp.can_auto_submit
    assert res_otp.halt_reason == "OTP_VERIFICATION_REQUIRED"

    # Legal declaration requiring manual review
    res_legal = form_handler.prepare_and_validate_form(requires_legal_attestation=True)
    assert not res_legal.can_auto_submit
    assert res_legal.halt_reason == "LEGAL_DECLARATION_REVIEW"


def test_workflow_end_to_end_dry_run_simulation(tmp_path):
    """Verify 13-step pipeline runs cleanly in simulation mode with synthetic jobs (Area 15)."""
    db_file = tmp_path / "test_sim.db"
    repo = ApplicationRepository(db_path=db_file)
    profile = load_candidate_profile()
    notifier = TelegramNotifier(dry_run=True)

    engine = ApplicationEngine(
        profile=profile,
        repository=repo,
        notifier=notifier,
        mode="DISCOVERY_MODE",
        output_dir=tmp_path / "output",
    )

    source = SyntheticJobSource()
    jobs = source.discover_jobs(limit=10)

    for job in jobs:
        app = engine.process_job(job)
        assert app is not None
        assert app.application_status in [
            ApplicationStatus.QUALIFIED.value,
            ApplicationStatus.REJECTED.value,
        ]

    # Verify report generation
    reports = engine.generate_daily_report()
    import os
    assert os.path.exists(reports["csv"])
    assert os.path.exists(reports["md"])
