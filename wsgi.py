"""Production WSGI entry point for Render Cloud Deployment."""

import logging
import os
from dashboard.app import create_app
from scheduler.keep_alive import start_keep_alive_pinger
from scheduler.runner import BackgroundJobScheduler
from candidate_profile.loader import load_candidate_profile
from database.repository import get_default_repository
from telegram_notifications.notifier import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("wsgi")

# Operational mode from environment
active_mode = os.environ.get("AGENT_MODE", "DISCOVERY_MODE")

# Ensure verified Telegram credentials for candidate Kiran A N are present
if not os.environ.get("TELEGRAM_BOT_TOKEN"):
    os.environ["TELEGRAM_BOT_TOKEN"] = "8647018389:AAEe6j1NgipZdY67RXxz9rJdSjvaiU3t7jQ"
if not os.environ.get("TELEGRAM_CHAT_ID"):
    os.environ["TELEGRAM_CHAT_ID"] = "7273693371"

# Initialize Flask application
app = create_app(
    current_mode=active_mode,
    email_monitoring=os.environ.get("EMAIL_MONITORING", "false").lower() == "true",
)

# Start anti-sleep keep-alive pinger if running on Render or if KEEP_ALIVE_URL is set
start_keep_alive_pinger()

# Autonomous Background Harvesting Routine
def run_autonomous_cloud_harvest():
    try:
        from scheduler.daily_agent import AutonomousDailyScrapingAgent
        profile = load_candidate_profile()
        repo = get_default_repository()
        notifier = TelegramNotifier()
        agent = AutonomousDailyScrapingAgent(
            profile=profile,
            repository=repo,
            notifier=notifier,
            mode=active_mode,
        )
        logger.info("[WSGI Scheduler] Starting autonomous cloud harvesting cycle across Naukri, Internshala, and ATS boards...")
        res = agent.run_daily_cycle(limit_per_source=15)
        logger.info(
            f"[WSGI Scheduler] Harvesting complete: {res.get('total_scraped', 0)} scraped, "
            f"{res.get('total_qualified', 0)} qualified, {res.get('total_vetoed', 0)} vetoed."
        )
    except Exception as e:
        logger.error(f"[WSGI Scheduler] Autonomous harvest error: {e}")

# Read harvest interval from env (default 720 minutes = 12 hours)
harvest_interval = int(os.environ.get("HARVEST_INTERVAL_MINUTES", 720))

# Start background harvester daemon with a 20-second startup delay
cloud_scheduler = BackgroundJobScheduler(
    run_discovery_fn=run_autonomous_cloud_harvest,
    interval_minutes=harvest_interval,
    initial_delay_seconds=20,
)
cloud_scheduler.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

