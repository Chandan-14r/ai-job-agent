"""Tests for AutonomousDailyScrapingAgent and /api/run_daily_agent Endpoint."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from candidate_profile.loader import load_candidate_profile
from database.repository import ApplicationRepository
from dashboard.app import create_app
from job_parser.extractor import JobExtractor, ParsedJob
from job_sources.connectors.session_vault import SessionVault
from scheduler.daily_agent import AutonomousDailyScrapingAgent


def test_daily_agent_execution_cycle(tmp_path, monkeypatch):
    """Verify AutonomousDailyScrapingAgent filters, scores, and saves qualified jobs."""
    db_file = tmp_path / "test_agent.db"
    repo = ApplicationRepository(db_path=db_file)
    vault = SessionVault(session_dir=tmp_path / "agent_sessions")
    profile = load_candidate_profile()

    # Create test sample jobs:
    # 1. Qualified Python Full Stack Developer (BLR, 5 LPA)
    job_qualified = JobExtractor.parse_job(
        title="Junior Python Full Stack Developer",
        employer="CloudMatrix Technologies",
        description="Looking for Junior Python Full Stack Developer (0-1 yr exp). Stack: Python, Django, SQL, JS. CTC: 5.0 - 7.0 LPA. Bengaluru.",
        job_url="https://www.naukri.com/job-listings-python-cloudmatrix-9988",
        source_platform="naukri",
        location_raw="Bengaluru, Karnataka",
        salary_raw="5.0 - 7.0 LPA",
        verification_status="VERIFIED_ACTIVE",
    )
    # 2. Vetoed: Non-developer role (UI/UX Designer)
    job_designer = JobExtractor.parse_job(
        title="UI/UX Designer",
        employer="DesignStudio Pvt Ltd",
        description="Figma, Wireframing, UI Design. CTC: 5.0 LPA. Bengaluru.",
        job_url="https://internshala.com/job/detail/ui-ux-designer-1234",
        source_platform="internshala",
        location_raw="Bengaluru",
        salary_raw="5.0 LPA",
    )
    # 3. Vetoed: Below 4.0 LPA floor (2.5 - 3.5 LPA)
    job_low_salary = JobExtractor.parse_job(
        title="Python Web Developer",
        employer="SmallTech Agency",
        description="Python Django. CTC: 2.5 - 3.5 LPA. Bengaluru.",
        job_url="https://www.linkedin.com/jobs/view/smalltech-python-123",
        source_platform="linkedin",
        location_raw="Bengaluru",
        salary_raw="2.5 - 3.5 LPA",
    )
    # 4. Vetoed: Non-target location (Hyderabad on-site)
    job_hyd = JobExtractor.parse_job(
        title="Python Backend Engineer",
        employer="HydTech Solutions",
        description="Python backend developer. CTC: 6.0 LPA. Hyderabad.",
        job_url="https://job-boards.greenhouse.io/hydtech/jobs/5544",
        source_platform="greenhouse_ats",
        location_raw="Hyderabad, Telangana",
        salary_raw="6.0 LPA",
    )

    agent = AutonomousDailyScrapingAgent(
        profile=profile,
        repository=repo,
        session_vault=vault,
        mode="DISCOVERY_MODE",
    )

    # Monkeypatch discovery methods to return test batch
    monkeypatch.setattr(agent.naukri, "discover_jobs", lambda *args, **kwargs: [job_qualified])
    monkeypatch.setattr(agent.internshala, "discover_jobs", lambda *args, **kwargs: [job_designer])
    monkeypatch.setattr(agent.linkedin, "discover_jobs", lambda *args, **kwargs: [job_low_salary])
    monkeypatch.setattr(agent.live_ats, "discover_jobs", lambda *args, **kwargs: [job_hyd])

    res = agent.run_daily_cycle(limit_per_source=5)

    assert res["status"] == "success"
    assert res["total_scraped"] == 4
    assert res["total_qualified"] == 1
    assert res["total_vetoed"] == 3

    # Verify qualified job is in database
    apps = repo.get_applications()
    assert len(apps) >= 1
    qualified_app = next((a for a in apps if a.employer == "CloudMatrix Technologies"), None)
    assert qualified_app is not None
    assert qualified_app.matching_score >= 80
    assert qualified_app.application_status == "QUALIFIED"


def test_daily_agent_dashboard_api(tmp_path, monkeypatch):
    """Verify POST /api/run_daily_agent endpoint in dashboard."""
    db_file = tmp_path / "test_api.db"
    repo = ApplicationRepository(db_path=db_file)
    vault = SessionVault(session_dir=tmp_path / "api_sessions")

    app = create_app(repo=repo, session_vault=vault)
    client = app.test_client()

    sample_job = JobExtractor.parse_job(
        title="Associate Software Engineer - Python",
        employer="Apex Analytics",
        description="Python, Django, SQL database integration. CTC: 5.5 LPA. Bengaluru.",
        job_url="https://www.naukri.com/job-listings-apex-python-3322",
        source_platform="naukri",
        location_raw="Bengaluru",
        salary_raw="5.5 LPA",
        verification_status="VERIFIED_ACTIVE",
    )

    from job_sources.connectors.naukri_browser import NaukriBrowserConnector
    monkeypatch.setattr(NaukriBrowserConnector, "discover_jobs", lambda *args, **kwargs: [sample_job])
    monkeypatch.setattr("scheduler.daily_agent.InternshalaBrowserConnector.discover_jobs", lambda *args, **kwargs: [])
    monkeypatch.setattr("scheduler.daily_agent.LinkedInBrowserConnector.discover_jobs", lambda *args, **kwargs: [])
    monkeypatch.setattr("scheduler.daily_agent.LivePublicDiscoverySource.discover_jobs", lambda *args, **kwargs: [])

    resp = client.post("/api/run_daily_agent", json={"limit_per_source": 5})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    assert data["total_scraped"] == 1
    assert data["total_qualified"] == 1


def test_emergency_stop_blocks_daily_agent(tmp_path):
    """Verify emergency stop prevents execution of /api/run_daily_agent."""
    db_file = tmp_path / "test_stop.db"
    repo = ApplicationRepository(db_path=db_file)
    vault = SessionVault(session_dir=tmp_path / "stop_sessions")

    app = create_app(repo=repo, session_vault=vault)
    client = app.test_client()

    # Trigger emergency stop
    res_stop = client.post("/api/emergency_stop", json={})
    assert res_stop.status_code == 200
    assert res_stop.get_json()["emergency_stop"] is True

    # Attempt to run daily agent
    resp = client.post("/api/run_daily_agent", json={})
    assert resp.status_code == 400
    data = resp.get_json()
    assert data["status"] == "error"
    assert "Emergency Stop is active" in data["message"]
