"""
Replit Watcher - Continuously monitor and keep your Replit alive

This script runs continuously and:
1. Finds your Replit's current URL (even as it changes)
2. Keeps pinging it to prevent sleep
3. Maintains a log of URL changes

Instructions:
1. Upload to PythonAnywhere (or any server)
2. Run with: python replit_watcher.py
3. Leave it running!
"""

import time
import random
import json
import logging
import os
from datetime import datetime
import requests

# === CONFIGURATION ===
# Your Replit info
REPL_OWNER = "veterancalisthe"
REPL_ID = "9aff7d4d-c131-4692-a733-762029a6d8e4"
PROJECT_NAME = "workspace"

# Ping settings
PING_INTERVAL = 270  # seconds (4.5 minutes)
URL_LOG_FILE = "replit_urls.json"
ENDPOINTS = ["/health", "/ping", "/ping.txt", "/"]

# === SETUP LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("replit_watcher.log")
    ]
)
log = logging.getLogger("ReplitWatcher")

# === URL TRACKING FUNCTIONS ===
def load_url_history():
    """Load previously found URLs from file"""
    if os.path.exists(URL_LOG_FILE):
        try:
            with open(URL_LOG_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            log.error(f"Could not parse {URL_LOG_FILE}, creating new history")
    
    # Create new history structure
    return {
        "project_info": {
            "owner": REPL_OWNER,
            "id": REPL_ID,
            "name": PROJECT_NAME
        },
        "current_url": None,
        "url_history": [],
        "ping_success_count": 0,
        "ping_failure_count": 0,
        "last_success": None
    }

def save_url_history(history):
    """Save URL history to file"""
    with open(URL_LOG_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def add_url_to_history(history, url, working=True):
    """Add new URL to history with timestamp"""
    timestamp = datetime.now().isoformat()
    
    # Add to history only if it's a new URL
    if not history["url_history"] or history["url_history"][-1]["url"] != url:
        history["url_history"].append({
            "url": url,
            "found_at": timestamp,
            "working": working
        })
    
    # Update current URL if working
    if working:
        history["current_url"] = url
        history["last_success"] = timestamp
    
    # Save back to file
    save_url_history(history)
    return history

# === REPLIT URL FINDER FUNCTIONS ===
def generate_possible_dev_urls():
    """Generate possible Replit development URLs to try"""
    # The known working URL format
    main_url = f"{REPL_ID}-00-378m7x1uk4bp1.kirk.replit.dev"
    
    # Alternate formats to try if the main one stops working
    alternates = [
        f"{REPL_ID}.replit.dev",
        f"{PROJECT_NAME}.{REPL_OWNER}.repl.co",
        f"{PROJECT_NAME}.replit.app",
        "tgtb-telegram-twitter-bot.replit.app"
    ]
    
    return [main_url] + alternates

def ping_url(url):
    """Ping a URL and return True if it works"""
    try:
        log.info(f"Pinging {url}...")
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            log.info(f"✅ Success! Status: {response.status_code}")
            return True
        else:
            log.warning(f"❌ Bad status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        log.error(f"❌ Error: {str(e)}")
    return False

def find_working_url(history):
    """Find a working Replit URL"""
    # Try current URL first
    if history["current_url"]:
        for endpoint in ENDPOINTS:
            url = f"https://{history['current_url']}{endpoint}"
            if ping_url(url):
                log.info(f"✅ Current URL still working!")
                return history["current_url"], True
        log.warning("Current URL no longer working, trying alternatives...")
    
    # Try all possible URL formats
    for base_url in generate_possible_dev_urls():
        for endpoint in ENDPOINTS:
            url = f"https://{base_url}{endpoint}"
            if ping_url(url):
                log.info(f"✅ Found working URL: {base_url}")
                return base_url, True
    
    return None, False

# === MAIN FUNCTIONS ===
def run_ping_cycle():
    """Run one ping cycle"""
    # Load URL history
    history = load_url_history()
    
    # Find working URL
    url, success = find_working_url(history)
    
    # Update history
    if success and url:
        add_url_to_history(history, url, True)
        history["ping_success_count"] += 1
    else:
        log.error("❌ Could not find any working URL!")
        history["ping_failure_count"] += 1
    
    # Save updated ping counts
    save_url_history(history)
    
    # Return whether we were successful
    return success

def main():
    """Main loop to continuously ping the Replit"""
    log.info("=" * 60)
    log.info("👀 Replit Watcher - Keeping Your Bot Alive")
    log.info(f"Target: @{REPL_OWNER}/{PROJECT_NAME} ({REPL_ID})")
    log.info(f"Ping interval: {PING_INTERVAL} seconds")
    log.info("=" * 60)
    
    success_streak = 0
    failure_streak = 0
    
    try:
        while True:
            start_time = time.time()
            
            # Run a ping cycle
            if run_ping_cycle():
                success_streak += 1
                failure_streak = 0
            else:
                failure_streak += 1
                success_streak = 0
            
            # Load latest history for stats
            history = load_url_history()
            total_pings = history["ping_success_count"] + history["ping_failure_count"]
            success_rate = (history["ping_success_count"] / total_pings * 100) if total_pings > 0 else 0
            
            # Show detailed stats
            log.info("-" * 60)
            log.info(f"📊 Stats: {history['ping_success_count']} successes, {history['ping_failure_count']} failures ({success_rate:.1f}% success rate)")
            log.info(f"🔷 Current streak: {'✓' * success_streak if success_streak > 0 else '✗' * failure_streak}")
            log.info(f"🌐 Current URL: {history['current_url']}")
            
            if history["last_success"]:
                last_success_time = datetime.fromisoformat(history["last_success"])
                elapsed = (datetime.now() - last_success_time).total_seconds()
                log.info(f"⏱️ Last successful ping: {int(elapsed//60)} minutes ago")
            
            # Calculate sleep time
            elapsed = time.time() - start_time
            sleep_time = max(1, PING_INTERVAL - elapsed)
            
            next_ping = datetime.now().timestamp() + sleep_time
            next_ping_str = datetime.fromtimestamp(next_ping).strftime('%H:%M:%S')
            log.info(f"⏱️ Next ping in {sleep_time:.1f} seconds (at {next_ping_str})")
            log.info("-" * 60)
            
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        log.info("Watcher stopped by user")
    except Exception as e:
        log.error(f"Unexpected error: {str(e)}")
        # Wait and restart
        time.sleep(60)
        main()

if __name__ == "__main__":
    main()