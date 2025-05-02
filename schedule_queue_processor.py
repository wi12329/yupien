"""
Schedule Queue Processor

This script schedules the queue processor to run at regular intervals.
It ensures tweets are processed and posted even if the user closes their Replit.

Usage:
    python schedule_queue_processor.py
"""

import time
import logging
import threading
import os
import sys
import signal
from datetime import datetime, timedelta
import requests
import subprocess
from queue_processor import process_queue

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("queue_scheduler.log")
    ]
)
log = logging.getLogger("QueueScheduler")

# Configuration
PROCESSOR_INTERVAL = 5 * 60  # Run the processor every 5 minutes
SELF_PING_INTERVAL = 4 * 60  # Self-ping every 4 minutes to stay alive
REPLIT_PROJECT_URL = None    # Will be populated automatically
HEALTH_ENDPOINTS = ["/health", "/ping", "/ping.txt", "/"]

# Control flags
stop_flag = False
last_processor_run = None
last_ping_time = None

def get_replit_url():
    """Get the Replit URL for self-pinging."""
    try:
        # Try to get URL from environment
        repl_slug = os.environ.get("REPL_SLUG", "workspace")
        repl_owner = os.environ.get("REPL_OWNER", "veterancalisthe")
        
        # Use the known development URL first
        dev_url = "9aff7d4d-c131-4692-a733-762029a6d8e4-00-378m7x1uk4bp1.kirk.replit.dev"
        
        # Then try standard URLs
        urls = [
            dev_url,  # Development URL
            f"{repl_slug}.{repl_owner}.repl.co",  # Standard Replit URL
            f"{repl_slug}.replit.app",  # New Replit URL format
            "tgtb-telegram-twitter-bot.replit.app"  # Custom domain
        ]
        
        for url in urls:
            for endpoint in HEALTH_ENDPOINTS:
                full_url = f"https://{url}{endpoint}"
                try:
                    log.info(f"Trying URL: {full_url}")
                    response = requests.get(full_url, timeout=5)
                    if response.status_code == 200:
                        log.info(f"Found working URL: {full_url}")
                        return full_url
                except:
                    pass
        
        return None
    except Exception as e:
        log.error(f"Error getting Replit URL: {e}")
        return None

def self_ping():
    """Ping our own Replit to keep it alive."""
    global last_ping_time, REPLIT_PROJECT_URL
    
    # Get URL if not already set
    if not REPLIT_PROJECT_URL:
        REPLIT_PROJECT_URL = get_replit_url()
    
    if REPLIT_PROJECT_URL:
        try:
            log.info(f"Self-pinging at {REPLIT_PROJECT_URL}")
            response = requests.get(REPLIT_PROJECT_URL, timeout=10)
            log.info(f"Self-ping result: {response.status_code}")
            last_ping_time = datetime.now()
            return True
        except Exception as e:
            log.error(f"Self-ping failed: {e}")
            # Reset URL so we'll try to find it again next time
            REPLIT_PROJECT_URL = None
    else:
        log.warning("No valid Replit URL found for self-pinging")
    
    return False

def run_processor():
    """Run the tweet queue processor."""
    global last_processor_run
    
    log.info("Running queue processor")
    try:
        process_queue()
        last_processor_run = datetime.now()
        log.info("Queue processor completed successfully")
        return True
    except Exception as e:
        log.error(f"Error running queue processor: {e}")
        return False

def self_ping_thread():
    """Thread function for self-pinging."""
    global stop_flag, last_ping_time
    
    log.info("Starting self-ping thread")
    while not stop_flag:
        # Check if we need to ping
        current_time = datetime.now()
        if not last_ping_time or (current_time - last_ping_time).total_seconds() >= SELF_PING_INTERVAL:
            self_ping()
        
        # Sleep for a while
        time.sleep(30)  # Check every 30 seconds

def processor_thread():
    """Thread function for running the queue processor."""
    global stop_flag, last_processor_run
    
    log.info("Starting processor thread")
    while not stop_flag:
        # Check if we need to run the processor
        current_time = datetime.now()
        if not last_processor_run or (current_time - last_processor_run).total_seconds() >= PROCESSOR_INTERVAL:
            run_processor()
        
        # Sleep for a while
        time.sleep(30)  # Check every 30 seconds

def signal_handler(sig, frame):
    """Handle termination signals."""
    global stop_flag
    log.info("Received signal to stop")
    stop_flag = True
    sys.exit(0)

def main():
    """Main function."""
    global last_processor_run, last_ping_time
    
    log.info("=" * 60)
    log.info("🔄 Queue Processor Scheduler")
    log.info(f"Processor interval: {PROCESSOR_INTERVAL} seconds")
    log.info(f"Self-ping interval: {SELF_PING_INTERVAL} seconds")
    log.info("=" * 60)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the processor once at startup
    last_processor_run = datetime.now() - timedelta(seconds=PROCESSOR_INTERVAL)  # Force immediate run
    run_processor()
    
    # Start self-pinging
    last_ping_time = datetime.now() - timedelta(seconds=SELF_PING_INTERVAL)  # Force immediate ping
    self_ping()
    
    # Start threads
    ping_thread = threading.Thread(target=self_ping_thread, daemon=True)
    proc_thread = threading.Thread(target=processor_thread, daemon=True)
    
    ping_thread.start()
    proc_thread.start()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(60)
            log.info(f"Still running. Last processor run: {last_processor_run}, Last ping: {last_ping_time}")
    except KeyboardInterrupt:
        log.info("Keyboard interrupt received")
        stop_flag = True
    
    log.info("Scheduler stopped")

if __name__ == "__main__":
    main()