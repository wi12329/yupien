"""
Simple External Pinger - A reliable way to keep your Replit bot running 24/7
Just run this script on any computer or server that's online continuously.

Instructions:
1. Save this file to your computer as 'external_pinger.py'
2. Install requests if you don't have it: pip install requests
3. Run the script: python external_pinger.py
4. Leave it running on any computer, Raspberry Pi, or server that stays on

By: YupienBot Team
"""

import time
import random
import logging
import requests
from datetime import datetime

# === CONFIGURATION - CHANGE THIS URL ===
REPLIT_URL = "https://9aff7d4d-c131-4692-a733-762029a6d8e4-00-378m7x1uk4bp1.kirk.replit.dev"

# How often to ping (in seconds)
# Random variation to avoid patterns (4-6 minutes)
MIN_PING_INTERVAL = 240  # 4 minutes
MAX_PING_INTERVAL = 360  # 6 minutes

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()  # Log to console only
    ]
)
log = logging.getLogger("TelegramXPinger")

def send_ping():
    """Send a ping request to the Replit URL"""
    endpoints = ["/health", "/ping", "/ping.txt"]
    
    # Try all endpoints until one succeeds
    for endpoint in endpoints:
        url = f"{REPLIT_URL}{endpoint}"
        try:
            log.info(f"Pinging {url}...")
            response = requests.get(url, timeout=20)
            
            if response.status_code == 200:
                log.info(f"✅ Ping successful! Status: {response.status_code}")
                return True
            else:
                log.warning(f"❌ Bad status: {response.status_code}")
        except Exception as e:
            log.error(f"❌ Error: {str(e)}")
    
    return False

def main():
    """Main pinger loop"""
    log.info("=" * 60)
    log.info("🤖 YupienBot External Pinger Started 🤖")
    log.info(f"URL: {REPLIT_URL}")
    log.info("=" * 60)
    log.info("Keep this script running to maintain your bot online 24/7")
    log.info("Press Ctrl+C to stop")
    log.info("-" * 60)
    
    success_count = 0
    failure_count = 0
    
    try:
        while True:
            # Send ping
            if send_ping():
                success_count += 1
            else:
                failure_count += 1
            
            # Calculate uptime percentage
            total = success_count + failure_count
            if total > 0:
                uptime = (success_count / total) * 100
                log.info(f"📊 Stats: {success_count} successes, {failure_count} failures ({uptime:.1f}% uptime)")
            
            # Random interval to avoid patterns
            interval = random.randint(MIN_PING_INTERVAL, MAX_PING_INTERVAL)
            next_time = datetime.now().timestamp() + interval
            next_time_str = datetime.fromtimestamp(next_time).strftime('%H:%M:%S')
            
            log.info(f"⏰ Next ping in {interval} seconds (at {next_time_str})")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        log.info("Pinger stopped by user")
    except Exception as e:
        log.error(f"Unexpected error: {str(e)}")
        time.sleep(60)
        log.info("Restarting pinger...")
        main()

if __name__ == "__main__":
    main()