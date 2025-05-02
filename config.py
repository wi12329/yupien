import os
import logging

# Telegram Bot API Configuration
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable not set")

# X (Twitter) API Configuration
TWITTER_API_KEY = os.getenv("TWITTER_API_KEY", "")
TWITTER_API_SECRET = os.getenv("TWITTER_API_SECRET", "")
TWITTER_ACCESS_TOKEN = os.getenv("TWITTER_ACCESS_TOKEN", "")
TWITTER_ACCESS_SECRET = os.getenv("TWITTER_ACCESS_SECRET", "")

if not all([TWITTER_API_KEY, TWITTER_API_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_SECRET]):
    raise ValueError("One or more X (Twitter) API environment variables not set")

# Allowed Telegram user IDs (for security)
# Convert comma-separated string of user IDs to a list of integers
ALLOWED_USER_IDS = []

# For testing, we'll create a default set of allowed users if none are provided
allowed_ids_str = os.getenv("ALLOWED_USER_IDS", "")

# Make this more robust - for now we'll disable the restrictions
if True:  # Temporarily disable restrictions while testing
    logging.warning("⚠️ User ID restrictions temporarily disabled for testing.")
    ALLOWED_USER_IDS = []  # Empty list means no restrictions
else:
    # Original logic - kept for when we want to re-enable restrictions
    if not allowed_ids_str or allowed_ids_str.strip() == "":
        # No user IDs specified, allow all users (no restrictions)
        logging.warning("No ALLOWED_USER_IDS specified. Bot will accept commands from any user.")
        ALLOWED_USER_IDS = []  # Empty list means no restrictions
    else:
        try:
            # Handle if the string is just a single ID without commas
            if ',' in allowed_ids_str:
                ALLOWED_USER_IDS = [int(user_id.strip()) for user_id in allowed_ids_str.split(',') if user_id.strip()]
            else:
                # Try to convert a single value
                if allowed_ids_str.strip():
                    ALLOWED_USER_IDS = [int(allowed_ids_str.strip())]
            
            if ALLOWED_USER_IDS:
                logging.info(f"Bot will only accept commands from these user IDs: {ALLOWED_USER_IDS}")
            else:
                logging.warning("No valid user IDs found in ALLOWED_USER_IDS. Bot will accept commands from any user.")
        except ValueError:
            logging.warning("Invalid format for ALLOWED_USER_IDS. Using unrestricted mode.")
            ALLOWED_USER_IDS = []  # No restrictions

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = os.getenv("LOG_FILE", "telegram_twitter_bot.log")

# Command prefix settings
TWEET_COMMAND = "tweet"
HELP_COMMAND = "help"
STATUS_COMMAND = "status"

# Rate limiting to avoid Twitter API limits
MAX_TWEETS_PER_HOUR = 300  # Twitter API limits to about 300 tweets per 3 hours
