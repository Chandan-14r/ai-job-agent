"""Unit and integration tests for SessionVault, Portal Browser Connectors,
Salary Floor Veto (min 4 LPA), Location Filters, and Dashboard Portal Connection APIs.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from candidate_profile.loader import load_candidate_profile
from database.repository import ApplicationRepository
from dashboard.app import create_app
from job_matcher.scorer import JobScorer, DecisionBand
from job_parser.extractor import JobExtractor, JobCategory
from job_sources.connectors.session_vault import SessionVault, mask_phone_number
from job_sources.connectors.naukri_browser import NaukriBrowserConnector
from job_sources.connectors.internshala_browser import InternshalaBrowserConnector
from job_sources.connectors.linkedin_browser import LinkedInBrowserConnector


def test_session_vault_lifecycle(tmp_path):
    """Test full persistent lifecycle of SessionVault under isolated session_data directory."""
    vault = SessionVault(session_dir=tmp_path / "session_data")

    # 1. Initial state
    status = vault.get_portal_status("naukri")
    assert status["status"] == "DISCONNECTED"
    assert not vault.has_valid_session("naukri")
    assert not status["has_storage_state"]

    # 2. Update status to PENDING_OTP
    vault.update_status("naukri", status="PENDING_OTP", phone="+91 9876543210")
    status_pending = vault.get_portal_status("naukri")
    assert status_pending["status"] == "PENDING_OTP"
    assert status_pending["phone"] == "+91 9876543210"
    assert "****3210" in status_pending["masked_phone"]

    # 3. Save authenticated session with cookies
    storage_state = {
        "cookies": [
            {"name": "naukri_auth", "value": "xyz123", "domain": ".naukri.com", "path": "/"},
            {"name": "session_id", "value": "sess_abc", "domain": ".naukri.com", "path": "/"},
        ],
        "origins": [],
    }
    vault.save_session("naukri", phone="+91 9876543210", storage_state=storage_state, status="AUTHENTICATED")
    assert vault.has_valid_session("naukri")

    auth_status = vault.get_portal_status("naukri")
    assert auth_status["status"] == "AUTHENTICATED"
    assert auth_status["is_authenticated"]
    assert auth_status["cookie_count"] == 2
    assert auth_status["has_storage_state"]

    # 4. Verify storage_state and metadata persistence
    loaded_state = vault.load_storage_state("naukri")
    assert loaded_state is not None
    assert len(loaded_state["cookies"]) == 2

    # 5. Record sync result
    vault.record_sync_result("naukri", jobs_count=8)
    synced_status = vault.get_portal_status("naukri")
    assert synced_status["last_sync_jobs_count"] == 8
    assert synced_status["last_sync_at"] is not None

    # 6. Clear session
    vault.clear_session("naukri")
    cleared_status = vault.get_portal_status("naukri")
    assert cleared_status["status"] == "DISCONNECTED"
    assert not vault.has_valid_session("naukri")
    assert not vault.get_storage_state_path("naukri").exists()


def test_phone_number_masking():
    """Verify phone numbers are masked properly for privacy in UI views."""
    assert mask_phone_number("+91 9876543210") == "+91 ****3210"
    assert mask_phone_number("9876543210") == "9876****3210"
    assert mask_phone_number("") == ""
    assert mask_phone_number(None) == ""


def test_salary_floor_veto_enforcement():
    """Verify mandatory 4.0 LPA salary floor veto in JobScorer."""
    profile = load_candidate_profile()
    scorer = JobScorer(profile)

    # 1. Below floor: 2.5 - 3.5 LPA -> MUST BE VETOED
    job_low_range = JobExtractor.parse_job(
        title="Junior Python Developer",
        employer="SmallTech Solutions",
        description="We are hiring a Python Developer (0-1 yr exp). Stack: Python, Django, SQL. Salary: 2.5 - 3.5 LPA. Bengaluru.",
        location_raw="Bengaluru",
        salary_raw="2.5 - 3.5 LPA",
    )
    res_low = scorer.evaluate_job(job_low_range)
    assert res_low.is_vetoed
    assert res_low.decision_band == DecisionBand.REJECTED
    assert "below candidate's minimum floor of 4.0 LPA" in res_low.veto_reason

    # 2. Below floor: 3 LPA single figure -> MUST BE VETOED
    job_low_single = JobExtractor.parse_job(
        title="Associate Software Engineer",
        employer="EntryCorp",
        description="Looking for Python Developer. Fixed CTC: 3 LPA. Bengaluru.",
        location_raw="Bengaluru",
        salary_raw="3 LPA",
    )
    res_single = scorer.evaluate_job(job_low_single)
    assert res_single.is_vetoed
    assert "below candidate's minimum floor of 4.0 LPA" in res_single.veto_reason

    # 3. Below floor in INR notation: ₹ 2,50,000 - 3,50,000 P.A. -> MUST BE VETOED
    job_low_rupee = JobExtractor.parse_job(
        title="Python Web Trainee",
        employer="StartApp",
        description="Junior developer role in Bengaluru. Remuneration: ₹ 2,50,000 - ₹ 3,50,000 P.A.",
        location_raw="Bengaluru",
    )
    res_rupee = scorer.evaluate_job(job_low_rupee)
    assert res_rupee.is_vetoed
    assert "below candidate's minimum floor of 4.0 LPA" in res_rupee.veto_reason

    # 4. Meets floor: 4.0 - 6.5 LPA -> NOT VETOED
    job_meets = JobExtractor.parse_job(
        title="Junior Python Full Stack Engineer",
        employer="GrowthTech",
        description="Python Full Stack Developer. Python, Django, SQL, JS. Salary: 4.0 - 6.5 LPA. Bengaluru.",
        location_raw="Bengaluru",
        salary_raw="4.0 - 6.5 LPA",
    )
    res_meets = scorer.evaluate_job(job_meets)
    assert not res_meets.is_vetoed
    assert res_meets.total_score >= 80

    # 5. Overlapping boundary: 3.5 - 5.5 LPA (max is 5.5 >= 4.0) -> NOT VETOED
    job_overlap = JobExtractor.parse_job(
        title="Python Developer",
        employer="MidCorp",
        description="Python backend developer. Skills: Python, Django, SQL. CTC: 3.5 - 5.5 LPA. Bengaluru.",
        location_raw="Bengaluru",
        salary_raw="3.5 - 5.5 LPA",
    )
    res_overlap = scorer.evaluate_job(job_overlap)
    assert not res_overlap.is_vetoed

    # 7. Range with explicit LPA on first figure: 3.5 LPA - 5.5 LPA -> NOT VETOED
    job_lpa_explicit = JobExtractor.parse_job(
        title="Python Engineer",
        employer="TechCorp",
        description="Python backend developer. Skills: Python, Django, SQL. Bengaluru.",
        location_raw="Bengaluru",
        salary_raw="3.5 LPA - 5.5 LPA",
    )
    res_lpa_exp = scorer.evaluate_job(job_lpa_explicit)
    assert not res_lpa_exp.is_vetoed

    # 8. Monthly salary above floor: ₹ 50,000 / month (6.0 LPA) -> NOT VETOED
    job_monthly_high = JobExtractor.parse_job(
        title="Python Full Stack Engineer",
        employer="ModernWeb",
        description="Python, Django, SQL web developer role in Bengaluru. Remuneration: ₹ 50,000 / month.",
        location_raw="Bengaluru",
    )
    res_m_high = scorer.evaluate_job(job_monthly_high)
    assert not res_m_high.is_vetoed

    # 9. Monthly salary below floor: ₹ 25,000 / month (3.0 LPA) -> MUST BE VETOED
    job_monthly_low = JobExtractor.parse_job(
        title="Python Web Trainee",
        employer="SmallScale",
        description="Junior developer role in Bengaluru. Monthly stipend: ₹ 25,000 / month.",
        location_raw="Bengaluru",
    )
    res_m_low = scorer.evaluate_job(job_monthly_low)
    assert res_m_low.is_vetoed
    assert "below candidate's minimum floor of 4.0 LPA" in res_m_low.veto_reason


def test_bangalore_mysore_wfh_location_filter():
    """Verify strict location filter (strictly Bengaluru, Mysuru, or Remote / Work From Home)."""
    profile = load_candidate_profile()
    scorer = JobScorer(profile)

    # 1. Bengaluru -> ACCEPTED
    job_blr = JobExtractor.parse_job(
        title="Python Backend Developer",
        employer="BLR Corp",
        description="Python, Django, SQL. 0-1 yr exp. Salary: 5 LPA.",
        location_raw="Bengaluru, Karnataka",
        salary_raw="5 LPA",
    )
    assert not scorer.evaluate_job(job_blr).is_vetoed

    # 2. Mysuru -> ACCEPTED
    job_mys = JobExtractor.parse_job(
        title="Junior Python Developer",
        employer="Mysore Infotech",
        description="Python, SQL database. Freshers eligible. Salary: 4.5 LPA.",
        location_raw="Mysuru, Karnataka",
        salary_raw="4.5 LPA",
    )
    assert not scorer.evaluate_job(job_mys).is_vetoed

    # 3. Remote / Work From Home -> ACCEPTED
    job_wfh = JobExtractor.parse_job(
        title="Remote Python Engineer",
        employer="Global Tech",
        description="Work from home anywhere in India. Python, Django, REST APIs. Salary: 6 LPA.",
        location_raw="Remote (India)",
        salary_raw="6 LPA",
    )
    assert not scorer.evaluate_job(job_wfh).is_vetoed

    # 4. Hyderabad (On-site) -> MUST BE VETOED
    job_hyd = JobExtractor.parse_job(
        title="Python Developer",
        employer="Hyd Solutions",
        description="On-site position in HITEC City, Hyderabad. Python, Django. Salary: 6 LPA.",
        location_raw="Hyderabad",
        salary_raw="6 LPA",
    )
    res_hyd = scorer.evaluate_job(job_hyd)
    assert res_hyd.is_vetoed
    assert "outside candidate's strict locations" in res_hyd.veto_reason

    # 5. Pune (On-site) -> MUST BE VETOED
    job_pune = JobExtractor.parse_job(
        title="Python Developer",
        employer="Pune Tech Park",
        description="On-site position in Hinjewadi, Pune. Python, Django. Salary: 5 LPA.",
        location_raw="Pune",
        salary_raw="5 LPA",
    )
    res_pune = scorer.evaluate_job(job_pune)
    assert res_pune.is_vetoed
    assert "outside candidate's strict locations" in res_pune.veto_reason

    # 6. Pune job with Bangalore mentioned in description -> MUST STILL BE VETOED!
    job_pune_mentions_blr = JobExtractor.parse_job(
        title="Python Developer",
        employer="Pune Tech Labs",
        description="Our headquarters are in Bangalore, but this opening is strictly located at our Pune development center. Salary: 5 LPA.",
        location_raw="Pune",
        salary_raw="5 LPA",
    )
    res_pune_blr = scorer.evaluate_job(job_pune_mentions_blr)
    assert res_pune_blr.is_vetoed
    assert "outside candidate's strict locations" in res_pune_blr.veto_reason

    # 7. Unlisted city (Jaipur) -> MUST BE VETOED!
    job_jaipur = JobExtractor.parse_job(
        title="Python Developer",
        employer="Jaipur Software",
        description="Junior Python engineer role in Jaipur. Salary: 5 LPA.",
        location_raw="Jaipur",
        salary_raw="5 LPA",
    )
    res_jaipur = scorer.evaluate_job(job_jaipur)
    assert res_jaipur.is_vetoed
    assert "outside candidate's strict locations" in res_jaipur.veto_reason


def test_portal_browser_connectors_otp_flow(tmp_path, monkeypatch):
    """Test OTP login flow and job scraping on Naukri, Internshala, and LinkedIn connectors."""
    vault = SessionVault(session_dir=tmp_path / "sessions")

    # Fast mock for external network navigations to avoid 20s timeouts on external sites
    monkeypatch.setattr(NaukriBrowserConnector, "_portal_send_otp", lambda self, page, phone: True)
    monkeypatch.setattr(InternshalaBrowserConnector, "_portal_send_otp", lambda self, page, phone: True)
    monkeypatch.setattr(LinkedInBrowserConnector, "_portal_send_otp", lambda self, page, phone: True)
    monkeypatch.setattr(NaukriBrowserConnector, "_scrape_portal_jobs", lambda self, page, q, l, limit: self._get_fallback_genuine_jobs(q, l, limit))
    monkeypatch.setattr(InternshalaBrowserConnector, "_scrape_portal_jobs", lambda self, page, q, l, limit: self._get_fallback_genuine_jobs(q, l, limit))
    monkeypatch.setattr(LinkedInBrowserConnector, "_scrape_portal_jobs", lambda self, page, q, l, limit: self._get_fallback_genuine_jobs(q, l, limit))

    connectors = [
        NaukriBrowserConnector(session_vault=vault),
        InternshalaBrowserConnector(session_vault=vault),
        LinkedInBrowserConnector(session_vault=vault),
    ]

    for conn in connectors:
        pid = conn.platform_id

        # 1. Verify initially disconnected
        assert not conn.has_valid_session()

        # 2. Send OTP
        res_send = conn.send_otp("+91 9876543210")
        assert res_send["status"] == "PENDING_OTP"
        assert res_send["portal"] == pid

        # 3. Verify OTP
        res_verify = conn.verify_otp("123456")
        assert res_verify["status"] == "AUTHENTICATED"
        assert conn.has_valid_session()

        # 4. Discover jobs
        jobs = conn.discover_jobs(query="python developer", location="Bengaluru", limit=3)
        assert len(jobs) > 0
        for j in jobs:
            assert j.source_platform == pid
            # Check candidate constraints: location and salary
            assert ("bengaluru" in j.location.lower() or "mysuru" in j.location.lower() or "remote" in j.location.lower() or j.work_arrangement == "Remote")
            if j.max_salary_lpa is not None:
                assert j.max_salary_lpa >= 4.0

        # 5. Clear session
        assert conn.clear_session()
        assert not conn.has_valid_session()


def test_dashboard_portal_endpoints(tmp_path, monkeypatch):
    """Verify Flask dashboard portal API endpoints with isolated session vault."""
    db_file = tmp_path / "test_dash.db"
    repo = ApplicationRepository(db_path=db_file)
    vault = SessionVault(session_dir=tmp_path / "test_sessions")

    monkeypatch.setattr(NaukriBrowserConnector, "_portal_send_otp", lambda self, page, phone: True)
    monkeypatch.setattr(NaukriBrowserConnector, "_scrape_portal_jobs", lambda self, page, q, l, limit: self._get_fallback_genuine_jobs(q, l, limit))

    app = create_app(repo=repo, session_vault=vault)
    client = app.test_client()

    # 1. Check initial portal statuses
    resp_status = client.get("/api/portals/status")
    assert resp_status.status_code == 200
    data_status = resp_status.get_json()
    assert data_status["status"] == "success"
    assert "naukri" in data_status["portals"]
    assert "internshala" in data_status["portals"]
    assert "linkedin" in data_status["portals"]

    # 2. Send OTP for Naukri
    resp_send = client.post("/api/portals/send_otp", json={"portal": "naukri", "phone": "9876543210"})
    assert resp_send.status_code == 200
    data_send = resp_send.get_json()
    assert data_send["status"] == "PENDING_OTP"

    # 3. Verify OTP for Naukri
    resp_verify = client.post("/api/portals/verify_otp", json={"portal": "naukri", "otp": "998877"})
    assert resp_verify.status_code == 200
    data_verify = resp_verify.get_json()
    assert data_verify["status"] == "AUTHENTICATED"

    # 4. Trigger genuine job sync
    resp_sync = client.post("/api/portals/sync", json={"portal": "naukri"})
    assert resp_sync.status_code == 200
    data_sync = resp_sync.get_json()
    assert data_sync["status"] == "success"
    assert data_sync["total_scraped"] > 0
    assert data_sync["qualified"] > 0

    # Verify jobs were stored in database
    apps = repo.get_applications(source_platform="naukri")
    assert len(apps) > 0

    # 5. Disconnect portal
    resp_disc = client.post("/api/portals/disconnect", json={"portal": "naukri"})
    assert resp_disc.status_code == 200
    data_disc = resp_disc.get_json()
    assert data_disc["status"] == "success"

    # 6. Index page render check
    resp_index = client.get("/")
    assert resp_index.status_code == 200
    html = resp_index.get_data(as_text=True)
    assert "Live Portal Connection Center" in html
    assert "Naukri India" in html
    assert "Internshala" in html
    assert "LinkedIn Jobs" in html
