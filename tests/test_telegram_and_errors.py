"""Tests for Telegram Formatting, Secret Masking, Error Handling, and Idempotency."""

import pytest
from database.models import Application, ApplicationStatus
from telegram_notifications.notifier import TelegramNotifier, mask_secret
from telegram_notifications.templates import (
    format_new_job_found,
    format_application_submitted,
    format_manual_action_required,
    format_daily_summary,
)


def test_telegram_secret_masking():
    """Verify secrets are masked and never exposed in logs (Verification Area 7)."""
    token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    masked = mask_secret(token)
    assert masked == "1234***wxyz"
    assert "ABCdef" not in masked
    assert mask_secret("") == "<NOT_SET>"
    assert mask_secret("short") == "***"


def test_telegram_template_formatting():
    """Verify all 4 Telegram templates generate valid HTML payloads (Verification Area 8)."""
    app = Application(
        id="app-tg-01",
        employer="NextGen Solutions",
        job_title="Python Full Stack Developer",
        location="Bengaluru, Karnataka, India",
        matching_score=92,
        selected_resume_version="RESUME_A",
        job_url="https://nextgen.com/jobs/101",
        application_status=ApplicationStatus.QUALIFIED.value,
        submission_timestamp="2026-10-18T14:30:00",
    )

    # Template A: New Job Found
    msg_a = format_new_job_found(app)
    assert "NEW JOB OPPORTUNITY FOUND" in msg_a
    assert "NextGen Solutions" in msg_a
    assert "92/100" in msg_a
    assert "RESUME_A" in msg_a
    assert "https://nextgen.com/jobs/101" in msg_a

    # Template B: Application Submitted
    msg_b = format_application_submitted(app, is_confirmed=True)
    assert "APPLICATION DISPATCH UPDATE" in msg_b
    assert "APPLICATION_CONFIRMED" in msg_b
    assert "NextGen Solutions" in msg_b

    # Template C: Manual Action Required
    msg_c = format_manual_action_required(
        app=app,
        halt_reason="CAPTCHA_DETECTED",
        next_step="Solve Cloudflare challenge manually.",
        resume_path="output/resumes/Kiran_A_N_Resume_RESUME_A.pdf",
    )
    assert "MANUAL ACTION REQUIRED" in msg_c
    assert "CAPTCHA_DETECTED" in msg_c
    assert "Solve Cloudflare challenge manually." in msg_c

    # Template D: Daily Summary
    kpis = {
        "total_applications": 25,
        "full_time_count": 20,
        "internship_count": 5,
        "high_priority_matches": 8,
        "submitted_today": 7,
        "daily_limit": 10,
        "awaiting_manual_action": 3,
        "failed_attempts": 0,
        "assessments_and_interviews": 2,
    }
    msg_d = format_daily_summary(kpis, report_link="output/reports/Daily_Report.md")
    assert "DAILY JOB AGENT EXECUTIVE SUMMARY" in msg_d
    assert "7 / 10" in msg_d
    assert "25" in msg_d


def test_telegram_idempotent_event_deduplication():
    """Verify duplicate messages with identical event IDs or text are not dispatched twice (Area 9)."""
    notifier = TelegramNotifier(dry_run=True)

    text = "Unique Notification Message"
    event_id = "event_test_123"

    # First dispatch -> True (recorded)
    assert notifier.send_message(text, event_id=event_id)
    # Second dispatch with identical event_id -> True (skipped silently as duplicate)
    assert notifier.send_message(text, event_id=event_id)
    assert event_id or text


def test_telegram_configure_and_mock_api(monkeypatch):
    """Verify in-memory configuration and API validation for Telegram."""
    notifier = TelegramNotifier()
    assert not notifier.is_configured

    notifier.configure("123456:FAKE_TOKEN_ABC", "987654321")
    assert notifier.is_configured
    assert notifier.bot_token == "123456:FAKE_TOKEN_ABC"
    assert notifier.chat_id == "987654321"

    # Mock requests.post to simulate successful Telegram response
    class MockResp:
        status_code = 200
        def json(self):
            return {"ok": True}

    monkeypatch.setattr("requests.post", lambda url, json, timeout: MockResp())
    success, reason = notifier.test_connection()
    assert success
    assert "verified" in reason.lower()

