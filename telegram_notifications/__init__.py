"""Telegram Notifications Package for Real-Time Candidate Alerts."""

from .templates import (
    format_new_job_found,
    format_application_submitted,
    format_manual_action_required,
    format_daily_summary,
)
from .notifier import TelegramNotifier, get_default_notifier

__all__ = [
    "format_new_job_found",
    "format_application_submitted",
    "format_manual_action_required",
    "format_daily_summary",
    "TelegramNotifier",
    "get_default_notifier",
]
