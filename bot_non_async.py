#!/usr/bin/env python3
"""
Non-async version of the Telegram bot that avoids event loop conflicts.
"""

import os
import sys
import logging
import time
from datetime import datetime
import json

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Status file for communication with web UI
STATUS_FILE = 'bot_status.json'

class SimpleBot:
    """Simple bot that checks for Telegram API access."""
    
    def __init__(self):
        """Initialize the bot."""
        self.telegram_token = os.getenv("TELEGRAM_TOKEN", "")
        if not self.telegram_token:
            self.update_status(False, "Telegram token not found", "Not configured")
            raise ValueError("TELEGRAM_TOKEN environment variable not set")
            
        self.twitter_api_key = os.getenv("TWITTER_API_KEY", "")
        self.twitter_api_secret = os.getenv("TWITTER_API_SECRET", "")
        self.twitter_access_token = os.getenv("TWITTER_ACCESS_TOKEN", "")
        self.twitter_access_secret = os.getenv("TWITTER_ACCESS_SECRET", "")
        
        if not all([self.twitter_api_key, self.twitter_api_secret, 
                   self.twitter_access_token, self.twitter_access_secret]):
            self.update_status(False, "Checking Telegram", "Twitter credentials missing")
            logger.warning("Some Twitter API credentials are missing")
    
    def update_status(self, running=False, telegram_status="Not started", 
                     twitter_status="Not connected", error=None):
        """Update status file for web UI."""
        status = {
            "running": running,
            "telegram_status": telegram_status,
            "twitter_status": twitter_status,
            "last_updated": time.time()
        }
        
        if error:
            status["last_error"] = str(error)
            
        try:
            with open(STATUS_FILE, 'w') as f:
                json.dump(status, f, indent=2)
            logger.info(f"Updated status: {telegram_status}, {twitter_status}")
        except Exception as e:
            logger.error(f"Failed to update status file: {e}")
            
    def check_telegram_api(self):
        """Check if we can connect to the Telegram Bot API."""
        import requests
        
        self.update_status(True, "Checking Telegram API...", "Pending")
        
        try:
            # Try to call getMe to verify token is valid
            url = f"https://api.telegram.org/bot{self.telegram_token}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    bot_username = data["result"]["username"]
                    logger.info(f"Successfully connected to Telegram API as @{bot_username}")
                    self.update_status(True, f"Connected as @{bot_username}", "Checking...")
                    return True
                else:
                    error = data.get("description", "Unknown error")
                    logger.error(f"Failed to connect to Telegram API: {error}")
                    self.update_status(False, f"Error: {error}", "Not checked", error)
            else:
                logger.error(f"Failed to connect to Telegram API. Status code: {response.status_code}")
                self.update_status(False, f"HTTP Error: {response.status_code}", "Not checked", 
                                  f"HTTP Error: {response.status_code}")
        except Exception as e:
            logger.error(f"Exception while connecting to Telegram API: {e}")
            self.update_status(False, f"Connection error: {e}", "Not checked", str(e))
            
        return False
            
    def check_twitter_api(self):
        """Check if we can connect to the Twitter API."""
        self.update_status(True, "Telegram OK", "Checking Twitter API...")
        
        try:
            import tweepy
            
            # Create client
            client = tweepy.Client(
                consumer_key=self.twitter_api_key,
                consumer_secret=self.twitter_api_secret,
                access_token=self.twitter_access_token,
                access_token_secret=self.twitter_access_secret
            )
            
            # Try to get our own user info to verify credentials
            me = client.get_me()
            
            if me.data:
                username = me.data.username
                logger.info(f"Successfully connected to Twitter API as @{username}")
                self.update_status(True, "Telegram OK", f"Connected as @{username}")
                return True
            else:
                logger.error("Failed to get user info from Twitter API")
                self.update_status(True, "Telegram OK", "Failed to get Twitter user info")
        except Exception as e:
            logger.error(f"Exception while connecting to Twitter API: {e}")
            self.update_status(True, "Telegram OK", f"Twitter error: {e}", str(e))
            
        return False
            
    def run(self):
        """Run the bot check process."""
        logger.info("Starting bot API check...")
        
        # First check Telegram API
        telegram_ok = self.check_telegram_api()
        if not telegram_ok:
            logger.error("Telegram API check failed, cannot continue")
            return False
            
        # Then check Twitter API
        twitter_ok = self.check_twitter_api()
        if not twitter_ok:
            logger.warning("Twitter API check failed, but Telegram is working")
            
        # Final status update
        if telegram_ok and twitter_ok:
            self.update_status(True, "Telegram connected", "Twitter connected")
            logger.info("All API checks passed!")
        elif telegram_ok:
            self.update_status(True, "Telegram connected", "Twitter failed")
            logger.info("Only Telegram API check passed")
        else:
            self.update_status(False, "Telegram failed", "Twitter not checked")
            logger.error("All API checks failed")
            
        return telegram_ok and twitter_ok

if __name__ == "__main__":
    try:
        bot = SimpleBot()
        success = bot.run()
        
        if success:
            logger.info("Bot is ready to use!")
            print("\n✅ Bot API check completed successfully!")
            print("You can now use the Telegram bot @YupienBot with the following commands:")
            print("  - /start - Start using the bot")
            print("  - /help - Show help information")
            print("  - /status - Check bot status")
            print("  - /tweet [message] - Post a tweet\n")
        else:
            logger.error("Bot API check failed!")
            print("\n❌ Bot API check failed! Check the logs for details.\n")
            
    except KeyboardInterrupt:
        logger.info("Bot check interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)