"""
Status management for Telegram-X bot integration.
This module provides a way for the bot process to communicate its status
to the web interface process.
"""

import os
import json
import time
import threading
from logger import logger

# Path to the status file
STATUS_FILE = 'bot_status.json'

# Lock for thread-safe file operations
file_lock = threading.Lock()

# Default status
DEFAULT_STATUS = {
    "running": False,
    "last_error": None,
    "telegram_status": "Not started",
    "twitter_status": "Not connected",
    "last_tweet_time": None,
    "last_updated": time.time()
}

def get_status():
    """
    Get the current bot status from the status file.
    Returns the default status if the file doesn't exist.
    """
    with file_lock:
        try:
            if os.path.exists(STATUS_FILE):
                with open(STATUS_FILE, 'r') as f:
                    return json.load(f)
            return DEFAULT_STATUS.copy()
        except Exception as e:
            logger.error(f"Error reading status file: {e}")
            return DEFAULT_STATUS.copy()

def update_status(running=None, telegram_status=None, twitter_status=None, error=None, tweet_time=None):
    """
    Update the bot status file with the provided information.
    Only updates the fields that are provided (not None).
    """
    with file_lock:
        try:
            # Get current status
            current = get_status()
            
            # Update provided fields
            if running is not None:
                current["running"] = running
            if telegram_status is not None:
                current["telegram_status"] = telegram_status
            if twitter_status is not None:
                current["twitter_status"] = twitter_status
            if error is not None:
                current["last_error"] = str(error)
            if tweet_time is not None:
                current["last_tweet_time"] = tweet_time
                
            # Always update the timestamp
            current["last_updated"] = time.time()
            
            # Write back to file
            with open(STATUS_FILE, 'w') as f:
                json.dump(current, f, indent=2)
                
            logger.info(f"Status updated: {current['telegram_status']}, {current['twitter_status']}")
            return current
        except Exception as e:
            logger.error(f"Error writing status file: {e}")
            return None