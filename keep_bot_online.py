"""
Custom pinger script to keep a Replit bot online 24/7.
This script can be run on any computer or server to periodically 
ping your Replit bot to prevent it from sleeping.

Usage:
    python keep_bot_online.py
"""

import time
import logging
import requests
import socket
from datetime import datetime

# ==== Configuration ====
# Your Replit URL - CHANGE THIS to your actual Replit URL
REPLIT_URL = "https://9aff7d4d-c131-4692-a733-762029a6d8e4-00-378m7x1uk4bp1.kirk.replit.dev"

# The endpoints to ping
PING_ENDPOINTS = [
    "/health",       # Health check endpoint
    "/ping",         # Simple ping endpoint
    "/ping.txt",     # Plain text ping endpoint
]

# How often to ping (in seconds)
PING_INTERVAL = 240  # Every 4 minutes

# Retry settings
MAX_RETRIES = 3
RETRY_DELAY = 5  # Seconds between retries

# ==== Logging Setup ====
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot_pinger.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def ping_bot():
    """Ping the bot with retries on failure"""
    success = False
    
    for endpoint in PING_ENDPOINTS:
        url = f"{REPLIT_URL}{endpoint}"
        
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Pinging {url}...")
                start_time = time.time()
                response = requests.get(url, timeout=30)  # Longer timeout for Replit
                elapsed = time.time() - start_time
                
                if response.status_code == 200:
                    logger.info(f"✅ Ping to {url} successful! Response time: {elapsed:.2f}s")
                    success = True
                    break
                else:
                    logger.warning(f"❌ {url} responded with non-200 status: {response.status_code}")
            except requests.RequestException as e:
                logger.error(f"❌ Failed to ping {url} (attempt {attempt+1}/{MAX_RETRIES}): {str(e)}")
            
            if attempt < MAX_RETRIES - 1:
                logger.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
        
        if success:
            # If any endpoint succeeds, we can return success
            return True
    
    # If all endpoints failed, return failure
    return False

def main():
    """Main loop to periodically ping the bot"""
    logger.info("=" * 60)
    logger.info("Starting Replit Bot Pinger")
    logger.info(f"Target URL: {REPLIT_URL}")
    logger.info(f"Ping interval: {PING_INTERVAL} seconds")
    logger.info(f"Endpoints to try: {', '.join(PING_ENDPOINTS)}")
    logger.info("=" * 60)
    
    successes = 0
    failures = 0
    
    try:
        while True:
            start_time = time.time()
            
            # Ping the bot
            if ping_bot():
                successes += 1
            else:
                failures += 1
            
            # Log statistics every 10 pings
            if (successes + failures) % 10 == 0:
                total = successes + failures
                success_rate = (successes / total) * 100 if total > 0 else 0
                logger.info(f"Stats: {successes} successes, {failures} failures ({success_rate:.1f}% success rate)")
            
            # Calculate time to sleep
            elapsed = time.time() - start_time
            sleep_time = max(1, PING_INTERVAL - elapsed)
            
            next_ping = datetime.now().timestamp() + sleep_time
            next_ping_str = datetime.fromtimestamp(next_ping).strftime('%H:%M:%S')
            logger.info(f"Next ping in {sleep_time:.1f} seconds (at {next_ping_str})")
            
            time.sleep(sleep_time)
    except KeyboardInterrupt:
        logger.info("Bot pinger stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        # Sleep and restart
        time.sleep(60)
        main()

if __name__ == "__main__":
    # Check if we can resolve the hostname
    try:
        ip = socket.gethostbyname(REPLIT_URL.replace("https://", "").replace("http://", "").split("/")[0])
        logger.info(f"Resolved {REPLIT_URL} to IP: {ip}")
    except socket.gaierror:
        logger.error(f"⚠️ Could not resolve the hostname in {REPLIT_URL}")
        logger.error("Please make sure the URL is correct!")
    
    # Run the main loop
    main()