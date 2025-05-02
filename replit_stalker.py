"""
Replit Stalker - Find and Track Your Replit's Current Dev URL

This script can be run on PythonAnywhere or any external service to:
1. Find your Replit's current development URL
2. Track URL changes over time
3. Keep your Replit awake by pinging it periodically

Usage:
1. Set your Replit username, project ID, and project name below
2. Upload to PythonAnywhere and schedule it to run frequently
3. It will automatically find and ping your Replit no matter how the URL changes
"""

import time
import random
import json
import logging
import os
from datetime import datetime
try:
    import requests
    HAVE_REQUESTS = True
except ImportError:
    HAVE_REQUESTS = False
    import urllib.request
    import socket

# === CONFIGURATION (CHANGE THESE) ===
# Your Replit username, project ID, and name
REPL_OWNER = "veterancalisthe"  # Your Replit username
REPL_ID = "9aff7d4d-c131-4692-a733-762029a6d8e4"  # Your project's ID
PROJECT_NAME = "workspace"  # Your project name

# Stalker settings
URL_LOG_FILE = "replit_urls.json"  # File to store found URLs
REPLIT_API_URL = f"https://replit.com/data/repls/@{REPL_OWNER}/{PROJECT_NAME}"
PING_INTERVAL = 5 * 60  # 5 minutes between pings

# Endpoints to try
ENDPOINTS = ["/health", "/ping", "/ping.txt", "/"]

# === SETUP LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
log = logging.getLogger("ReplitStalker")

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
        "ping_failure_count": 0
    }

def save_url_history(history):
    """Save URL history to file"""
    with open(URL_LOG_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def add_url_to_history(history, url, working=True):
    """Add new URL to history with timestamp"""
    timestamp = datetime.now().isoformat()
    
    # Add to history
    history["url_history"].append({
        "url": url,
        "found_at": timestamp,
        "working": working
    })
    
    # Update current URL if working
    if working:
        history["current_url"] = url
    
    # Save back to file
    save_url_history(history)
    return history

# === REPLIT URL FINDER FUNCTIONS ===
def get_replit_current_dev_url():
    """Try to get the current development URL from Replit's API"""
    if HAVE_REQUESTS:
        try:
            response = requests.get(REPLIT_API_URL, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "hostedUrl" in data:
                    return data["hostedUrl"]
        except Exception as e:
            log.error(f"Error accessing Replit API: {e}")
    return None

def generate_possible_dev_urls():
    """Generate possible Replit development URLs to try"""
    # Currently works with kirk.replit.dev format
    # The format may change over time, so we try variations
    base_patterns = [
        f"{REPL_ID}-00-378m7x1uk4bp1.kirk.replit.dev",  # Current known format
        f"{REPL_ID}-00-*.kirk.replit.dev",  # Wildcard middle section
        f"{REPL_ID}.replit.dev",  # Simple format
        f"{REPL_ID}-*.replit.dev",  # Any suffix
    ]
    
    # Resolve wildcards with different possibilities
    resolved_urls = []
    for pattern in base_patterns:
        if "*" in pattern:
            # Just use the non-wildcard part as we can't guess the random part
            resolved_urls.append(pattern.split("*")[0].rstrip("-") + ".replit.dev")
        else:
            resolved_urls.append(pattern)
    
    return resolved_urls

def try_all_possible_urls(history):
    """Try all possible URL formats until one works"""
    # Try current URL from history first, if it exists
    if history["current_url"]:
        for endpoint in ENDPOINTS:
            url = f"https://{history['current_url']}{endpoint}"
            if ping_url(url):
                log.info(f"✅ Current URL still working: {url}")
                return url, True
        log.warning("❌ Current URL no longer working, trying alternatives...")
    
    # Try generating new dev URLs
    dev_urls = generate_possible_dev_urls()
    for base_url in dev_urls:
        for endpoint in ENDPOINTS:
            url = f"https://{base_url}{endpoint}"
            if ping_url(url):
                # Extract just the base URL part without endpoint
                base_url = url.split("://")[1].split("/")[0]
                log.info(f"✅ Found working dev URL: {base_url}")
                return base_url, True
    
    # Try traditional URLs as fallback
    traditional_urls = [
        f"{PROJECT_NAME}.{REPL_OWNER}.repl.co",
        f"{PROJECT_NAME}.replit.app",
        f"tgtb-telegram-twitter-bot.replit.app"
    ]
    
    for base_url in traditional_urls:
        for endpoint in ENDPOINTS:
            url = f"https://{base_url}{endpoint}"
            if ping_url(url):
                # Extract just the base URL part without endpoint
                base_url = url.split("://")[1].split("/")[0]
                log.info(f"✅ Found working traditional URL: {base_url}")
                return base_url, True
    
    return None, False

# === PING FUNCTIONS ===
def ping_url(url):
    """Ping a URL and return True if it works"""
    if HAVE_REQUESTS:
        return ping_with_requests(url)
    else:
        return ping_with_urllib(url)

def ping_with_requests(url):
    """Ping URL using requests library"""
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

def ping_with_urllib(url):
    """Ping URL using urllib (no dependencies)"""
    try:
        log.info(f"Pinging {url}...")
        response = urllib.request.urlopen(url, timeout=30)
        code = response.getcode()
        if code == 200:
            log.info(f"✅ Success! Status: {code}")
            return True
        else:
            log.warning(f"❌ Bad status: {code}")
    except (urllib.error.URLError, socket.timeout) as e:
        log.error(f"❌ Error: {str(e)}")
    return False

# === MAIN FUNCTION ===
def main():
    """Main function"""
    log.info("=" * 60)
    log.info("🕵️ Replit Stalker - Find & Track Your Replit's URL")
    log.info(f"Looking for: @{REPL_OWNER}/{PROJECT_NAME} ({REPL_ID})")
    log.info("=" * 60)
    
    # Load URL history
    history = load_url_history()
    
    # Try to get current URL
    url, success = try_all_possible_urls(history)
    
    # Update history
    if success and url:
        log.info(f"✅ Successfully found working URL: {url}")
        add_url_to_history(history, url, True)
        history["ping_success_count"] += 1
    else:
        log.error("❌ Could not find a working URL!")
        history["ping_failure_count"] += 1
    
    # Always save updated ping counts
    save_url_history(history)
    
    # Show statistics
    total_pings = history["ping_success_count"] + history["ping_failure_count"]
    success_rate = (history["ping_success_count"] / total_pings * 100) if total_pings > 0 else 0
    log.info("-" * 60)
    log.info(f"📊 Stats: {history['ping_success_count']} successes, {history['ping_failure_count']} failures ({success_rate:.1f}% success rate)")
    log.info(f"🔷 Current URL: {history['current_url']}")
    log.info(f"🗂️ URL history: {len(history['url_history'])} entries")
    log.info("-" * 60)
    
    return success

if __name__ == "__main__":
    success = main()
    
    # If running as a command, exit with appropriate code
    import sys
    sys.exit(0 if success else 1)