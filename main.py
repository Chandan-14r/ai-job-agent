"""Antigravity Autonomous AI Job Application Agent for Kiran A N.

Production Entrypoint supporting CLI modes, discovery, dry-runs, and local dashboard.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from candidate_profile.loader import load_candidate_profile, get_missing_candidate_fields
from database.repository import ApplicationRepository, get_default_repository
from telegram_notifications.notifier import TelegramNotifier
from application_workflow.engine import ApplicationEngine
from resume_generator.builder_docx import generate_docx_resume, ResumeVariant
from resume_generator.builder_pdf import generate_pdf_resume
from job_sources.connectors.synthetic_source import SyntheticJobSource
from scheduler.runner import BackgroundJobScheduler
from dashboard.app import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("main")


def parse_args():
    parser = argparse.ArgumentParser(description="Antigravity Autonomous AI Job Application Agent")
    parser.add_argument(
        "--mode",
        choices=["DISCOVERY_MODE", "ASSISTED_APPLICATION_MODE", "AUTHORIZED_AUTO_APPLY_MODE"],
        default="DISCOVERY_MODE",
        help="System operational mode (Default: DISCOVERY_MODE)",
    )
    parser.add_argument("--dry-run", action="store_true", help="Execute in safe simulation mode")
    parser.add_argument("--discover", action="store_true", help="Run a job discovery and scoring cycle")
    parser.add_argument("--live", action="store_true", help="Query live public employer ATS boards (Mode 1 Discovery)")
    parser.add_argument("--generate-resumes", action="store_true", help="Generate Resumes A, B, C in DOCX & PDF")
    parser.add_argument("--dashboard", action="store_true", help="Launch the local monitoring web dashboard")
    parser.add_argument("--port", type=int, default=5000, help="Port for the dashboard web server")
    parser.add_argument("--scheduler", action="store_true", help="Run scheduler for recurring discovery")
    parser.add_argument("--report", action="store_true", help="Generate daily summary reports (CSV & MD)")
    parser.add_argument("--test-telegram", action="store_true", help="Send a dry-run test ping to Telegram")
    parser.add_argument("--status", action="store_true", help="Display current system status and candidate profile checklist")
    parser.add_argument("--approve-activation", action="store_true", help="Record explicit candidate approval for Mode 3")
    parser.add_argument("--daily-agent", action="store_true", help="Run the autonomous daily scraper across Naukri, Internshala, LinkedIn, and ATS boards")
    return parser.parse_args()


def main():
    args = parse_args()
    profile = load_candidate_profile()
    repo = get_default_repository()
    notifier = TelegramNotifier(dry_run=args.dry_run)

    print("\n" + "=" * 70)
    print("   ANTIGRAVITY AUTONOMOUS AI JOB APPLICATION AGENT")
    print(f"   Candidate: {profile.full_name} | Location: {profile.contact.current_location}")
    print(f"   Degree: B.E. CSE (CGPA: 7.98) | Training: QSpiders Python Full Stack")
    print(f"   Active Mode: {args.mode} | Dry-Run: {args.dry_run}")
    print("=" * 70 + "\n")

    engine = ApplicationEngine(
        profile=profile,
        repository=repo,
        notifier=notifier,
        mode=args.mode,
        pre_activation_approved=args.approve_activation,
    )

    if args.status:
        print("[Candidate Profile Status & Missing Information Checklist]")
        missing = get_missing_candidate_fields(profile)
        if missing:
            print(f"ATTENTION: {len(missing)} fields require candidate input (Zero Fabrication Policy):")
            for m in missing:
                print(f"  • {m['field']}: {m['reason']}")
        else:
            print("All candidate profile fields verified.")
        kpis = repo.get_kpi_summary()
        print("\n[Application Tracking KPIs]")
        for k, v in kpis.items():
            print(f"  • {k}: {v}")
        return

    if args.daily_agent:
        print("[Starting Autonomous Daily Scraping Agent...]")
        from scheduler.daily_agent import AutonomousDailyScrapingAgent
        agent = AutonomousDailyScrapingAgent(profile=profile, repository=repo, notifier=notifier, mode=args.mode)
        res = agent.run_daily_cycle(limit_per_source=15)
        print("\n" + "=" * 60)
        print("   AUTONOMOUS DAILY AGENT HARVEST SUMMARY")
        print("=" * 60)
        print(f"Total Scraped:   {res['total_scraped']}")
        print(f"Total Qualified: {res['total_qualified']}")
        print(f"Total Vetoed:    {res['total_vetoed']}")
        print("\n[Source Breakdown]")
        for s, info in res["sources"].items():
            print(f"  • {s:15s}: Scraped={info.get('scraped', 0)} | Qualified={info.get('qualified', 0)}")
        print("\n[Qualified Listings Saved to Database]")
        for q in res["qualified_jobs"][:10]:
            print(f"  • [{q['score']}/100] {q['employer']} - {q['title']} ({q['location']})")
            print(f"    URL: {q['url']}")
        return

    if args.generate_resumes:
        print("[Generating ATS Resumes for Variants A, B, and C...]")
        for variant in [ResumeVariant.RESUME_A, ResumeVariant.RESUME_B, ResumeVariant.RESUME_C]:
            docx = generate_docx_resume(profile, variant=variant)
            pdf = generate_pdf_resume(profile, variant=variant)
            print(f"  • {variant.value}:")
            print(f"      DOCX: {docx}")
            print(f"      PDF:  {pdf}")
        print("Resume generation complete.\n")

    if args.test_telegram:
        print("[Executing Telegram Connection Test...]")
        if notifier.is_configured:
            msg = (
                "🤖 <b>ANTIGRAVITY AGENT CONNECTION TEST</b>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                f"Candidate: <b>{profile.full_name}</b>\n"
                "System: <code>Operational</code>\n"
                f"Mode: <code>{args.mode}</code>\n"
                "<i>Telegram bot notifications successfully verified.</i>"
            )
            success = notifier.send_message(msg, event_id="connection_test")
            print(f"Telegram dispatch result: {'SUCCESS' if success else 'FAILED'}")
        else:
            print("Telegram credentials not configured in .env. Mock dispatch verified.")

    if args.discover or args.live or args.dry_run:
        print(f"[Starting Job Discovery Run (Mode: {args.mode}, Live ATS: {args.live}, Dry-Run: {args.dry_run})...]")
        if args.live:
            from job_sources.connectors.live_discovery import LivePublicDiscoverySource
            source = LivePublicDiscoverySource()
            jobs = source.discover_jobs(query="python", location="India", limit=15)
        else:
            source = SyntheticJobSource()
            jobs = source.discover_jobs(limit=15)
        print(f"Discovered {len(jobs)} candidate opportunities. Evaluating 100-point rubric...\n")

        qualified = 0
        vetoed = 0
        for j in jobs:
            app = engine.process_job(j)
            if app:
                if app.application_status in ["QUALIFIED", "READY_FOR_APPLICATION", "AWAITING_MANUAL_ACTION", "SUBMITTED", "APPLICATION_CONFIRMED"]:
                    qualified += 1
                    print(f"  [QUALIFIED] {app.employer} - {app.job_title} | Score: {app.matching_score}/100 | Resume: {app.selected_resume_version}")
                else:
                    vetoed += 1
                    print(f"  [REJECTED/VETOED] {app.employer} - {app.job_title} | Score: {app.matching_score}/100 | Reason: {app.error_log}")

        print(f"\nDiscovery Cycle Complete: {qualified} Qualified, {vetoed} Rejected / Vetoed.")
        reports = engine.generate_daily_report()
        print(f"Daily Reports Generated:\n  CSV: {reports['csv']}\n  MD:  {reports['md']}\n")

    if args.report:
        reports = engine.generate_daily_report()
        print(f"Daily Reports exported to:\n  CSV: {reports['csv']}\n  MD:  {reports['md']}")

    if args.dashboard:
        print(f"[Launching Local Monitoring Dashboard on http://127.0.0.1:{args.port}]...")
        # Start Autonomous Background Harvester daemon (12-hour interval, 15s startup delay)
        def run_dashboard_bg_harvest():
            try:
                from scheduler.daily_agent import AutonomousDailyScrapingAgent
                agent = AutonomousDailyScrapingAgent(profile=profile, repository=repo, notifier=notifier, mode=args.mode)
                agent.run_daily_cycle(limit_per_source=15)
            except Exception as e:
                logger.error(f"[Background Harvester] Error in scheduled run: {e}")

        bg_scheduler = BackgroundJobScheduler(
            run_discovery_fn=run_dashboard_bg_harvest,
            interval_minutes=720,
            initial_delay_seconds=15,
        )
        bg_scheduler.start()
        print("[Autonomous Background Harvester Active: checks Naukri, Internshala & ATS feeds every 12 hours.]\n")

        flask_app = create_app(repo=repo, current_mode=args.mode)
        try:
            # Bind to 0.0.0.0 so mobile phones on local WiFi/LAN can open the dashboard
            flask_app.run(host="0.0.0.0", port=args.port, debug=False)
        finally:
            bg_scheduler.stop()

    if args.scheduler:
        def scheduled_cycle():
            from scheduler.daily_agent import AutonomousDailyScrapingAgent
            agent = AutonomousDailyScrapingAgent(profile=profile, repository=repo, notifier=notifier, mode=args.mode)
            agent.run_daily_cycle(limit_per_source=15)

        scheduler = BackgroundJobScheduler(run_discovery_fn=scheduled_cycle, interval_minutes=60)
        scheduler.start()
        print("[Scheduler running in background. Press Ctrl+C to stop...]")
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
            print("Scheduler halted.")


if __name__ == "__main__":
    main()
