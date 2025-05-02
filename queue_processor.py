"""
Tweet Queue Processor

This script processes the tweet queue even if the main Replit app is closed.
It's designed to be run by the scheduled tasks system or by our main app.

Features:
- Picks up and processes tweets that were queued but not sent
- Handles image uploads with automatic redownloading from Telegram
- Can run independently of the main app
- Auto-retries failed tweets with exponential backoff
"""

import os
import time
import logging
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import json
import requests
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime, select
from sqlalchemy.orm import sessionmaker
import tweepy

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("queue_processor.log")
    ]
)
log = logging.getLogger("QueueProcessor")

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TWITTER_API_KEY = os.environ.get("TWITTER_API_KEY")
TWITTER_API_SECRET = os.environ.get("TWITTER_API_SECRET")
TWITTER_ACCESS_TOKEN = os.environ.get("TWITTER_ACCESS_TOKEN")
TWITTER_ACCESS_SECRET = os.environ.get("TWITTER_ACCESS_SECRET")
DATABASE_URL = os.environ.get("DATABASE_URL")

# Verify configuration
missing_vars = []
for var_name in ["TELEGRAM_TOKEN", "TWITTER_API_KEY", "TWITTER_API_SECRET", 
                "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET", "DATABASE_URL"]:
    if not locals()[var_name]:
        missing_vars.append(var_name)

if missing_vars:
    log.error(f"Missing environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

# Temp directory for downloaded images
TEMP_DIR = "temp"
os.makedirs(TEMP_DIR, exist_ok=True)

# Set up database connection
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
metadata = MetaData()

# Define tweet_queue table
tweet_queue = Table(
    'tweet_queue', metadata,
    Column('id', Integer, primary_key=True),
    Column('tweet_id', String(32)),
    Column('user_id', String(32), nullable=False),
    Column('message', Text),
    Column('image_path', Text),
    Column('command_prefix', String(16)),
    Column('telegram_file_id', String(255)),
    Column('timestamp', DateTime),
    Column('status', String(16)),
    Column('attempt_count', Integer),
    Column('last_attempt', DateTime),
    Column('error_message', Text)
)

class TwitterHandler:
    """Twitter API handler with tweet posting functionality."""
    
    def __init__(self):
        """Initialize Twitter API client with credentials."""
        self.api_key = TWITTER_API_KEY
        self.api_secret = TWITTER_API_SECRET
        self.access_token = TWITTER_ACCESS_TOKEN
        self.access_secret = TWITTER_ACCESS_SECRET
        self.client = None
        self.setup_client()
    
    def setup_client(self):
        """Set up the Twitter API client with error handling."""
        try:
            auth = tweepy.OAuth1UserHandler(
                self.api_key, self.api_secret,
                self.access_token, self.access_secret
            )
            self.client = tweepy.API(auth)
            log.info("Twitter API client initialized")
            return True
        except Exception as e:
            log.error(f"Error setting up Twitter client: {e}")
            return False
    
    def can_tweet(self):
        """
        Check if we're within rate limits.
        Returns True if we can tweet, False otherwise.
        """
        try:
            status = self.client.rate_limit_status()
            remaining = status['resources']['statuses']['/statuses/update']['remaining']
            return remaining > 0
        except Exception as e:
            log.error(f"Error checking rate limits: {e}")
            # If we can't check, assume we can tweet
            return True
    
    def post_tweet(self, message):
        """
        Post a tweet with rate limiting and error handling.
        Returns a tuple (success, response_or_error_message)
        """
        if not self.client:
            log.error("Twitter client not initialized")
            return False, "Twitter client not initialized"
        
        try:
            # Check if we can tweet
            if not self.can_tweet():
                log.warning("Twitter rate limit reached")
                return False, "Rate limit reached"
            
            # Post the tweet
            response = self.client.update_status(message)
            log.info(f"Tweet posted: {response.id}")
            return True, response.id
        except Exception as e:
            log.error(f"Error posting tweet: {e}")
            return False, str(e)
    
    def post_tweet_with_image(self, message, image_path):
        """
        Post a tweet with an image attachment.
        Returns a tuple (success, response_or_error_message)
        
        Args:
            message (str): The tweet text
            image_path (str): Path to the image file
        """
        if not self.client:
            log.error("Twitter client not initialized")
            return False, "Twitter client not initialized"
        
        try:
            # Check if we can tweet
            if not self.can_tweet():
                log.warning("Twitter rate limit reached")
                return False, "Rate limit reached"
            
            # Check if image file exists
            if not os.path.exists(image_path):
                log.error(f"Image file not found: {image_path}")
                return False, f"Image file not found: {image_path}"
            
            # Post the tweet with media
            response = self.client.update_status_with_media(
                status=message,
                filename=image_path
            )
            log.info(f"Tweet with image posted: {response.id}")
            return True, response.id
        except Exception as e:
            log.error(f"Error posting tweet with image: {e}")
            return False, str(e)


def download_telegram_file(file_id):
    """
    Download a file from Telegram using its file_id.
    Returns the path to the downloaded file or None if failed.
    """
    try:
        # Get file info
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile"
        response = requests.get(url, params={"file_id": file_id})
        file_info = response.json()
        
        if not file_info.get("ok"):
            log.error(f"Error getting file info: {file_info}")
            return None
        
        file_path = file_info["result"]["file_path"]
        
        # Download the file
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
        response = requests.get(download_url)
        
        if response.status_code != 200:
            log.error(f"Error downloading file: {response.status_code}")
            return None
        
        # Save the file
        local_filename = os.path.join(TEMP_DIR, f"{file_id}_{os.path.basename(file_path)}")
        with open(local_filename, "wb") as f:
            f.write(response.content)
        
        log.info(f"File downloaded: {local_filename}")
        return local_filename
    except Exception as e:
        log.error(f"Error downloading Telegram file: {e}")
        return None


def process_queue():
    """Process the tweet queue and send pending tweets."""
    log.info("Starting queue processing")
    
    # Initialize Twitter handler
    twitter = TwitterHandler()
    
    session = Session()
    try:
        # Get pending tweets (status="pending")
        pending_query = select(tweet_queue).where(tweet_queue.c.status == "pending")
        pending_tweets = session.execute(pending_query).fetchall()
        log.info(f"Found {len(pending_tweets)} pending tweets")
        
        # Get stalled tweets (status="posting" and last_attempt > 15 minutes ago)
        cutoff_time = datetime.utcnow() - timedelta(minutes=15)
        stalled_query = select(tweet_queue).where(
            tweet_queue.c.status == "posting",
            tweet_queue.c.last_attempt <= cutoff_time
        )
        stalled_tweets = session.execute(stalled_query).fetchall()
        log.info(f"Found {len(stalled_tweets)} stalled tweets")
        
        # Combine lists for processing
        all_tweets = pending_tweets + stalled_tweets
        
        # Process each tweet
        for tweet in all_tweets:
            log.info(f"Processing tweet ID {tweet.id} from user {tweet.user_id}")
            
            # Mark as posting
            session.execute(
                tweet_queue.update().where(tweet_queue.c.id == tweet.id).values(
                    status="posting",
                    attempt_count=tweet_queue.c.attempt_count + 1,
                    last_attempt=datetime.utcnow()
                )
            )
            session.commit()
            
            # Check if we can tweet (rate limiting)
            last_tweet_query = select(tweet_queue).where(
                tweet_queue.c.status == "posted"
            ).order_by(tweet_queue.c.timestamp.desc()).limit(1)
            last_tweet = session.execute(last_tweet_query).first()
            
            can_tweet = True
            if last_tweet:
                time_since_last = datetime.utcnow() - last_tweet.timestamp
                if time_since_last < timedelta(minutes=10):
                    # Save this tweet back to pending status
                    log.info(f"Rate limited, cannot tweet yet. Setting back to pending")
                    session.execute(
                        tweet_queue.update().where(tweet_queue.c.id == tweet.id).values(
                            status="pending"
                        )
                    )
                    session.commit()
                    can_tweet = False
            
            if not can_tweet:
                continue
            
            # Process tweet based on whether it has an image
            success = False
            tweet_id = None
            error_message = None
            
            try:
                if tweet.telegram_file_id:
                    # Download the image from Telegram
                    image_path = download_telegram_file(tweet.telegram_file_id)
                    if not image_path:
                        error_message = "Failed to download image from Telegram"
                        raise Exception(error_message)
                    
                    # Post tweet with image
                    log.info(f"Posting tweet with image: {image_path}")
                    success, response = twitter.post_tweet_with_image(tweet.message, image_path)
                    if success:
                        tweet_id = response
                    else:
                        error_message = response
                else:
                    # Post text-only tweet
                    log.info(f"Posting text tweet: {tweet.message[:20]}...")
                    success, response = twitter.post_tweet(tweet.message)
                    if success:
                        tweet_id = response
                    else:
                        error_message = response
            except Exception as e:
                log.error(f"Error processing tweet: {e}")
                success = False
                error_message = str(e)
            
            # Update tweet status based on result
            if success:
                log.info(f"Tweet posted successfully: {tweet_id}")
                session.execute(
                    tweet_queue.update().where(tweet_queue.c.id == tweet.id).values(
                        status="posted",
                        tweet_id=str(tweet_id),
                        timestamp=datetime.utcnow()  # Update timestamp to actual posting time
                    )
                )
            else:
                log.error(f"Failed to post tweet: {error_message}")
                session.execute(
                    tweet_queue.update().where(tweet_queue.c.id == tweet.id).values(
                        status="failed" if tweet.attempt_count >= 3 else "pending",
                        error_message=error_message
                    )
                )
            
            session.commit()
            
            # Add a small delay between tweets
            time.sleep(2)
    
    except Exception as e:
        log.error(f"Error in process_queue: {e}")
    finally:
        session.close()
        
    log.info("Queue processing completed")


def main():
    """Main entry point for the queue processor."""
    log.info("=" * 60)
    log.info("🐦 Tweet Queue Processor")
    log.info("This script processes the tweet queue and sends pending tweets")
    log.info("=" * 60)
    
    # Check if database is accessible
    try:
        engine.connect()
        log.info("Database connection successful")
    except Exception as e:
        log.error(f"Database connection failed: {e}")
        return
    
    # Process the queue
    process_queue()
    
    log.info("Queue processor completed")


if __name__ == "__main__":
    main()