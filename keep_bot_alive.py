#!/usr/bin/env python
"""
Standalone script to keep the Telegram-X bot alive.
This script can be run separately to prevent Replit from sleeping.
"""

import os
import sys
import logging
import time
from keep_alive import run_keep_alive
import threading

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("keep_alive.log")
    ]
)
logger = logging.getLogger(__name__)

def ping_main_app():
    """Periodically ping the main app to keep it alive."""
    import urllib.request
    import urllib.error
    
    # Use environment variable for the port if specified, otherwise use default
    port = os.environ.get('PORT', 5000)
    
    while True:
        try:
            logger.info("Pinging main application...")
            with urllib.request.urlopen(f"http://localhost:{port}/api/status") as response:
                if response.status == 200:
                    logger.info("Main application is alive")
                else:
                    logger.warning(f"Main application returned status code {response.status}")
        except urllib.error.URLError as e:
            logger.warning(f"Could not connect to main application: {e}")
        except Exception as e:
            logger.error(f"Error pinging main application: {e}")
        
        # Sleep for a while before pinging again (5 minutes)
        time.sleep(300)

if __name__ == "__main__":
    logger.info("Starting keep-alive service for Telegram-X bot")
    
    # Start the keep-alive web server
    try:
        logger.info("Starting keep-alive web server...")
        run_keep_alive()
        logger.info("Keep-alive web server started")
        
        # Start a thread to periodically ping the main application
        pinger_thread = threading.Thread(target=ping_main_app, daemon=True)
        pinger_thread.start()
        logger.info("Pinger thread started")
        
        # Print instructions for users
        print("\n" + "="*60)
        print(" TELEGRAM-X BOT KEEP-ALIVE SERVICE")
        print("="*60)
        print("\nThis service helps keep your bot running 24/7 on Replit.")
        print("The keep-alive server is now running on port 8080.")
        print("\nTo ensure 24/7 uptime:")
        print("1. Set up a service like UptimeRobot to ping your Replit URL every 5-10 minutes")
        print("2. Make sure both Bot and Web workflows are running")
        print("\nPress Ctrl+C to stop this service")
        print("="*60 + "\n")
        
        # Keep the main thread alive
        while True:
            time.sleep(60)
            logger.info("Keep-alive service is running")
    
    except KeyboardInterrupt:
        logger.info("Keep-alive service stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        sys.exit(1)