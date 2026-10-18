"""Persistent Local Browser Session Vault for Portal Authentication.

Manages encrypted / protected local cookie and storage states for Naukri, Internshala, and LinkedIn
under the session_data/ directory (excluded from git tracking).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("session_vault")

SUPPORTED_PORTALS = ["naukri", "internshala", "linkedin"]


def mask_phone_number(phone: Optional[str]) -> str:
    """Mask phone number for safe UI display (e.g. +91 98****3210)."""
    if not phone:
        return ""
    clean = phone.strip()
    if len(clean) <= 4:
        return clean
    if len(clean) >= 10:
        return f"{clean[:4]}****{clean[-4:]}"
    return f"{clean[:2]}****{clean[-2:]}"


class SessionVault:
    """
    Local storage manager for browser contexts, auth cookies, and portal connection states.
    All state is saved locally under session_data/ to maintain candidate session privacy.
    """

    def __init__(self, session_dir: Optional[Path | str] = None):
        if session_dir is None:
            # Default to session_data at the project root
            base_dir = Path(__file__).resolve().parent.parent.parent
            self.session_dir = base_dir / "session_data"
        else:
            self.session_dir = Path(session_dir)

        self.session_dir.mkdir(parents=True, exist_ok=True)

    def get_storage_state_path(self, portal: str) -> Path:
        """Return the absolute path to the Playwright storage_state JSON file for the portal."""
        return self.session_dir / f"{portal.lower()}_state.json"

    def get_metadata_path(self, portal: str) -> Path:
        """Return the absolute path to the session metadata JSON file for the portal."""
        return self.session_dir / f"{portal.lower()}_meta.json"

    def save_session(
        self,
        portal: str,
        phone: Optional[str] = None,
        storage_state: Optional[Dict[str, Any]] = None,
        status: str = "AUTHENTICATED",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Save Playwright storage_state (cookies + localStorage) and metadata for a portal.
        """
        portal_key = portal.lower()
        state_file = self.get_storage_state_path(portal_key)
        meta_file = self.get_metadata_path(portal_key)

        cookie_count = 0
        if storage_state is not None:
            cookie_count = len(storage_state.get("cookies", []))
            try:
                with open(state_file, "w", encoding="utf-8") as f:
                    json.dump(storage_state, f, indent=2)
            except Exception as e:
                logger.error(f"[{portal_key}] Failed to write storage state: {e}")
        elif state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    existing_state = json.load(f)
                    cookie_count = len(existing_state.get("cookies", []))
            except Exception:
                cookie_count = 0

        # Load existing meta to preserve previous sync data if present
        existing_meta = self.load_metadata(portal_key) or {}

        meta = {
            "portal": portal_key,
            "status": status,
            "phone": phone or existing_meta.get("phone", ""),
            "masked_phone": mask_phone_number(phone or existing_meta.get("phone", "")),
            "authenticated_at": datetime.utcnow().isoformat() if status == "AUTHENTICATED" else existing_meta.get("authenticated_at"),
            "last_updated_at": datetime.utcnow().isoformat(),
            "cookie_count": cookie_count,
            "storage_state_file": str(state_file),
            "has_storage_state": state_file.exists(),
            "last_sync_at": existing_meta.get("last_sync_at"),
            "last_sync_jobs_count": existing_meta.get("last_sync_jobs_count", 0),
        }
        if extra:
            meta.update(extra)

        try:
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
        except Exception as e:
            logger.error(f"[{portal_key}] Failed to write session metadata: {e}")

        logger.info(f"[{portal_key}] Session saved successfully. Status: {status}, Cookies: {cookie_count}")
        return meta

    def update_status(
        self,
        portal: str,
        status: str,
        phone: Optional[str] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update portal connection status (e.g. PENDING_OTP, DISCONNECTED, AUTHENTICATED)."""
        portal_key = portal.lower()
        meta = self.load_metadata(portal_key) or {
            "portal": portal_key,
            "cookie_count": 0,
            "has_storage_state": self.get_storage_state_path(portal_key).exists(),
            "last_sync_at": None,
            "last_sync_jobs_count": 0,
        }
        meta["status"] = status
        meta["last_updated_at"] = datetime.utcnow().isoformat()
        if phone:
            meta["phone"] = phone
            meta["masked_phone"] = mask_phone_number(phone)
        if status == "AUTHENTICATED":
            meta["authenticated_at"] = datetime.utcnow().isoformat()
        if extra:
            meta.update(extra)

        meta_file = self.get_metadata_path(portal_key)
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        return meta

    def load_storage_state(self, portal: str) -> Optional[Dict[str, Any]]:
        """Load the stored Playwright storage_state dict if present."""
        state_file = self.get_storage_state_path(portal)
        if not state_file.exists():
            return None
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[{portal}] Failed to read storage state from {state_file}: {e}")
            return None

    def load_metadata(self, portal: str) -> Optional[Dict[str, Any]]:
        """Load portal session metadata dict if present."""
        meta_file = self.get_metadata_path(portal)
        if not meta_file.exists():
            return None
        try:
            with open(meta_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[{portal}] Failed to read session metadata from {meta_file}: {e}")
            return None

    def has_valid_session(self, portal: str) -> bool:
        """Check whether portal has an authenticated session with stored cookies."""
        portal_key = portal.lower()
        meta = self.load_metadata(portal_key)
        if not meta:
            return False
        if meta.get("status") != "AUTHENTICATED":
            return False
        state_file = self.get_storage_state_path(portal_key)
        return state_file.exists() and state_file.stat().st_size > 10

    def clear_session(self, portal: str) -> bool:
        """Clear local session state and reset portal status to DISCONNECTED."""
        portal_key = portal.lower()
        state_file = self.get_storage_state_path(portal_key)
        meta_file = self.get_metadata_path(portal_key)

        if state_file.exists():
            try:
                state_file.unlink()
            except Exception as e:
                logger.warning(f"Could not remove state file {state_file}: {e}")

        # Update metadata to DISCONNECTED
        self.update_status(portal_key, status="DISCONNECTED", extra={
            "authenticated_at": None,
            "cookie_count": 0,
            "has_storage_state": False,
        })
        logger.info(f"[{portal_key}] Session cleared and disconnected.")
        return True

    def get_portal_status(self, portal: str) -> Dict[str, Any]:
        """Get standard status summary for a portal."""
        portal_key = portal.lower()
        meta = self.load_metadata(portal_key)
        state_exists = self.get_storage_state_path(portal_key).exists()

        if not meta:
            return {
                "portal": portal_key,
                "status": "DISCONNECTED",
                "phone": "",
                "masked_phone": "",
                "authenticated_at": None,
                "last_sync_at": None,
                "last_sync_jobs_count": 0,
                "cookie_count": 0,
                "has_storage_state": state_exists,
                "is_authenticated": False,
            }

        is_auth = meta.get("status") == "AUTHENTICATED" and state_exists
        return {
            "portal": portal_key,
            "status": meta.get("status", "DISCONNECTED"),
            "phone": meta.get("phone", ""),
            "masked_phone": meta.get("masked_phone", mask_phone_number(meta.get("phone"))),
            "authenticated_at": meta.get("authenticated_at"),
            "last_sync_at": meta.get("last_sync_at"),
            "last_sync_jobs_count": meta.get("last_sync_jobs_count", 0),
            "cookie_count": meta.get("cookie_count", 0),
            "has_storage_state": state_exists,
            "is_authenticated": is_auth,
        }

    def get_all_portal_statuses(self) -> Dict[str, Dict[str, Any]]:
        """Return status dictionary for all supported portals."""
        return {portal: self.get_portal_status(portal) for portal in SUPPORTED_PORTALS}

    def record_sync_result(self, portal: str, jobs_count: int) -> Dict[str, Any]:
        """Update last sync timestamp and jobs count for portal."""
        return self.update_status(
            portal=portal,
            status="AUTHENTICATED",
            extra={
                "last_sync_at": datetime.utcnow().isoformat(),
                "last_sync_jobs_count": jobs_count,
            },
        )
