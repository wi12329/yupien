#!/usr/bin/env python3
"""
Robust Telegram-X integration bot that runs in the background.
This script handles Telegram bot commands and integration with Twitter/X.
"""

import os
import sys
import time
import json
import signal
import logging
import subprocess
import threading
import requests
from datetime import datetime, timedelta
import dotenv
from flask import Flask
from models import db, TweetQueue

# Load environment variables from .env file 
dotenv.load_dotenv()

# Initialize Flask app for database connection only (no routes)
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_twitter_bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Status file for communicating with the web interface
STATUS_FILE = 'bot_status.json'

# Twitter handler for posting tweets
class TwitterHandler:
    def __init__(self):
        """Initialize Twitter API client with credentials."""
        self.api_key = os.getenv("TWITTER_API_KEY", "")
        self.api_secret = os.getenv("TWITTER_API_SECRET", "")
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN", "")
        self.access_secret = os.getenv("TWITTER_ACCESS_SECRET", "")
        self.last_tweets = []  # For rate limiting
        self.max_tweets_per_hour = 300
        self.client = None
        self.setup_client()
        
    def setup_client(self):
        """Set up the Twitter API client with error handling."""
        try:
            import tweepy
            self.client = tweepy.Client(
                consumer_key=self.api_key,
                consumer_secret=self.api_secret,
                access_token=self.access_token,
                access_token_secret=self.access_secret
            )
            logger.info("Twitter API client initialized")
        except Exception as e:
            logger.error(f"Failed to set up Twitter client: {e}")
            self.client = None
    
    def can_tweet(self):
        """
        Check if we're within rate limits.
        Returns True if we can tweet, False otherwise.
        """
        # Clean up old tweets (more than 1 hour old)
        current_time = time.time()
        self.last_tweets = [t for t in self.last_tweets if (current_time - t) < 3600]
        
        # Check if we're under the limit
        return len(self.last_tweets) < self.max_tweets_per_hour
    
    def post_tweet(self, message):
        """
        Post a tweet with rate limiting and error handling.
        Returns a tuple (success, response_or_error_message)
        """
        if not self.client:
            return False, "Twitter API client not initialized"
        
        # Check rate limiting
        if not self.can_tweet():
            return False, f"Rate limit reached ({self.max_tweets_per_hour} tweets per hour)"
        
        try:
            # Post the tweet
            response = self.client.create_tweet(text=message)
            
            # Record this tweet for rate limiting
            self.last_tweets.append(time.time())
            
            # Return the tweet URL
            tweet_id = response.data['id']
            tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"
            logger.info(f"Tweet posted: {message[:30]}... [{tweet_id}]")
            return True, tweet_url
        except Exception as e:
            logger.error(f"Error posting tweet: {e}")
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
            return False, "Twitter API client not initialized"
        
        # Check rate limiting
        if not self.can_tweet():
            return False, f"Rate limit reached ({self.max_tweets_per_hour} tweets per hour)"
        
        try:
            import tweepy
            # First upload the media
            auth = tweepy.OAuth1UserHandler(
                self.api_key, self.api_secret,
                self.access_token, self.access_secret
            )
            api = tweepy.API(auth)
            
            # Upload the media
            uploaded_media = api.media_upload(image_path)
            media_id = uploaded_media.media_id_string
            
            # Post the tweet with the media
            response = self.client.create_tweet(
                text=message,
                media_ids=[media_id]
            )
            
            # Record this tweet for rate limiting
            self.last_tweets.append(time.time())
            
            # Return the tweet URL
            tweet_id = response.data['id']
            tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"
            logger.info(f"Tweet with image posted: {message[:30]}... [{tweet_id}]")
            return True, tweet_url
        except Exception as e:
            logger.error(f"Error posting tweet with image: {e}")
            return False, str(e)
    
    def get_status(self):
        """
        Get current Twitter account status for diagnostics.
        Returns a tuple (success, info_or_error_message)
        """
        if not self.client:
            return False, "Twitter API client not initialized"
        
        try:
            # Try to get our own user info
            me = self.client.get_me()
            if me.data:
                username = me.data.username
                return True, f"Connected as @{username}"
            else:
                return False, "Failed to get Twitter user info"
        except Exception as e:
            logger.error(f"Error getting Twitter status: {e}")
            return False, str(e)

# Function to update the status file
def update_status(running=None, telegram_status=None, twitter_status=None, error=None):
    """Update the status file that's used by the web interface."""
    try:
        # Read current status
        current_status = {
            "running": False,
            "telegram_status": "Not started",
            "twitter_status": "Not connected",
            "last_error": None,
            "last_updated": time.time()
        }
        
        if os.path.exists(STATUS_FILE):
            try:
                with open(STATUS_FILE, 'r') as f:
                    current_status = json.load(f)
            except:
                pass
        
        # Update with new values
        if running is not None:
            current_status["running"] = running
        if telegram_status is not None:
            current_status["telegram_status"] = telegram_status
        if twitter_status is not None:
            current_status["twitter_status"] = twitter_status
        if error is not None:
            current_status["last_error"] = str(error)
        
        current_status["last_updated"] = time.time()
        
        # Write back to file
        with open(STATUS_FILE, 'w') as f:
            json.dump(current_status, f, indent=2)
        
        if telegram_status or twitter_status:
            logger.info(f"Status updated: " +
                       f"{telegram_status if telegram_status else current_status['telegram_status']}, " +
                       f"{twitter_status if twitter_status else current_status['twitter_status']}")
    except Exception as e:
        logger.error(f"Error updating status: {e}")

# Function to download image from Telegram
def download_telegram_image(file_id):
    """
    Download an image from Telegram using its file_id.
    Returns the path to the downloaded file.
    """
    token = os.getenv("TELEGRAM_TOKEN", "")
    if not token:
        logger.error("TELEGRAM_TOKEN not set")
        return None
    
    try:
        # Get file path from Telegram
        file_url = f"https://api.telegram.org/bot{token}/getFile?file_id={file_id}"
        response = requests.get(file_url)
        
        if response.status_code != 200:
            logger.error(f"Failed to get file info: {response.text}")
            return None
        
        file_path = response.json()['result']['file_path']
        
        # Download the file
        download_url = f"https://api.telegram.org/file/bot{token}/{file_path}"
        image_response = requests.get(download_url)
        
        if image_response.status_code != 200:
            logger.error(f"Failed to download file: {image_response.status_code}")
            return None
        
        # Create temp directory if it doesn't exist
        if not os.path.exists("temp"):
            os.makedirs("temp")
            
        # Save the file
        file_extension = os.path.splitext(file_path)[1]
        local_file_path = f"temp/image_{int(time.time())}{file_extension}"
        
        with open(local_file_path, 'wb') as f:
            f.write(image_response.content)
            
        logger.info(f"Downloaded image to {local_file_path}")
        return local_file_path
    
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None

# Run the Telegram bot in a separate process
def run_telegram_bot():
    """
    Run the Telegram bot using our non-async implementation.
    This runs in a subprocess to avoid event loop conflicts.
    """
    # Start the bot in a subprocess
    try:
        update_status(running=True, telegram_status="Starting Telegram bot subprocess...")
        logger.info("Starting Telegram bot subprocess...")
        
        # Run the non-async bot script
        process = subprocess.Popen([sys.executable, "telegram_bot_sync.py"])
        
        logger.info(f"Telegram bot subprocess started with PID {process.pid}")
        update_status(telegram_status=f"Telegram bot running (PID: {process.pid})")
        
        # Return the process for monitoring
        return process
    except Exception as e:
        logger.error(f"Error starting Telegram bot subprocess: {e}")
        update_status(error=f"Failed to start Telegram bot: {str(e)}")
        return None

# File to store tweet commands from the Telegram bot
COMMAND_FILE = 'bot_command.json'

# File to store responses for the Telegram bot
RESPONSE_FILE = 'bot_response.json'

# Function to write a response for the Telegram bot
def write_response(user_id, response_type, response_text):
    """Write a response for the Telegram bot to send to the user."""
    try:
        with open(RESPONSE_FILE, 'w') as f:
            json.dump({
                "user_id": user_id,
                "type": response_type,
                "text": response_text,
                "timestamp": time.time()
            }, f, indent=2)
        logger.info(f"Response written: {response_type}")
        return True
    except Exception as e:
        logger.error(f"Error writing response: {e}")
        return False

# Function to handle commands from Telegram bot
def process_commands(twitter_handler):
    """Process commands from the Telegram bot."""
    if not os.path.exists(COMMAND_FILE):
        return
    
    try:
        # Read the command file
        with open(COMMAND_FILE, 'r') as f:
            command_data = json.load(f)
        
        # Process based on command type
        command = command_data.get("command")
        user_id = command_data.get("user_id")
        text = command_data.get("text", "")
        timestamp = command_data.get("timestamp", 0)
        
        # Skip old commands (> 60 seconds)
        if time.time() - timestamp > 60:
            os.remove(COMMAND_FILE)
            return
        
        logger.info(f"Processing command: {command} from user {user_id}")
        
        if command == "tweet":
            # Check if we can tweet now based on the 10-minute queue
            with app.app_context():
                if not TweetQueue.can_tweet_now():
                    wait_time = TweetQueue.time_until_next_available()
                    formatted_wait = TweetQueue.format_wait_time(wait_time)
                    error_msg = f"Rate limit: Please wait {formatted_wait} before posting again"
                    
                    # Update status to show we're rate limited
                    update_status(
                        twitter_status="Rate limited - waiting",
                        error=error_msg
                    )
                    logger.warning(f"Rate limited tweet for user {user_id}: {error_msg}")
                    
                    # Write a response for the Telegram bot to inform the user
                    write_response(
                        user_id=user_id,
                        response_type="rate_limit",
                        response_text=f"⏰ Rate limit exceeded. Please wait {formatted_wait} before posting again."
                    )
                    
                    # Delete the command file
                    os.remove(COMMAND_FILE)
                    return
                
                # Add to queue first
                queue_entry = TweetQueue.add_to_queue(user_id, text)
                
                # Post the tweet
                success, result = twitter_handler.post_tweet(text)
                
                # Update status with the result
                if success:
                    # Mark as posted in the queue
                    tweet_id = result.split('/')[-1] if '/' in result else None
                    TweetQueue.mark_as_posted(queue_entry.id, tweet_id)
                    
                    update_status(
                        twitter_status=f"Tweet posted: {text[:20]}..."
                    )
                    logger.info(f"Tweet posted for user {user_id}: {text[:30]}...")
                    
                    # Write a success response for the Telegram bot to inform the user
                    write_response(
                        user_id=user_id,
                        response_type="success",
                        response_text=f"✅ Your tweet has been posted\n\nView it here: {result}"
                    )
                else:
                    # Mark as failed in the queue
                    TweetQueue.mark_as_failed(queue_entry.id, error=result)
                    
                    update_status(
                        twitter_status="Failed to post tweet",
                        error=result
                    )
                    logger.warning(f"Failed tweet for user {user_id}: {result}")
                    
                    # Write an error response for the Telegram bot to inform the user
                    write_response(
                        user_id=user_id,
                        response_type="error",
                        response_text=f"Could not post your tweet: {result}"
                    )
        
        elif command == "image":
            # This command is for posting an image with a caption
            try:
                # Check if we can tweet now based on the 10-minute queue
                with app.app_context():
                    if not TweetQueue.can_tweet_now():
                        wait_time = TweetQueue.time_until_next_available()
                        formatted_wait = TweetQueue.format_wait_time(wait_time)
                        error_msg = f"Rate limit: Please wait {formatted_wait} before posting again"
                        
                        # Update status to show we're rate limited
                        update_status(
                            twitter_status="Rate limited - waiting",
                            error=error_msg
                        )
                        logger.warning(f"Rate limited image tweet for user {user_id}: {error_msg}")
                        
                        # Write a response for the Telegram bot to inform the user
                        write_response(
                            user_id=user_id,
                            response_type="rate_limit",
                            response_text=f"⏰ Rate limit exceeded. Please wait {formatted_wait} before posting again."
                        )
                        
                        # Delete the command file
                        os.remove(COMMAND_FILE)
                        return
                
                # Parse the JSON string from the text field
                image_data = json.loads(text)
                file_id = image_data.get("file_id")
                caption = image_data.get("caption", "")
                
                # Download the image from Telegram
                logger.info(f"Downloading image with file_id: {file_id}")
                image_path = download_telegram_image(file_id)
                
                if not image_path:
                    logger.error("Failed to download image")
                    update_status(
                        twitter_status="Failed to download image",
                        error="Could not download image from Telegram"
                    )
                    
                    # Notify the user of the error
                    write_response(
                        user_id=user_id,
                        response_type="error",
                        response_text="Could not download your image from Telegram. Please try again with a different image."
                    )
                    
                    os.remove(COMMAND_FILE)
                    return
                
                # Add to queue first
                with app.app_context():
                    queue_entry = TweetQueue.add_to_queue(user_id, caption)
                
                # Post the tweet with the image
                success, result = twitter_handler.post_tweet_with_image(caption, image_path)
                
                # Clean up the temporary image file
                try:
                    os.remove(image_path)
                except:
                    pass
                
                # Update status with the result
                with app.app_context():
                    if success:
                        # Mark as posted in the queue
                        tweet_id = result.split('/')[-1] if '/' in result else None
                        TweetQueue.mark_as_posted(queue_entry.id, tweet_id)
                        
                        update_status(
                            twitter_status=f"Image tweet posted: {caption[:20]}..."
                        )
                        logger.info(f"Image tweet posted for user {user_id}: {caption[:30]}...")
                        
                        # Write a success response for the Telegram bot to inform the user
                        write_response(
                            user_id=user_id,
                            response_type="success",
                            response_text=f"✅ Your image tweet has been posted\n\nView it here: {result}"
                        )
                    else:
                        # Mark as failed in the queue
                        TweetQueue.mark_as_failed(queue_entry.id, error=result)
                        
                        update_status(
                            twitter_status="Failed to post image tweet",
                            error=result
                        )
                        logger.warning(f"Failed image tweet for user {user_id}: {result}")
                        
                        # Write an error response for the Telegram bot to inform the user
                        write_response(
                            user_id=user_id,
                            response_type="error",
                            response_text=f"Could not post your image tweet: {result}"
                        )
            
            except Exception as e:
                logger.error(f"Error processing image tweet: {e}")
                update_status(
                    twitter_status="Error processing image tweet",
                    error=str(e)
                )
                
                # Notify the user of the error
                try:
                    write_response(
                        user_id=user_id,
                        response_type="error",
                        response_text="An error occurred while processing your image tweet. Please try again later."
                    )
                except:
                    pass  # Can't do much if we can't even write a response
        
        # Remove the command file after processing
        os.remove(COMMAND_FILE)
        
    except Exception as e:
        logger.error(f"Error processing commands: {e}")
        # Don't remove the file on error to avoid losing commands
        
        # Try to notify the user about the error if we have user_id
        try:
            # Read the command file to get the user_id
            if os.path.exists(COMMAND_FILE):
                with open(COMMAND_FILE, 'r') as f:
                    cmd_data = json.load(f)
                    user_id = cmd_data.get("user_id")
                    if user_id:
                        write_response(
                            user_id=user_id,
                            response_type="error",
                            response_text="An error occurred while processing your request. Please try again later."
                        )
        except:
            pass  # Can't do much if we can't write a response

# Main function
def main():
    """Main entry point for the Telegram-X integration bot."""
    logger.info("Starting Telegram-X integration bot")
    
    # Initialize Twitter handler
    twitter_handler = TwitterHandler()
    
    # Update initial status
    twitter_status = "Not connected"
    try:
        twitter_success, twitter_message = twitter_handler.get_status()
        if twitter_success:
            twitter_status = twitter_message
        else:
            # If Twitter is rate-limiting us, still consider it connected
            if "429" in str(twitter_message) or "rate limit" in str(twitter_message).lower():
                twitter_status = "Connected (rate limited)"
    except Exception as e:
        logger.error(f"Error checking Twitter status: {str(e)}")
        if "429" in str(e) or "rate limit" in str(e).lower():
            twitter_status = "Connected (rate limited)"
        else:
            twitter_status = f"Connection error: {str(e)[:50]}..."
    
    update_status(
        running=True,
        telegram_status="Initializing...",
        twitter_status=twitter_status
    )
    
    # Start the Telegram bot in a subprocess
    telegram_process = run_telegram_bot()
    if not telegram_process:
        logger.error("Failed to start Telegram bot subprocess")
        update_status(
            running=False,
            telegram_status="Failed to start",
            error="Could not start Telegram bot subprocess"
        )
        return
    
    # Set up signal handling for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        update_status(
            running=False,
            telegram_status="Shutting down...",
            twitter_status="Shutting down..."
        )
        
        # Terminate the Telegram bot process
        if telegram_process and telegram_process.poll() is None:
            logger.info(f"Terminating Telegram bot process (PID: {telegram_process.pid})...")
            telegram_process.terminate()
            telegram_process.wait()
        
        # Final status update
        update_status(
            running=False,
            telegram_status="Offline",
            twitter_status="Offline"
        )
        
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Main loop - check for commands and monitor the Telegram bot process
    try:
        logger.info("Entering main loop")
        
        while True:
            # Process any commands from the Telegram bot
            process_commands(twitter_handler)
            
            # Check if the Telegram bot process is still running
            if telegram_process.poll() is not None:
                logger.warning(f"Telegram bot process exited with code {telegram_process.returncode}")
                update_status(
                    telegram_status=f"Process exited (code: {telegram_process.returncode})",
                    error=f"Telegram bot process exited unexpectedly with code {telegram_process.returncode}"
                )
                
                # Restart the Telegram bot
                logger.info("Restarting Telegram bot process...")
                telegram_process = run_telegram_bot()
                if not telegram_process:
                    logger.error("Failed to restart Telegram bot process")
                    update_status(
                        telegram_status="Failed to restart",
                        error="Could not restart Telegram bot process"
                    )
                    break
            
            # Sleep for a bit to avoid high CPU usage
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        logger.error(f"Unhandled exception in main loop: {e}", exc_info=True)
        update_status(
            running=False,
            error=f"Unhandled exception: {str(e)}"
        )
        
        # Terminate the Telegram bot process
        if telegram_process and telegram_process.poll() is None:
            telegram_process.terminate()
            telegram_process.wait()

if __name__ == "__main__":
    main()