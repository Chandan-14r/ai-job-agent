"""Production WSGI entry point for Render Cloud Deployment."""

import logging
import os
from dashboard.app import create_app
from scheduler.keep_alive import start_keep_alive_pinger

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

# Initialize Flask application
app = create_app(
    current_mode=os.environ.get("AGENT_MODE", "DISCOVERY_MODE"),
    email_monitoring=os.environ.get("EMAIL_MONITORING", "false").lower() == "true",
)

# Start anti-sleep keep-alive pinger if running on Render or if KEEP_ALIVE_URL is set
start_keep_alive_pinger()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
