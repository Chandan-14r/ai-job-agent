"""Platform Permission Matrix enforcing governance and anti-automation rules."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


class PlatformMode(str, Enum):
    API_FEED = "API_FEED"
    ASSISTED_BROWSER = "ASSISTED_BROWSER"
    MANUAL_ONLY = "MANUAL_ONLY"
    AUTHORIZED_AUTO_APPLY = "AUTHORIZED_AUTO_APPLY"


# Default fallback permissions
DEFAULT_PLATFORM_PERMISSIONS: Dict[str, Dict[str, str]] = {
    "linkedin": {
        "discovery_mode": PlatformMode.ASSISTED_BROWSER.value,
        "apply_mode": PlatformMode.MANUAL_ONLY.value,
    },
    "naukri": {
        "discovery_mode": PlatformMode.ASSISTED_BROWSER.value,
        "apply_mode": PlatformMode.ASSISTED_BROWSER.value,
    },
    "indeed_india": {
        "discovery_mode": PlatformMode.ASSISTED_BROWSER.value,
        "apply_mode": PlatformMode.ASSISTED_BROWSER.value,
    },
    "foundit": {
        "discovery_mode": PlatformMode.ASSISTED_BROWSER.value,
        "apply_mode": PlatformMode.ASSISTED_BROWSER.value,
    },
    "internshala": {
        "discovery_mode": PlatformMode.ASSISTED_BROWSER.value,
        "apply_mode": PlatformMode.ASSISTED_BROWSER.value,
    },
    "wellfound": {
        "discovery_mode": PlatformMode.ASSISTED_BROWSER.value,
        "apply_mode": PlatformMode.MANUAL_ONLY.value,
    },
    "cutshort": {
        "discovery_mode": PlatformMode.ASSISTED_BROWSER.value,
        "apply_mode": PlatformMode.MANUAL_ONLY.value,
    },
    "instahyre": {
        "discovery_mode": PlatformMode.ASSISTED_BROWSER.value,
        "apply_mode": PlatformMode.MANUAL_ONLY.value,
    },
    "workday_ats": {
        "discovery_mode": PlatformMode.API_FEED.value,
        "apply_mode": PlatformMode.MANUAL_ONLY.value,
    },
    "greenhouse_ats": {
        "discovery_mode": PlatformMode.API_FEED.value,
        "apply_mode": PlatformMode.AUTHORIZED_AUTO_APPLY.value,
    },
    "lever_ats": {
        "discovery_mode": PlatformMode.API_FEED.value,
        "apply_mode": PlatformMode.AUTHORIZED_AUTO_APPLY.value,
    },
    "ashby_ats": {
        "discovery_mode": PlatformMode.API_FEED.value,
        "apply_mode": PlatformMode.AUTHORIZED_AUTO_APPLY.value,
    },
}


class PlatformPermissionMatrix:
    def __init__(self, config_path: Optional[Path | str] = None):
        if config_path is None:
            base_dir = Path(__file__).resolve().parent.parent
            config_path = base_dir / "config" / "job_sources.yaml"
        self.config_path = Path(config_path)
        self.permissions: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.config_path.exists():
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                self.permissions = data.get("sources", {})
        else:
            self.permissions = DEFAULT_PLATFORM_PERMISSIONS

    def get_discovery_mode(self, platform_key: str) -> str:
        plat = self.permissions.get(platform_key, {})
        return plat.get("discovery_mode", PlatformMode.ASSISTED_BROWSER.value)

    def get_apply_mode(self, platform_key: str) -> str:
        plat = self.permissions.get(platform_key, {})
        return plat.get("apply_mode", PlatformMode.MANUAL_ONLY.value)

    def is_auto_apply_permitted(self, platform_key: str) -> bool:
        """
        Check if automated applying is strictly permitted by the platform's governance policy.
        Returns False for LinkedIn, Workday, Cutshort, Wellfound, Instahyre.
        """
        apply_mode = self.get_apply_mode(platform_key)
        return apply_mode == PlatformMode.AUTHORIZED_AUTO_APPLY.value


def is_auto_apply_permitted(platform_key: str) -> bool:
    matrix = PlatformPermissionMatrix()
    return matrix.is_auto_apply_permitted(platform_key)
