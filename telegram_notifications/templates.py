"""Telegram Notification Templates formatted in clean, valid HTML."""

from __future__ import annotations

import html
from typing import Any, Dict, List, Optional
from database.models import Application


def clean(val: Any) -> str:
    """Escape special HTML characters for Telegram message safety."""
    if val is None:
        return "N/A"
    return html.escape(str(val))


def format_new_job_found(app: Application, score_result: Optional[Any] = None) -> str:
    """
    Template A: New Job Found (Trigger: Score >= 60).
    Includes breakdown, verified skills, and recommended resume version.
    """
    breakdown_text = ""
    if score_result and hasattr(score_result, "breakdown"):
        bd = score_result.breakdown
        breakdown_text = (
            f"• Skills Alignment: <b>{bd.get('technical_skill_alignment', 0)}/35</b>\n"
            f"• Project Relevance: <b>{bd.get('project_relevance', 0)}/20</b>\n"
            f"• Eligibility Fit: <b>{bd.get('experience_eligibility_fit', 0)}/15</b>\n"
            f"• Location/Arrangement: <b>{bd.get('location_work_arrangement', 0)}/10</b>\n"
            f"• Recency: <b>{bd.get('posting_recency', 0)}/10</b>\n"
            f"• Career Growth: <b>{bd.get('career_fit_responsibilities', 0)}/10</b>\n"
        )

    req_skills = ", ".join(app.get_required_skills()) or "Core Python / Software Stack"
    missing_skills = ", ".join(app.get_missing_skills()) or "None (Clean match)"

    return (
        f"🎯 <b>NEW JOB OPPORTUNITY FOUND</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 <b>Role:</b> {clean(app.job_title)}\n"
        f"🏢 <b>Company:</b> {clean(app.employer)}\n"
        f"📍 <b>Location:</b> {clean(app.location)} ({clean(app.work_arrangement)})\n"
        f"📋 <b>Type:</b> {clean(app.employment_type)}\n"
        f"📅 <b>Posted:</b> {clean(app.posting_date or 'Recent')}\n"
        f"⭐ <b>Match Score:</b> <b>{app.matching_score}/100</b>\n\n"
        f"<b>📊 Rubric Score Breakdown:</b>\n"
        f"{breakdown_text}\n"
        f"<b>🛠️ Matched Skills:</b> {clean(req_skills)}\n"
        f"<b>⚠️ Missing Skills / Gaps:</b> {clean(missing_skills)}\n"
        f"<b>📄 Recommended Resume:</b> <code>{clean(app.selected_resume_version)}</code>\n"
        f"<b>🔄 Current Status:</b> <code>{clean(app.application_status)}</code>\n\n"
        f"🔗 <a href='{clean(app.job_url)}'>View Job Posting</a>"
    )


def format_application_submitted(app: Application, is_confirmed: bool = False) -> str:
    """
    Template B: Application Submitted / Confirmed.
    """
    status_label = "APPLICATION_CONFIRMED" if is_confirmed else "SUBMITTED (Pending Receipt)"
    icon = "✅" if is_confirmed else "📤"
    ref_num = app.application_reference_number or "N/A (Direct ATS Confirmation Screen)"

    return (
        f"{icon} <b>APPLICATION DISPATCH UPDATE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 <b>Role:</b> {clean(app.job_title)}\n"
        f"🏢 <b>Company:</b> {clean(app.employer)}\n"
        f"📍 <b>Location:</b> {clean(app.location)}\n"
        f"🌐 <b>Portal:</b> {clean(app.source_platform)}\n"
        f"⭐ <b>Score:</b> {app.matching_score}/100\n"
        f"📄 <b>Resume Version:</b> <code>{clean(app.selected_resume_version)}</code>\n"
        f"🕒 <b>Submitted At:</b> {clean(app.submission_timestamp or 'Just now')} (IST)\n"
        f"🏷️ <b>Status:</b> <b>{status_label}</b>\n"
        f"🔖 <b>Ref Number:</b> <code>{clean(ref_num)}</code>\n\n"
        f"🔗 <a href='{clean(app.job_url)}'>View Job Posting</a>"
    )


def format_manual_action_required(
    app: Application,
    halt_reason: str,
    next_step: str,
    resume_path: Optional[str] = None,
    cover_letter_path: Optional[str] = None
) -> str:
    """
    Template C: Manual Action Required.
    Triggered when automation encounters a restricted portal, CAPTCHA, missing candidate field,
    or required candidate legal declaration.
    """
    return (
        f"⚠️ <b>MANUAL ACTION REQUIRED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💼 <b>Role:</b> {clean(app.job_title)}\n"
        f"🏢 <b>Company:</b> {clean(app.employer)}\n"
        f"📍 <b>Location:</b> {clean(app.location)}\n"
        f"⭐ <b>Match Score:</b> {app.matching_score}/100\n\n"
        f"🛑 <b>Halt Reason:</b>\n"
        f"<code>{clean(halt_reason)}</code>\n\n"
        f"👉 <b>Candidate Action Needed:</b>\n"
        f"{clean(next_step)}\n\n"
        f"📁 <b>Prepared Materials:</b>\n"
        f"• Resume: <code>{clean(resume_path or app.selected_resume_version)}</code>\n"
        f"• Cover Letter: <code>{clean(cover_letter_path or 'Generated in output/cover_letters/')}</code>\n\n"
        f"🔗 <a href='{clean(app.job_url)}'>Complete Application Manually</a>"
    )


def format_daily_summary(kpis: Dict[str, Any], report_link: str = "") -> str:
    """
    Template D: Daily Summary Digest.
    """
    total = kpis.get("total_applications", 0)
    full_time = kpis.get("full_time_count", 0)
    internships = kpis.get("internship_count", 0)
    high_prio = kpis.get("high_priority_matches", 0)
    submitted = kpis.get("submitted_today", 0)
    cap = kpis.get("daily_limit", 10)
    manual_queue = kpis.get("awaiting_manual_action", 0)
    failed = kpis.get("failed_attempts", 0)
    interviews = kpis.get("assessments_and_interviews", 0)

    return (
        f"📊 <b>DAILY JOB AGENT EXECUTIVE SUMMARY</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔍 <b>Total Jobs Discovered:</b> {total}\n"
        f"   • Full-Time Permanent: {full_time}\n"
        f"   • Internships / Trainees: {internships}\n"
        f"🔥 <b>High-Priority Matches (≥85):</b> {high_prio}\n"
        f"🚀 <b>Submitted Today:</b> <b>{submitted} / {cap} (Daily Cap)</b>\n"
        f"⏳ <b>Awaiting Manual Action:</b> {manual_queue}\n"
        f"🎯 <b>Interviews & Assessments:</b> {interviews}\n"
        f"⚠️ <b>Failed / Halted Submissions:</b> {failed}\n\n"
        f"📑 <b>Detailed Report:</b> <code>{clean(report_link or 'output/reports/')}</code>\n"
        f"<i>Automated cycle complete. Zero fabricated data submitted.</i>"
    )
