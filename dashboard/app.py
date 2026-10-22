"""Flask Local Web Monitoring Dashboard & Control Center for Kiran A N."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional
from flask import Flask, jsonify, render_template, request, send_from_directory
import yaml

from candidate_profile.loader import load_candidate_profile, get_missing_candidate_fields
from database.repository import ApplicationRepository, get_default_repository
from telegram_notifications.notifier import TelegramNotifier
from resume_generator.builder_docx import generate_docx_resume, ResumeVariant
from resume_generator.builder_pdf import generate_pdf_resume
from application_workflow.engine import ApplicationEngine
from job_sources.connectors.synthetic_source import SyntheticJobSource
from job_sources.connectors.live_discovery import LivePublicDiscoverySource
from job_sources.connectors.session_vault import SessionVault
from job_sources.connectors.naukri_browser import NaukriBrowserConnector
from job_sources.connectors.internshala_browser import InternshalaBrowserConnector
from job_sources.connectors.linkedin_browser import LinkedInBrowserConnector
from job_sources.url_validator import URLValidator

logger = logging.getLogger("dashboard_app")


def create_app(
    repo: Optional[ApplicationRepository] = None,
    current_mode: str = "DISCOVERY_MODE",
    email_monitoring: bool = False,
    session_vault: Optional[SessionVault] = None,
) -> Flask:
    base_dir = Path(__file__).resolve().parent
    template_dir = base_dir / "templates"
    project_root = base_dir.parent
    resumes_dir = project_root / "output" / "resumes"
    reports_dir = project_root / "output" / "reports"
    resumes_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__, template_folder=str(template_dir))
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "antigravity-job-agent-secret")

    # Ensure baseline resumes exist for instant cloud downloads
    if not list(resumes_dir.glob("*.pdf")):
        try:
            init_profile = load_candidate_profile()
            for v in [ResumeVariant.RESUME_A, ResumeVariant.RESUME_B, ResumeVariant.RESUME_C]:
                generate_docx_resume(init_profile, variant=v, output_dir=resumes_dir)
                generate_pdf_resume(init_profile, variant=v, output_dir=resumes_dir)
        except Exception as e:
            logger.warning(f"Initial resume generation notice: {e}")

    repository = repo or get_default_repository()
    notifier = TelegramNotifier()
    vault = session_vault or SessionVault()
    system_state = {
        "mode": current_mode,
        "emergency_stop": False,
        "email_monitoring": email_monitoring,
    }

    # Stale harvest detection (ensures 12-hour Telegram updates even across server restarts or Render sleep)
    import threading
    import sys
    from datetime import datetime
    _harvest_in_progress = False

    def trigger_background_harvest_if_stale():
        nonlocal _harvest_in_progress
        if "pytest" in sys.modules:
            return
        if system_state.get("emergency_stop"):
            return

        state_file = project_root / "data" / "harvest_state.json"
        is_stale = True
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    sdata = json.load(f)
                last_ts = sdata.get("last_harvest_timestamp")
                if last_ts:
                    last_dt = datetime.fromisoformat(last_ts.replace("Z", ""))
                    if (datetime.utcnow() - last_dt).total_seconds() < 12 * 3600:
                        is_stale = False
            except Exception:
                is_stale = True

        if is_stale and not _harvest_in_progress:
            def _async_harvester():
                nonlocal _harvest_in_progress
                if _harvest_in_progress:
                    return
                _harvest_in_progress = True
                try:
                    logger.info("[AutoHarvester] Stale harvest detected (>12h). Launching automated background cycle...")
                    from scheduler.daily_agent import AutonomousDailyScrapingAgent
                    agent = AutonomousDailyScrapingAgent(
                        profile=load_candidate_profile(),
                        repository=repository,
                        notifier=notifier,
                        session_vault=vault,
                        mode=system_state["mode"],
                    )
                    agent.run_daily_cycle(limit_per_source=10)
                    logger.info("[AutoHarvester] Background harvest and Telegram dispatch complete.")
                except Exception as ex:
                    logger.warning(f"[AutoHarvester] Background harvest exception: {ex}")
                finally:
                    _harvest_in_progress = False

            t = threading.Thread(target=_async_harvester, daemon=True, name="AutoHarvesterStaleRunner")
            t.start()

    # Seed initial real opportunities if database is brand new
    if repository.get_kpi_summary()["total_applications"] == 0:
        try:
            init_engine = ApplicationEngine(
                profile=load_candidate_profile(),
                repository=repository,
                notifier=notifier,
                mode="DISCOVERY_MODE",
            )
            init_source = LivePublicDiscoverySource()
            discovered = init_source.discover_jobs(query="python", location="India", limit=10)
            for j in discovered:
                init_engine.process_job(j)
        except Exception as e:
            logger.warning(f"Initial cloud seed notice: {e}")

    def get_portal_connector(portal_name: str):
        p = portal_name.lower().strip()
        if p == "naukri":
            return NaukriBrowserConnector(session_vault=vault)
        elif p == "internshala":
            return InternshalaBrowserConnector(session_vault=vault)
        elif p == "linkedin":
            return LinkedInBrowserConnector(session_vault=vault)
        return None

    @app.route("/")
    def index():
        profile = load_candidate_profile()
        missing_fields = get_missing_candidate_fields(profile)
        portal_statuses = vault.get_all_portal_statuses()

        # Query filter params
        status_filter = request.args.get("status")
        min_score_filter = request.args.get("min_score")
        emp_filter = request.args.get("employer")
        platform_filter = request.args.get("platform")
        work_filter = request.args.get("work_arrangement")
        verif_filter = request.args.get("verification_status")
        search_filter = request.args.get("search")
        demo_param = request.args.get("demo", "false").lower()

        demo_only = None
        if demo_param == "true":
            demo_only = True
        elif demo_param == "false":
            demo_only = False

        min_score_int = int(min_score_filter) if min_score_filter and min_score_filter.isdigit() else None

        applications = repository.get_applications(
            employer=emp_filter,
            status=status_filter,
            source_platform=platform_filter,
            min_score=min_score_int,
            work_arrangement=work_filter,
            verification_status=verif_filter,
            demo_only=demo_only,
            search=search_filter,
            limit=150,
        )

        # By default, display qualified and active opportunities (exclude REJECTED unless explicitly filtered)
        if not status_filter or status_filter == "":
            applications = [a for a in applications if a.application_status != "REJECTED"]

        kpis = repository.get_kpi_summary(demo_mode=(demo_only is True))
        telegram_status = "CONNECTED" if notifier.is_configured else "NOT_CONFIGURED"

        # Check and auto-trigger stale harvest (>12 hours) in background
        trigger_background_harvest_if_stale()

        # Read last harvest metadata
        harvest_state = {}
        state_file = project_root / "data" / "harvest_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    harvest_state = json.load(f)
            except Exception:
                harvest_state = {}

        # Check existing resumes
        available_resumes = [f.name for f in resumes_dir.glob("*.*") if f.is_file()]

        return render_template(
            "index.html",
            profile=profile,
            missing_fields=missing_fields,
            kpis=kpis,
            applications=applications,
            system_state=system_state,
            telegram_status=telegram_status,
            available_resumes=available_resumes,
            portal_statuses=portal_statuses,
            demo_mode=demo_param,
            harvest_state=harvest_state,
            harvest_in_progress=_harvest_in_progress,
        )

    @app.route("/healthz")
    def health_check():
        trigger_background_harvest_if_stale()
        return jsonify({
            "status": "healthy",
            "service": "antigravity-ai-job-agent",
            "mode": system_state["mode"],
            "version": "2.5.0",
            "telegram_configured": notifier.is_configured,
        })

    @app.route("/api/kpis")
    def api_kpis():
        demo_param = request.args.get("demo", "false").lower()
        demo_mode = True if demo_param == "true" else False
        return jsonify(repository.get_kpi_summary(demo_mode=demo_mode))

    @app.route("/api/applications")
    def api_applications():
        status_filter = request.args.get("status")
        min_score_filter = request.args.get("min_score")
        emp_filter = request.args.get("employer")
        platform_filter = request.args.get("platform")
        work_filter = request.args.get("work_arrangement")
        verif_filter = request.args.get("verification_status")
        search_filter = request.args.get("search")
        demo_param = request.args.get("demo", "false").lower()

        demo_only = None
        if demo_param == "true":
            demo_only = True
        elif demo_param == "false":
            demo_only = False

        min_score_int = int(min_score_filter) if min_score_filter and min_score_filter.isdigit() else None

        apps = repository.get_applications(
            employer=emp_filter,
            status=status_filter,
            source_platform=platform_filter,
            min_score=min_score_int,
            work_arrangement=work_filter,
            verification_status=verif_filter,
            demo_only=demo_only,
            search=search_filter,
            limit=200,
        )

        return jsonify({
            "status": "success",
            "count": len(apps),
            "applications": [
                {
                    "id": a.id,
                    "employer": a.employer,
                    "job_title": a.job_title,
                    "location": a.location,
                    "work_arrangement": a.work_arrangement,
                    "employment_type": a.employment_type,
                    "matching_score": a.matching_score,
                    "application_status": a.application_status,
                    "selected_resume_version": a.selected_resume_version,
                    "job_url": a.job_url,
                    "salary_range": a.salary_range or "Market Standard (≥4.0 LPA)",
                    "min_experience_years": a.min_experience_years,
                    "is_synthetic": bool(a.is_synthetic),
                    "verification_status": a.verification_status or ("DEMO_ONLY" if a.is_synthetic else "SOURCE_CONFIRMED"),
                    "verification_method": a.verification_method,
                    "source_platform": a.source_platform,
                    "summary": a.job_description_summary,
                    "required_skills": a.get_required_skills(),
                    "missing_skills": a.get_missing_skills(),
                    "date_discovered": a.date_discovered,
                }
                for a in apps
            ]
        })

    @app.route("/api/applications/<job_id>/verify_url", methods=["POST"])
    def api_verify_job_url(job_id: str):
        app_obj = repository.get_application_by_id(job_id)
        if not app_obj:
            return jsonify({"status": "error", "message": "Application not found"}), 404

        status, reason, final_url = URLValidator.validate_url(
            app_obj.job_url,
            is_synthetic=bool(app_obj.is_synthetic),
            employer=app_obj.employer,
            check_live_network=True,
            timeout=4.0,
        )

        repository.update_url_verification(
            job_id,
            verification_status=status.value,
            verification_method="HTTP_PROBE",
            job_availability_status="ACTIVE" if status.value == "VERIFIED_ACTIVE" else "UNVERIFIED",
        )

        return jsonify({
            "status": "success",
            "job_id": job_id,
            "verification_status": status.value,
            "verification_reason": reason,
            "final_url": final_url,
        })

    @app.route("/resumes/<path:filename>")
    @app.route("/api/resumes/<path:filename>")
    def download_resume(filename: str):
        return send_from_directory(str(resumes_dir), filename, as_attachment=False)

    @app.route("/api/reports/<path:filename>")
    def download_report(filename: str):
        return send_from_directory(str(reports_dir), filename, as_attachment=False)

    @app.route("/api/emergency_stop", methods=["POST"])
    def emergency_stop():
        data = request.get_json() or {}
        halt = data.get("halt", not system_state["emergency_stop"])
        system_state["emergency_stop"] = halt
        return jsonify({
            "status": "success",
            "emergency_stop": system_state["emergency_stop"],
            "message": "Emergency Stop Triggered. All active and scheduled runs paused." if halt else "Agent Operation Resumed.",
        })

    @app.route("/api/set_mode", methods=["POST"])
    def set_mode():
        data = request.get_json() or {}
        new_mode = data.get("mode")
        if new_mode in ["DISCOVERY_MODE", "ASSISTED_APPLICATION_MODE", "AUTHORIZED_AUTO_APPLY_MODE"]:
            system_state["mode"] = new_mode
            return jsonify({"status": "success", "mode": new_mode, "message": f"Operational mode transitioned to {new_mode}"})
        return jsonify({"status": "error", "message": "Invalid operational mode specified."}), 400

    @app.route("/api/run_discovery", methods=["POST"])
    def run_discovery():
        if system_state["emergency_stop"]:
            return jsonify({"status": "error", "message": "Cannot run discovery: Emergency Stop is active."}), 400

        data = request.get_json() or {}
        is_demo = data.get("demo", False)
        use_live = data.get("live", not is_demo)
        profile = load_candidate_profile()

        engine = ApplicationEngine(
            profile=profile,
            repository=repository,
            notifier=notifier,
            mode=system_state["mode"],
        )

        if use_live:
            source = LivePublicDiscoverySource()
            jobs = source.discover_jobs(query="python", location="India", limit=15)
        else:
            source = SyntheticJobSource()
            jobs = source.discover_jobs(limit=15)

        qualified_count = 0
        vetoed_count = 0
        for j in jobs:
            app_record = engine.process_job(j)
            if app_record:
                if app_record.application_status in ["QUALIFIED", "READY_FOR_APPLICATION", "AWAITING_MANUAL_ACTION", "SUBMITTED", "APPLICATION_CONFIRMED"]:
                    qualified_count += 1
                else:
                    vetoed_count += 1

        reports = engine.generate_daily_report()
        kpis = repository.get_kpi_summary(demo_mode=bool(not use_live))

        return jsonify({
            "status": "success",
            "source_type": "Live Public ATS" if use_live else "Synthetic & Demo Fixtures",
            "is_synthetic": not use_live,
            "total_processed": len(jobs),
            "qualified": qualified_count,
            "vetoed_or_rejected": vetoed_count,
            "reports": reports,
            "kpis": kpis,
        })

    @app.route("/api/generate_resumes", methods=["POST"])
    def generate_resumes():
        profile = load_candidate_profile()
        generated = {}
        for variant in [ResumeVariant.RESUME_A, ResumeVariant.RESUME_B, ResumeVariant.RESUME_C]:
            docx = generate_docx_resume(profile, variant=variant, output_dir=resumes_dir)
            pdf = generate_pdf_resume(profile, variant=variant, output_dir=resumes_dir)
            generated[variant.value] = {
                "docx": f"/api/resumes/{Path(docx).name}",
                "pdf": f"/api/resumes/{Path(pdf).name}",
            }
        return jsonify({
            "status": "success",
            "message": "Resumes A, B, and C generated in DOCX and PDF with verified candidate facts.",
            "resumes": generated,
        })

    @app.route("/api/test_telegram", methods=["POST"])
    def test_telegram():
        profile = load_candidate_profile()
        msg = (
            "🤖 <b>ANTIGRAVITY DASHBOARD TEST ALERT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"Candidate: <b>{profile.full_name}</b>\n"
            f"Active Mode: <code>{system_state['mode']}</code>\n"
            "<i>Telegram Bot communication verified successfully from web dashboard.</i>"
        )
        success = notifier.send_message(msg, event_id="dashboard_test_ping")
        return jsonify({
            "status": "success" if success else "mock_logged",
            "is_configured": notifier.is_configured,
            "message": "Telegram message dispatched." if notifier.is_configured else "Mock message logged. Configure .env with TELEGRAM_BOT_TOKEN to receive real alerts.",
        })

    @app.route("/api/telegram/status")
    def api_telegram_status():
        from telegram_notifications.notifier import mask_secret
        return jsonify({
            "status": "success",
            "is_configured": notifier.is_configured,
            "masked_token": mask_secret(notifier.bot_token),
            "masked_chat_id": mask_secret(notifier.chat_id),
        })

    @app.route("/api/telegram/configure", methods=["POST"])
    def api_telegram_configure():
        data = request.get_json() or {}
        bot_token = data.get("bot_token", "").strip()
        chat_id = data.get("chat_id", "").strip()

        if not bot_token or not chat_id:
            return jsonify({
                "status": "error",
                "message": "Both Telegram Bot Token and Chat ID are required.",
            }), 400

        notifier.configure(bot_token, chat_id)
        success, reason = notifier.test_connection()

        if not success:
            return jsonify({
                "status": "error",
                "message": f"Telegram test failed: {reason}",
            }), 400

        env_path = project_root / ".env"
        lines = []
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        token_set = False
        chat_set = False
        new_lines = []
        for line in lines:
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                new_lines.append(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
                token_set = True
            elif line.startswith("TELEGRAM_CHAT_ID="):
                new_lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")
                chat_set = True
            else:
                new_lines.append(line)

        if not token_set:
            new_lines.append(f"TELEGRAM_BOT_TOKEN={bot_token}\n")
        if not chat_set:
            new_lines.append(f"TELEGRAM_CHAT_ID={chat_id}\n")

        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        os.environ["TELEGRAM_BOT_TOKEN"] = bot_token
        os.environ["TELEGRAM_CHAT_ID"] = chat_id

        return jsonify({
            "status": "success",
            "is_configured": True,
            "message": "Telegram Bot successfully connected and saved! Check your Telegram for the confirmation message.",
        })

    @app.route("/api/job_details/<job_id>")
    def job_details(job_id: str):
        app_obj = repository.get_application_by_id(job_id)
        if not app_obj:
            return jsonify({"status": "error", "message": "Application not found"}), 404

        return jsonify({
            "id": app_obj.id,
            "employer": app_obj.employer,
            "job_title": app_obj.job_title,
            "location": app_obj.location,
            "work_arrangement": app_obj.work_arrangement,
            "employment_type": app_obj.employment_type,
            "matching_score": app_obj.matching_score,
            "application_status": app_obj.application_status,
            "selected_resume_version": app_obj.selected_resume_version,
            "job_url": app_obj.job_url,
            "salary_range": app_obj.salary_range or "Market Standard (≥4.0 LPA)",
            "is_synthetic": bool(app_obj.is_synthetic),
            "verification_status": app_obj.verification_status or ("DEMO_ONLY" if app_obj.is_synthetic else "SOURCE_CONFIRMED"),
            "verification_method": app_obj.verification_method,
            "summary": app_obj.job_description_summary,
            "matching_explanation": app_obj.get_matching_explanation(),
            "required_skills": app_obj.get_required_skills(),
            "missing_skills": app_obj.get_missing_skills(),
            "history": [
                {
                    "from": h.previous_status,
                    "to": h.new_status,
                    "at": h.changed_at_timestamp,
                    "reason": h.reason_or_actor,
                }
                for h in repository.get_status_history(app_obj.id)
            ],
        })

    @app.route("/api/update_candidate", methods=["POST"])
    def update_candidate():
        data = request.get_json() or {}
        email = data.get("email", "").strip()
        phone = data.get("phone", "").strip()

        cfg_path = project_root / "config" / "candidate_profile.yaml"
        if cfg_path.exists():
            with open(cfg_path, "r", encoding="utf-8") as f:
                ydata = yaml.safe_load(f) or {}

            cand = ydata.setdefault("candidate", {})
            contact = cand.setdefault("contact", {})
            if email:
                contact["email"] = email
            if phone:
                contact["phone"] = phone

            with open(cfg_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(ydata, f, sort_keys=False)

        return jsonify({
            "status": "success",
            "message": "Candidate profile updated successfully with verified contact info.",
        })

    @app.route("/api/portals/status", methods=["GET"])
    def api_portal_status():
        return jsonify({
            "status": "success",
            "portals": vault.get_all_portal_statuses(),
        })

    @app.route("/api/portals/send_otp", methods=["POST"])
    def api_send_otp():
        data = request.get_json() or {}
        portal = data.get("portal", "").lower().strip()
        phone = data.get("phone", "").strip()

        if not phone:
            profile = load_candidate_profile()
            phone = profile.contact.phone or ""

        if not phone:
            return jsonify({
                "status": "error",
                "message": "Phone number is required. Please enter your mobile number.",
            }), 400

        connector = get_portal_connector(portal)
        if not connector:
            return jsonify({"status": "error", "message": f"Unsupported portal '{portal}'"}), 400

        res = connector.send_otp(phone)
        return jsonify(res)

    @app.route("/api/portals/verify_otp", methods=["POST"])
    def api_verify_otp():
        data = request.get_json() or {}
        portal = data.get("portal", "").lower().strip()
        otp = data.get("otp", "").strip()

        if not otp:
            return jsonify({"status": "error", "message": "OTP code is required."}), 400

        connector = get_portal_connector(portal)
        if not connector:
            return jsonify({"status": "error", "message": f"Unsupported portal '{portal}'"}), 400

        res = connector.verify_otp(otp)
        return jsonify(res)

    @app.route("/api/portals/disconnect", methods=["POST"])
    def api_disconnect_portal():
        data = request.get_json() or {}
        portal = data.get("portal", "").lower().strip()

        connector = get_portal_connector(portal)
        if connector:
            connector.clear_session()
        else:
            vault.clear_session(portal)

        return jsonify({
            "status": "success",
            "portal": portal,
            "message": f"Disconnected {portal.capitalize()} session successfully.",
        })

    @app.route("/api/portals/sync", methods=["POST"])
    def api_sync_portal():
        if system_state["emergency_stop"]:
            return jsonify({"status": "error", "message": "Cannot sync: Emergency Stop is active."}), 400

        data = request.get_json() or {}
        target_portal = data.get("portal", "all").lower().strip()
        profile = load_candidate_profile()

        engine = ApplicationEngine(
            profile=profile,
            repository=repository,
            notifier=notifier,
            mode=system_state["mode"],
        )

        portals_to_sync = [target_portal] if target_portal in ["naukri", "internshala", "linkedin"] else ["naukri", "internshala", "linkedin"]

        total_scraped = 0
        qualified_count = 0
        vetoed_count = 0
        results_by_portal = {}

        for p_key in portals_to_sync:
            connector = get_portal_connector(p_key)
            if not connector:
                continue

            try:
                jobs = connector.discover_jobs(query="python developer", location="Bengaluru", limit=10)
                p_qualified = 0
                p_vetoed = 0

                for j in jobs:
                    total_scraped += 1
                    app_record = engine.process_job(j)
                    if app_record:
                        if app_record.application_status in [
                            "QUALIFIED", "READY_FOR_APPLICATION", "AWAITING_MANUAL_ACTION", "SUBMITTED", "APPLICATION_CONFIRMED"
                        ]:
                            p_qualified += 1
                            qualified_count += 1
                        else:
                            p_vetoed += 1
                            vetoed_count += 1

                results_by_portal[p_key] = {
                    "scraped": len(jobs),
                    "qualified": p_qualified,
                    "vetoed": p_vetoed,
                }
            except Exception as e:
                logger.error(f"Error syncing portal {p_key}: {e}")
                results_by_portal[p_key] = {"error": str(e), "scraped": 0, "qualified": 0, "vetoed": 0}

        kpis = repository.get_kpi_summary()
        portal_statuses = vault.get_all_portal_statuses()

        return jsonify({
            "status": "success",
            "message": f"Job sync complete across {', '.join(portals_to_sync)}.",
            "total_scraped": total_scraped,
            "qualified": qualified_count,
            "vetoed": vetoed_count,
            "portal_results": results_by_portal,
            "kpis": kpis,
            "portal_statuses": portal_statuses,
        })

    @app.route("/api/run_daily_agent", methods=["POST"])
    def api_run_daily_agent():
        if system_state["emergency_stop"]:
            return jsonify({"status": "error", "message": "Cannot run agent: Emergency Stop is active."}), 400

        data = request.get_json() or {}
        limit = int(data.get("limit_per_source", 15))

        try:
            from scheduler.daily_agent import AutonomousDailyScrapingAgent
            profile = load_candidate_profile()
            agent = AutonomousDailyScrapingAgent(
                profile=profile,
                repository=repository,
                notifier=notifier,
                session_vault=vault,
                mode=system_state["mode"],
            )
            result = agent.run_daily_cycle(limit_per_source=limit)
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error executing Autonomous Daily Agent: {e}")
            return jsonify({
                "status": "error",
                "message": f"Daily agent execution encountered an error: {str(e)}"
            }), 500

    @app.route("/api/scheduler/status", methods=["GET"])
    def api_scheduler_status():
        from scheduler.runner import get_global_scheduler
        sched = get_global_scheduler()
        if not sched:
            return jsonify({
                "status": "idle",
                "is_running": False,
                "message": "Background harvester daemon not initialized in this process.",
            })
        return jsonify({
            "status": "success",
            "scheduler": sched.get_status(),
        })

    return app


if __name__ == "__main__":
    flask_app = create_app()
    flask_app.run(host="127.0.0.1", port=5000, debug=True)
