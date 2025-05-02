"""
Self-pinging script for Telegram-X bot integration.
This script runs in a separate thread and periodically pings the web app
to keep it alive, removing the need for external uptime services.
"""

import os
import time
import logging
import threading
import requests
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('SelfPinger')

# Configuration
PING_INTERVAL = 270  # Ping every 4.5 minutes (270 seconds)
MAX_RETRIES = 3
RETRY_DELAY = 5  # Seconds between retries

def get_ping_url():
    """Get the URL to ping based on Replit environment variables."""
    # First try internal URLs (these work from within the Replit environment)
    main_url = "http://0.0.0.0:5000/health"
    keep_alive_url = "http://0.0.0.0:8080/ping"
    
    # Also try Replit domains if available
    replit_domain = os.environ.get('REPLIT_DOMAINS', '')
    if replit_domain:
        # The Replit domain URL format
        logger.info(f"Found Replit domain: {replit_domain}")
        replit_url = f"https://{replit_domain}/health"
        
        # Update main URL to use the Replit domain
        main_url = replit_url
    
    logger.info(f"Using ping URLs: {main_url} and {keep_alive_url}")
    return main_url, keep_alive_url

def ping_bot():
    """Ping the bot with retries on failure"""
    main_url, keep_alive_url = get_ping_url()
    success = False
    
    # Try main URL first
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Self-pinging main web app at {main_url}...")
            response = requests.get(main_url, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Self-ping successful! Main app is online.")
                success = True
                break
            else:
                logger.warning(f"❌ Main app responded with non-200 status: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"❌ Failed to ping main app on attempt {attempt+1}: {str(e)}")
        
        if attempt < MAX_RETRIES - 1:
            logger.info(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)
    
    # If main URL failed, try keep-alive server
    if not success:
        try:
            logger.info(f"Self-pinging keep-alive server at {keep_alive_url}...")
            response = requests.get(keep_alive_url, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"✅ Self-ping successful! Keep-alive server is online.")
                success = True
            else:
                logger.warning(f"❌ Keep-alive server responded with non-200 status: {response.status_code}")
        except requests.RequestException as e:
            logger.error(f"❌ Failed to ping keep-alive server: {str(e)}")
    
    return success

def self_ping_loop():
    """Main loop to periodically ping the bot"""
    logger.info("=" * 50)
    logger.info("Starting self-pinging thread")
    logger.info(f"Ping interval: {PING_INTERVAL} seconds")
    logger.info("=" * 50)
    
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
            logger.info(f"Next self-ping in {sleep_time:.1f} seconds (at {next_ping_str})")
            
            time.sleep(sleep_time)
    except Exception as e:
        logger.error(f"Self-pinging thread error: {str(e)}")
        # Restart the thread if it fails
        time.sleep(30)
        threading.Thread(target=self_ping_loop, daemon=True).start()

def start_self_pinger():
    """Start the self-pinging thread as a daemon"""
    # Run in a daemon thread so it will exit when the main program exits
    self_ping_thread = threading.Thread(target=self_ping_loop, daemon=True)
    self_ping_thread.start()
    logger.info("Self-pinger thread started")
    return self_ping_thread

if __name__ == "__main__":
    # For testing the script directly
    thread = start_self_pinger()
    try:
        # Keep the main thread running
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Self-pinger stopped by user")