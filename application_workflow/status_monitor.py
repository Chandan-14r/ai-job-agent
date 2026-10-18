"""Application Status Monitor with Candidate Privacy Guards."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from database.models import Application, ApplicationStatus
from database.repository import ApplicationRepository
from telegram_notifications.notifier import TelegramNotifier

logger = logging.getLogger("status_monitor")


class ApplicationStatusMonitor:
    def __init__(
        self,
        repository: ApplicationRepository,
        notifier: Optional[TelegramNotifier] = None,
        email_monitoring_enabled: bool = False,
    ):
        self.repo = repository
        self.notifier = notifier or TelegramNotifier()
        self.email_monitoring_enabled = email_monitoring_enabled

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Report current status monitoring configuration."""
        return {
            "email_monitoring_enabled": self.email_monitoring_enabled,
            "status_description": "DISABLED (Manual / Portal tracking active)" if not self.email_monitoring_enabled else "ENABLED",
            "active_applications_tracked": len(
                self.repo.get_applications(status=ApplicationStatus.SUBMITTED.value) +
                self.repo.get_applications(status=ApplicationStatus.APPLICATION_CONFIRMED.value)
            ),
        }

    def process_status_update(
        self,
        application_id: str,
        detected_status: ApplicationStatus | str,
        evidence_note: str = "",
    ) -> bool:
        """
        Record verified application status update and dispatch high-priority candidate alert.
        Strict Boundary: Never auto-replies to recruiters, books interview slots, or withdraws.
        """
        app = self.repo.get_application_by_id(application_id)
        if not app:
            logger.error(f"Application ID {application_id} not found.")
            return False

        status_str = detected_status.value if isinstance(detected_status, ApplicationStatus) else detected_status

        # Transition status in repository
        success = self.repo.update_status(
            application_id=application_id,
            new_status=status_str,
            reason_or_actor=f"Status Monitor: {evidence_note}",
        )

        if success and self.notifier:
            # Send candidate alert
            alert_text = (
                f"🔔 <b>APPLICATION STATUS UPDATE DETECTED</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"💼 <b>Role:</b> {app.job_title}\n"
                f"🏢 <b>Company:</b> {app.employer}\n"
                f"🏷️ <b>New Status:</b> <b>{status_str}</b>\n"
                f"📝 <b>Note:</b> {evidence_note}\n\n"
                f"<i>Action Required: Review in ATS dashboard or official email.</i>"
            )
            self.notifier.send_message(alert_text, event_id=f"status_update_{app.id}_{status_str}")

        return success
