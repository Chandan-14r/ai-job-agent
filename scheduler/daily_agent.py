"""Autonomous Daily Job Scraping and Matching Agent for Kiran A N.

Discovers genuine, active, real-world job postings across connected portals
(Naukri, Internshala, LinkedIn) and verified technical employer ATS boards (Greenhouse).
Applies deterministic 100-point scoring, strict salary floor veto (≥4.0 LPA),
strict location filtering (Bengaluru, Mysuru, Remote/WFH), ATS resume generation,
and Telegram notification dispatch.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from candidate_profile.loader import load_candidate_profile, CandidateProfile
from database.repository import ApplicationRepository, get_default_repository
from telegram_notifications.notifier import TelegramNotifier
from telegram_notifications.templates import format_new_job_found, clean
from application_workflow.engine import ApplicationEngine
from job_sources.connectors.session_vault import SessionVault
from job_sources.connectors.naukri_browser import NaukriBrowserConnector
from job_sources.connectors.internshala_browser import InternshalaBrowserConnector
from job_sources.connectors.linkedin_browser import LinkedInBrowserConnector
from job_sources.connectors.live_discovery import LivePublicDiscoverySource
from job_parser.extractor import ParsedJob

logger = logging.getLogger("daily_agent")


class AutonomousDailyScrapingAgent:
    """Production autonomous agent for harvesting genuine, verified jobs."""

    def __init__(
        self,
        profile: Optional[CandidateProfile] = None,
        repository: Optional[ApplicationRepository] = None,
        notifier: Optional[TelegramNotifier] = None,
        session_vault: Optional[SessionVault] = None,
        mode: str = "DISCOVERY_MODE",
    ):
        self.profile = profile or load_candidate_profile()
        self.repo = repository or get_default_repository()
        self.notifier = notifier or TelegramNotifier()
        self.vault = session_vault or SessionVault()
        self.mode = mode

        self.engine = ApplicationEngine(
            profile=self.profile,
            repository=self.repo,
            notifier=self.notifier,
            mode=self.mode,
        )

        # Initialize portal connectors with session vault
        self.naukri = NaukriBrowserConnector(session_vault=self.vault)
        self.internshala = InternshalaBrowserConnector(session_vault=self.vault)
        self.linkedin = LinkedInBrowserConnector(session_vault=self.vault)
        self.live_ats = LivePublicDiscoverySource()

    def run_daily_cycle(self, limit_per_source: int = 15) -> Dict[str, Any]:
        """
        Execute a complete autonomous daily job harvesting and evaluation cycle.
        Queries each platform, filters through deterministic rubric, deduplicates,
        stores qualified listings, generates ATS resumes, and sends Telegram alerts.
        """
        start_ts = datetime.utcnow().isoformat()
        logger.info(f"[DailyAgent] Starting autonomous job discovery cycle at {start_ts}...")

        all_scraped: List[ParsedJob] = []
        source_breakdown: Dict[str, Dict[str, int]] = {}

        # 1. Platform Connectors Configuration
        search_targets = [
            ("naukri", self.naukri, "python developer", "Bengaluru"),
            ("internshala", self.internshala, "python django", "bangalore"),
            ("linkedin", self.linkedin, "python developer", "Bengaluru"),
            ("greenhouse_ats", self.live_ats, "python", "India"),
        ]

        for name, connector, query, location in search_targets:
            logger.info(f"[DailyAgent] Fetching verified listings from '{name}'...")
            try:
                found = connector.discover_jobs(query=query, location=location, limit=limit_per_source)
                logger.info(f"[DailyAgent] '{name}' returned {len(found)} candidate postings.")
                all_scraped.extend(found)
                source_breakdown[name] = {"scraped": len(found), "qualified": 0, "vetoed": 0}
            except Exception as e:
                logger.warning(f"[DailyAgent] Source '{name}' encountered an error: {e}")
                source_breakdown[name] = {"scraped": 0, "qualified": 0, "vetoed": 0, "error": str(e)}

        # 2. Process and Score Discovered Jobs
        total_qualified = 0
        total_vetoed = 0
        qualified_records = []

        for job in all_scraped:
            src_name = job.source_platform or "unknown"
            if src_name not in source_breakdown:
                source_breakdown[src_name] = {"scraped": 0, "qualified": 0, "vetoed": 0}

            try:
                app_record = self.engine.process_job(job)
                if app_record:
                    if app_record.application_status in [
                        "QUALIFIED", "READY_FOR_APPLICATION", "AWAITING_MANUAL_ACTION", "SUBMITTED", "APPLICATION_CONFIRMED"
                    ]:
                        total_qualified += 1
                        source_breakdown[src_name]["qualified"] += 1
                        qualified_records.append({
                            "id": app_record.id,
                            "employer": app_record.employer,
                            "title": app_record.job_title,
                            "score": app_record.matching_score,
                            "location": app_record.location,
                            "salary": app_record.salary_range,
                            "url": app_record.job_url,
                            "resume_version": app_record.selected_resume_version,
                        })
                    else:
                        total_vetoed += 1
                        source_breakdown[src_name]["vetoed"] += 1
            except Exception as err:
                logger.error(f"[DailyAgent] Error processing job '{job.title}' at '{job.employer}': {err}")

        # 3. Update Portal Sync Metadata in Vault
        for name in ["naukri", "internshala", "linkedin"]:
            if name in source_breakdown:
                self.vault.record_sync_result(name, jobs_count=source_breakdown[name]["scraped"])

        # 4. Generate Audit Daily Report
        reports = self.engine.generate_daily_report()

        # 5. Automatically Dispatch Qualified Jobs & 12-Hour Summary to Telegram
        telegram_dispatches = 0
        if self.notifier and self.notifier.is_configured:
            logger.info("[DailyAgent] Dispatching job alerts and 12-hour summary to Telegram...")
            cycle_tag = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            # Send individual job cards for top qualified jobs (up to 5 per cycle)
            for q in qualified_records[:5]:
                app_obj = self.repo.get_application_by_id(q["id"])
                if app_obj:
                    card_msg = format_new_job_found(app_obj)
                    sent = self.notifier.send_message(card_msg, event_id=f"tg_card_{app_obj.id}_{cycle_tag}")
                    if sent:
                        telegram_dispatches += 1

            # Send 12-Hour Executive Summary (always delivered per cycle)
            summary_msg = self._build_cycle_telegram_summary(
                total_scraped=len(all_scraped),
                total_qualified=total_qualified,
                total_vetoed=total_vetoed,
                sources=source_breakdown,
                qualified_jobs=qualified_records,
            )
            self.notifier.send_message(summary_msg, event_id=f"summary_{cycle_tag}")
            logger.info(f"[DailyAgent] Telegram dispatch complete ({telegram_dispatches} cards + executive report).")

        end_ts = datetime.utcnow().isoformat()
        logger.info(
            f"[DailyAgent] Cycle complete: {len(all_scraped)} scraped, "
            f"{total_qualified} qualified, {total_vetoed} vetoed/rejected."
        )

        # Persist harvest state for autonomous stale detection across server restarts
        try:
            state_path = Path(__file__).resolve().parent.parent / "data" / "harvest_state.json"
            state_data = {
                "last_harvest_timestamp": end_ts,
                "total_scraped": len(all_scraped),
                "total_qualified": total_qualified,
                "total_vetoed": total_vetoed,
                "telegram_dispatches": telegram_dispatches,
            }
            with open(state_path, "w", encoding="utf-8") as sf:
                json.dump(state_data, sf, indent=2)
        except Exception as state_err:
            logger.warning(f"[DailyAgent] Could not persist harvest_state.json: {state_err}")

        return {
            "status": "success",
            "start_time": start_ts,
            "end_time": end_ts,
            "total_scraped": len(all_scraped),
            "total_qualified": total_qualified,
            "total_vetoed": total_vetoed,
            "telegram_dispatches": telegram_dispatches,
            "sources": source_breakdown,
            "qualified_jobs": qualified_records,
            "reports": reports,
            "kpi_summary": self.repo.get_kpi_summary(),
        }

    def _build_cycle_telegram_summary(
        self,
        total_scraped: int,
        total_qualified: int,
        total_vetoed: int,
        sources: Dict[str, Any],
        qualified_jobs: List[Dict[str, Any]],
    ) -> str:
        kpis = self.repo.get_kpi_summary()
        sources_line = " • ".join([f"{s.capitalize()}: {info.get('scraped', 0)}" for s, info in sources.items()])

        top_jobs_text = ""
        for i, q in enumerate(qualified_jobs[:5], 1):
            salary = q.get("salary") or "Market Standard (≥4.0 LPA)"
            top_jobs_text += (
                f"\n<b>{i}. {clean(q['employer'])}</b> – {clean(q['title'])}\n"
                f"   ⭐ Match Score: <b>{q['score']}/100</b>\n"
                f"   📍 Location: {clean(q['location'])}\n"
                f"   💰 Compensation: {clean(salary)}\n"
                f"   📄 Recommended Resume: <code>{clean(q.get('resume_version', 'RESUME_A'))}</code>\n"
                f"   🔗 <a href='{clean(q['url'])}'>View &amp; Apply on Employer Portal</a>\n"
            )

        if not top_jobs_text:
            top_jobs_text = "<i>No new openings discovered this cycle. Actively monitoring existing verified opportunities.</i>\n"

        return (
            "🤖 <b>12-HOUR AUTONOMOUS JOB HARVEST REPORT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Candidate: <b>{clean(self.profile.full_name)}</b>\n"
            f"Role: <b>Python Full Stack Developer (0–2 Yrs)</b>\n"
            f"Constraints: <b>Min ₹4.0 LPA | Bengaluru, Mysuru &amp; Remote</b>\n\n"
            f"🔍 <b>Scraped Listings:</b> {total_scraped} ({sources_line})\n"
            f"✅ <b>Qualified (≥4.0 LPA):</b> {total_qualified}\n"
            f"🚫 <b>Vetoed (&lt;4.0 LPA / Non-Target):</b> {total_vetoed}\n"
            f"📊 <b>Total Database Jobs:</b> {kpis.get('total_applications', 0)}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"<b>🎯 Top Matched Opportunities:</b>\n"
            f"{top_jobs_text}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Running on 12-hour automated schedule. Zero fabricated claims.</i>"
        )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    agent = AutonomousDailyScrapingAgent()
    res = agent.run_daily_cycle(limit_per_source=10)
    print("\n" + "=" * 60)
    print("   AUTONOMOUS DAILY AGENT EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Total Scraped:   {res['total_scraped']}")
    print(f"Total Qualified: {res['total_qualified']}")
    print(f"Total Vetoed:    {res['total_vetoed']}")
    print("\n[Source Breakdown]")
    for s, info in res["sources"].items():
        print(f"  • {s:15s}: Scraped={info.get('scraped', 0)} | Qualified={info.get('qualified', 0)}")
    print("\n[Qualified Listings]")
    for q in res["qualified_jobs"][:10]:
        print(f"  • [{q['score']}/100] {q['employer']} - {q['title']} ({q['location']})")
        print(f"    URL: {q['url']}")


if __name__ == "__main__":
    main()
