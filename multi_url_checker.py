"""
Ultimate Bot Keeper - Multi-URL Checker
Tries all possible Replit URL formats until one works

Run this on any computer or free cloud service to keep your bot online 24/7
"""

import time
import logging
import random
from datetime import datetime
try:
    import requests
    HAVE_REQUESTS = True
except ImportError:
    HAVE_REQUESTS = False
    import urllib.request
    import socket

# === CONFIGURATION ===
# Project info
REPL_OWNER = "veterancalisthe"
REPL_ID = "9aff7d4d-c131-4692-a733-762029a6d8e4"
PROJECT_NAME = "workspace"  # or "tgtb" or "telegram-twitter-bot"

# Base URLs to try (will try ALL of these)
BASE_URLS = [
    # Dev URL (temporary)
    f"https://{REPL_ID}-00-378m7x1uk4bp1.kirk.replit.dev",
    
    # Permanent URLs (repl.co domain)
    f"https://{PROJECT_NAME}.{REPL_OWNER}.repl.co",
    f"https://{PROJECT_NAME}-{REPL_OWNER}.repl.co",
    
    # App domains
    f"https://{PROJECT_NAME}.replit.app",
    "https://tgtb-telegram-twitter-bot.replit.app",
    
    # Try alternate project names
    "https://tgtb.veterancalisthe.repl.co",
    "https://telegram-twitter-bot.veterancalisthe.repl.co",
    
    # Last resort: Try direct IP (won't work externally but included for completeness)
    "http://0.0.0.0:5000"
]

# Endpoints to try with each base URL
ENDPOINTS = ["/health", "/ping", "/ping.txt", "/"]

# Ping interval (minutes)
MIN_INTERVAL = 4
MAX_INTERVAL = 6

# === SETUP LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
log = logging.getLogger("BotKeeper")

def ping_with_requests(url):
    """Ping URL using requests library"""
    try:
        log.info(f"Pinging {url}...")
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            log.info(f"✅ Success! URL: {url}, Status: {response.status_code}")
            return True
        else:
            log.warning(f"❌ Bad status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        log.error(f"❌ Error: {str(e)}")
    return False

def ping_with_urllib(url):
    """Ping URL using urllib (no dependencies)"""
    try:
        log.info(f"Pinging {url}...")
        response = urllib.request.urlopen(url, timeout=30)
        code = response.getcode()
        if code == 200:
            log.info(f"✅ Success! URL: {url}, Status: {code}")
            return True
        else:
            log.warning(f"❌ Bad status: {code}")
    except (urllib.error.URLError, socket.timeout) as e:
        log.error(f"❌ Error: {str(e)}")
    return False

def try_all_urls():
    """Try all combinations of base URLs and endpoints"""
    for base_url in BASE_URLS:
        for endpoint in ENDPOINTS:
            url = f"{base_url}{endpoint}"
            
            # Use appropriate ping function based on available libraries
            if HAVE_REQUESTS:
                if ping_with_requests(url):
                    return url, True
            else:
                if ping_with_urllib(url):
                    return url, True
    
    return None, False

def main():
    """Main loop"""
    log.info("=" * 60)
    log.info("🤖 Ultimate Bot Keeper - Multi-URL Checker 🤖")
    log.info(f"Trying {len(BASE_URLS)} base URLs with {len(ENDPOINTS)} endpoints")
    log.info(f"Total URL combinations to try: {len(BASE_URLS) * len(ENDPOINTS)}")
    log.info("=" * 60)
    
    success_count = 0
    failure_count = 0
    successful_urls = set()
    
    try:
        while True:
            # Try all URLs
            working_url, success = try_all_urls()
            
            if success:
                success_count += 1
                successful_urls.add(working_url)
                log.info(f"✅ Found a working URL: {working_url}")
            else:
                failure_count += 1
                log.error("❌ No working URLs found this time!")
            
            # Calculate uptime percentage
            total = success_count + failure_count
            if total > 0:
                uptime = (success_count / total) * 100
                log.info(f"📊 Stats: {success_count} successes, {failure_count} failures ({uptime:.1f}% uptime)")
                
                if successful_urls:
                    log.info(f"🔗 Working URLs found so far: {', '.join(successful_urls)}")
            
            # Random interval to avoid patterns
            interval = random.randint(MIN_INTERVAL * 60, MAX_INTERVAL * 60)
            next_time = datetime.now().timestamp() + interval
            next_time_str = datetime.fromtimestamp(next_time).strftime('%H:%M:%S')
            
            log.info(f"⏰ Next ping in {interval//60} minutes (at {next_time_str})")
            time.sleep(interval)
            
    except KeyboardInterrupt:
        log.info("Bot keeper stopped by user")
    except Exception as e:
        log.error(f"Unexpected error: {str(e)}")
        time.sleep(60)
        main()  # Restart on error

if __name__ == "__main__":
    main()