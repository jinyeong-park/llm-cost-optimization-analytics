# Example: Send alert when costs spike (using webhook.site for demo)

import requests
from datetime import datetime

# 🎯 STUDENT INSTRUCTIONS:
# 1. Go to https://webhook.site
# 2. Copy your unique URL
# 3. Paste it below
# 4. Run this script and watch the alert arrive!

WEBHOOK_URL = "https://webhook.site/b7313890-14e1-4a1b-9b5d-16371f7328eb"


def check_costs_and_alert():
    """
    Monitor LLM costs and send alerts when threshold exceeded.

    In production, replace webhook.site with:
    - Slack: https://hooks.slack.com/services/YOUR/WEBHOOK/URL
    - Discord: https://discord.com/api/webhooks/YOUR/WEBHOOK
    - PagerDuty, Opsgenie, etc.
    """

    # Simulated cost (in production, calculate from Langfuse metrics)
    hourly_cost = 15.50  # $15.50 spent this hour
    threshold = 10.00  # Alert if over $10/hour

    print(f"💰 Current hourly cost: ${hourly_cost:.2f}")
    print(f"⚠️  Threshold: ${threshold:.2f}")

    if hourly_cost > threshold:
        print(f"\n🚨 COST SPIKE DETECTED! Sending alert...\n")

        response = requests.post(
            WEBHOOK_URL,
            json={
                "text": f"🚨 Cost Alert: ${hourly_cost:.2f} spent in last hour",
                "timestamp": datetime.now().isoformat(),
                "alert_type": "cost_spike",
                "details": {
                    "hourly_cost": f"${hourly_cost:.2f}",
                    "threshold": f"${threshold:.2f}",
                    "overage": f"${hourly_cost - threshold:.2f}",
                    "dashboard": "https://cloud.langfuse.com",
                },
            },
        )

        if response.status_code == 200:
            print("✅ Alert sent! Check webhook.site to see it.")
        else:
            print(f"❌ Failed: {response.status_code}")
    else:
        print("✅ Costs within budget. No alert needed.")


if __name__ == "__main__":
    check_costs_and_alert()
