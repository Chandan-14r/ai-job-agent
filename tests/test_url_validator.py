"""Unit tests for Centralized URL Validator and Provenance Engine."""

import pytest
from unittest.mock import MagicMock, patch
import requests

from database.models import URLVerificationStatus
from job_sources.url_validator import URLValidator


def test_url_well_formedness():
    """Verify syntactic validation of URLs."""
    assert URLValidator.is_well_formed("https://canonical.com/careers/321") is True
    assert URLValidator.is_well_formed("http://boards.greenhouse.io/gitlab/jobs/123") is True
    assert URLValidator.is_well_formed("https://www.naukri.com/job-listings-123") is True

    # Invalid / placeholder URLs
    assert URLValidator.is_well_formed(None) is False
    assert URLValidator.is_well_formed("") is False
    assert URLValidator.is_well_formed("#") is False
    assert URLValidator.is_well_formed("javascript:void(0)") is False
    assert URLValidator.is_well_formed("not-a-valid-url") is False


def test_synthetic_and_demo_isolation():
    """Verify synthetic fixtures are flagged as DEMO_ONLY under Zero Fabrication."""
    status, reason, final_url = URLValidator.validate_url(
        "https://careers.fintechinnovations.com/jobs/101",
        is_synthetic=True,
    )
    assert status == URLVerificationStatus.DEMO_ONLY
    assert "DEMO DATA" in reason

    # Detected by mock domain even if is_synthetic is not passed
    status2, reason2, _ = URLValidator.validate_url(
        "https://mock.jobs.local/software-engineer",
        is_synthetic=False,
    )
    assert status2 == URLVerificationStatus.DEMO_ONLY


def test_restricted_portal_source_confirmed():
    """Verify login-restricted portals (Naukri, LinkedIn, Internshala) return SOURCE_CONFIRMED."""
    for portal_url in [
        "https://www.naukri.com/job-listings-python-dev-12345",
        "https://internshala.com/job/detail/python-developer-123",
        "https://www.linkedin.com/jobs/view/987654321",
    ]:
        status, reason, _ = URLValidator.validate_url(portal_url, check_live_network=False)
        assert status == URLVerificationStatus.SOURCE_CONFIRMED
        assert "Authentic" in reason or "Portal" in reason


def test_invalid_link_handling():
    """Verify malformed links return INVALID_LINK."""
    status, reason, _ = URLValidator.validate_url("#")
    assert status == URLVerificationStatus.INVALID_LINK

    status2, _, _ = URLValidator.validate_url("htp:/bad-scheme")
    assert status2 == URLVerificationStatus.INVALID_LINK


@patch("requests.head")
def test_public_ats_verified_active(mock_head):
    """Verify HTTP 200 on public ATS returns VERIFIED_ACTIVE."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.url = "https://boards.greenhouse.io/gitlab/jobs/45678"
    mock_head.return_value = mock_resp

    status, reason, final_url = URLValidator.validate_url(
        "https://boards.greenhouse.io/gitlab/jobs/45678",
        check_live_network=True,
    )
    assert status == URLVerificationStatus.VERIFIED_ACTIVE
    assert "HTTP 200 Verified" in reason
    assert final_url == "https://boards.greenhouse.io/gitlab/jobs/45678"


@patch("requests.head")
def test_public_ats_expired_404(mock_head):
    """Verify 404 response triggers EXPIRED status."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.url = "https://canonical.com/careers/old-job"
    mock_head.return_value = mock_resp

    status, reason, _ = URLValidator.validate_url(
        "https://canonical.com/careers/old-job",
        check_live_network=True,
    )
    assert status == URLVerificationStatus.EXPIRED
    assert "expired" in reason.lower()


@patch("requests.head")
def test_network_timeout_handling(mock_head):
    """Verify network timeout returns SOURCE_UNAVAILABLE without crashing."""
    mock_head.side_effect = requests.Timeout("Connection timed out")

    status, reason, _ = URLValidator.validate_url(
        "https://boards.greenhouse.io/slow-company/job/1",
        check_live_network=True,
    )
    assert status == URLVerificationStatus.SOURCE_UNAVAILABLE
    assert "timeout" in reason.lower()
