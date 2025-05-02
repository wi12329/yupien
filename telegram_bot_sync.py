#!/usr/bin/env python3
"""
Non-async version of the Telegram bot using polling.
This avoids event loop conflicts when run in a Replit environment.
"""

import os
import sys
import time
import json
import logging
import threading
import requests
import dotenv
from datetime import datetime

# Load environment variables from .env file
dotenv.load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_bot_sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Get the Telegram token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
if not TELEGRAM_TOKEN:
    logger.error("TELEGRAM_TOKEN not set")
    sys.exit(1)

# Status file
STATUS_FILE = 'bot_status.json'
COMMAND_FILE = 'bot_command.json'
RESPONSE_FILE = 'bot_response.json'
ALLOWED_USER_IDS = os.getenv("ALLOWED_USER_IDS", "")

# Command handlers
def start_command(update):
    """Handle /start command."""
    user_id = update['message']['from']['id']
    chat_id = update['message']['chat']['id']
    logger.info(f"Received /start command from user {user_id}")
    
    send_message(chat_id, 
        "Welcome to Telegram-X Integration Bot!\n\n"
        "Use -yupi [message] to post a tweet to X (Twitter).\n"
        "You can also use: -upnsby, -upnjkt, -upnvy, or -upnluv\n\n"
        "To post an image, just send a photo with any of the commands as caption.\n"
        "Example: Send a photo with caption \"-yupi Check out this photo!\"\n\n"
        "Use /help to see all available commands.\n"
        "Use /status to check bot status."
    )

def help_command(update):
    """Handle /help command."""
    user_id = update['message']['from']['id']
    chat_id = update['message']['chat']['id']
    logger.info(f"Received /help command from user {user_id}")
    
    send_message(chat_id, 
        "📚 *Telegram-X Integration Bot Help* 📚\n\n"
        "*Available Commands:*\n"
        "-yupi [message] - Post a tweet on X\n"
        "-upnsby [message] - Post a tweet on X\n"
        "-upnjkt [message] - Post a tweet on X\n"
        "-upnvy [message] - Post a tweet on X\n"
        "-upnluv [message] - Post a tweet on X\n"
        "/status - Check the bot status\n"
        "/help - Show this help message\n\n"
        "*Posting Images:*\n"
        "• Send an image with any of the commands as caption:\n"
        "  Example: Send a photo with caption \"-yupi Check out this photo!\"\n\n"
        "*Examples:*\n"
        "-yupi Hello, world! This is my tweet from Telegram.\n"
        "-upnjkt Quick update from Telegram!\n"
        "*Image Example:* Send a photo with caption \"-upnluv Look at this photo!\"\n\n"
        "*Notes:*\n"
        "- Tweets are limited to 280 characters\n"
        "- Rate limits apply as per X API restrictions",
        parse_mode="Markdown"
    )

def status_command(update):
    """Handle /status command."""
    user_id = update['message']['from']['id']
    chat_id = update['message']['chat']['id']
    logger.info(f"Received /status command from user {user_id}")
    
    # Check Telegram connection
    telegram_status = "✅ Telegram bot is online"
    
    # Read current status
    twitter_status = "❓ Unknown"
    
    try:
        if os.path.exists(STATUS_FILE):
            with open(STATUS_FILE, 'r') as f:
                status = json.load(f)
                twitter_status = status.get("twitter_status", "❓ Unknown")
                if twitter_status.startswith("Connected"):
                    twitter_status = "✅ " + twitter_status
                else:
                    twitter_status = "❌ " + twitter_status
    except Exception as e:
        logger.error(f"Error reading status: {e}")
    
    # Respond with status
    send_message(chat_id,
        "📊 *Bot Status Report* 📊\n\n"
        f"*Telegram:* {telegram_status}\n"
        f"*X (Twitter):* {twitter_status}\n",
        parse_mode="Markdown"
    )

def tweet_command(update):
    """Handle original /tweet command (kept for backward compatibility)."""
    user_id = update['message']['from']['id']
    chat_id = update['message']['chat']['id']
    message_text = update['message']['text']
    logger.info(f"Received /tweet command from user {user_id}")
    
    # Extract the tweet content
    parts = message_text.split(' ', 1)
    if len(parts) < 2 or not parts[1].strip():
        send_message(chat_id, "Please provide a message to tweet. Usage: /tweet [your message]")
        return
    
    tweet_text = parts[1].strip()
    
    # Send a processing message
    send_message(chat_id, "⏳ Processing your tweet...")
    
    # Write the command for the main process
    if write_command("tweet", user_id, tweet_text):
        # Wait for a response
        send_message(chat_id,
            "Your tweet has been sent for processing. "
            "You'll receive a confirmation shortly."
        )
    else:
        send_message(chat_id, "❌ Failed to process your tweet. Please try again later.")

def yupi_command(update):
    """Handle -yupi command."""
    user_id = update['message']['from']['id']
    chat_id = update['message']['chat']['id']
    message_text = update['message']['text']
    logger.info(f"Received -yupi command from user {user_id}")
    
    # Extract the tweet content (including the command)
    if not message_text.strip():
        send_message(chat_id, "Please provide a message to post. Usage: -yupi [your message]")
        return
    
    # Use the full message including the command
    tweet_text = message_text.strip()
    
    # Send a processing message
    send_message(chat_id, "⏳ Processing your post...")
    
    # Write the command for the main process
    if write_command("tweet", user_id, tweet_text):
        # Wait for a response
        send_message(chat_id,
            "Your post has been sent for processing. "
            "You'll receive a confirmation shortly."
        )
    else:
        send_message(chat_id, "❌ Failed to process your post. Please try again later.")

def upnsby_command(update):
    """Handle -upnsby command."""
    user_id = update['message']['from']['id']
    chat_id = update['message']['chat']['id']
    message_text = update['message']['text']
    logger.info(f"Received -upnsby command from user {user_id}")
    
    # Extract the tweet content (including the command)
    if not message_text.strip():
        send_message(chat_id, "Please provide a message to post. Usage: -upnsby [your message]")
        return
    
    # Use the full message including the command
    tweet_text = message_text.strip()
    
    # Send a processing message
    send_message(chat_id, "⏳ Processing your post...")
    
    # Write the command for the main process
    if write_command("tweet", user_id, tweet_text):
        # Wait for a response
        send_message(chat_id,
            "Your post has been sent for processing. "
            "You'll receive a confirmation shortly."
        )
    else:
        send_message(chat_id, "❌ Failed to process your post. Please try again later.")

def upnjkt_command(update):
    """Handle -upnjkt command."""
    user_id = update['message']['from']['id']
    chat_id = update['message']['chat']['id']
    message_text = update['message']['text']
    logger.info(f"Received -upnjkt command from user {user_id}")
    
    # Extract the tweet content (including the command)
    if not message_text.strip():
        send_message(chat_id, "Please provide a message to post. Usage: -upnjkt [your message]")
        return
    
    # Use the full message including the command
    tweet_text = message_text.strip()
    
    # Send a processing message
    send_message(chat_id, "⏳ Processing your post...")
    
    # Write the command for the main process
    if write_command("tweet", user_id, tweet_text):
        # Wait for a response
        send_message(chat_id,
            "Your post has been sent for processing. "
            "You'll receive a confirmation shortly."
        )
    else:
        send_message(chat_id, "❌ Failed to process your post. Please try again later.")

def upnvy_command(update):
    """Handle -upnvy command."""
    user_id = update['message']['from']['id']
    chat_id = update['message']['chat']['id']
    message_text = update['message']['text']
    logger.info(f"Received -upnvy command from user {user_id}")
    
    # Extract the tweet content (including the command)
    if not message_text.strip():
        send_message(chat_id, "Please provide a message to post. Usage: -upnvy [your message]")
        return
    
    # Use the full message including the command
    tweet_text = message_text.strip()
    
    # Send a processing message
    send_message(chat_id, "⏳ Processing your post...")
    
    # Write the command for the main process
    if write_command("tweet", user_id, tweet_text):
        # Wait for a response
        send_message(chat_id,
            "Your post has been sent for processing. "
            "You'll receive a confirmation shortly."
        )
    else:
        send_message(chat_id, "❌ Failed to process your post. Please try again later.")

def upnluv_command(update):
    """Handle -upnluv command."""
    user_id = update['message']['from']['id']
    chat_id = update['message']['chat']['id']
    message_text = update['message']['text']
    logger.info(f"Received -upnluv command from user {user_id}")
    
    # Extract the tweet content (including the command)
    if not message_text.strip():
        send_message(chat_id, "Please provide a message to post. Usage: -upnluv [your message]")
        return
    
    # Use the full message including the command
    tweet_text = message_text.strip()
    
    # Send a processing message
    send_message(chat_id, "⏳ Processing your post...")
    
    # Write the command for the main process
    if write_command("tweet", user_id, tweet_text):
        # Wait for a response
        send_message(chat_id,
            "Your post has been sent for processing. "
            "You'll receive a confirmation shortly."
        )
    else:
        send_message(chat_id, "❌ Failed to process your post. Please try again later.")

def process_photo_with_caption(update, caption_text):
    """Process a photo with a caption using our custom command prefixes."""
    user_id = update['message']['from']['id']
    chat_id = update['message']['chat']['id']
    logger.info(f"Processing photo with caption from user {user_id}")
    
    # Get the photo file_id (use the largest available size)
    photos = update['message']['photo']
    file_id = photos[-1]['file_id']  # Largest size
    
    # Keep the full caption text including the command prefix
    caption = caption_text.strip()
    
    # Send a processing message
    send_message(chat_id, "⏳ Processing your image post...")
    
    # Write the command for the main process
    if write_command("image", user_id, json.dumps({"file_id": file_id, "caption": caption})):
        send_message(chat_id,
            "Your image post has been sent for processing. "
            "You'll receive a confirmation shortly."
        )
    else:
        send_message(chat_id, "❌ Failed to process your image post. Please try again later.")

def image_command(update):
    """Handle /image command to post an image to Twitter."""
    user_id = update['message']['from']['id']
    chat_id = update['message']['chat']['id']
    logger.info(f"Received /image command from user {user_id}")
    
    # Check if this is a reply to a message with photo
    if 'reply_to_message' not in update['message'] or 'photo' not in update['message']['reply_to_message']:
        send_message(chat_id, "Please reply to a message with a photo using the /image command.")
        return
    
    # Get the photo file_id (use the largest available size)
    photos = update['message']['reply_to_message']['photo']
    file_id = photos[-1]['file_id']  # Largest size
    
    # Extract caption from the command
    message_text = update['message']['text']
    parts = message_text.split(' ', 1)
    caption = parts[1].strip() if len(parts) > 1 else ""
    
    # Send a processing message
    send_message(chat_id, "⏳ Processing your image post...")
    
    # Write the command for the main process
    if write_command("image", user_id, json.dumps({"file_id": file_id, "caption": caption})):
        send_message(chat_id,
            "Your image post has been sent for processing. "
            "You'll receive a confirmation shortly."
        )
    else:
        send_message(chat_id, "❌ Failed to process your image post. Please try again later.")

# Telegram API functions
def send_message(chat_id, text, parse_mode=None):
    """Send a message to a chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": chat_id,
        "text": text
    }
    
    if parse_mode:
        data["parse_mode"] = parse_mode
    
    try:
        response = requests.post(url, data=data, timeout=10)
        if response.status_code != 200:
            logger.error(f"Failed to send message: {response.text}")
        return response.json()
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return None

def get_updates(offset=None, timeout=30):
    """Get updates from Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": timeout}
    
    if offset:
        params["offset"] = offset
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Failed to get updates: {response.text}")
            return {"ok": False, "error": response.text}
    except Exception as e:
        logger.error(f"Error getting updates: {e}")
        return {"ok": False, "error": str(e)}

# Function to update status
def update_status(running=None, telegram_status=None, twitter_status=None, error=None):
    """Update the status file with current bot status."""
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
            logger.info(f"Status updated: {telegram_status or ''} {twitter_status or ''}")
    except Exception as e:
        logger.error(f"Error updating status: {e}")

# Function to write a command for the main process
def write_command(command, user_id, text=""):
    """Write a command to be processed by the main process."""
    try:
        with open(COMMAND_FILE, 'w') as f:
            json.dump({
                "command": command,
                "user_id": user_id,
                "text": text,
                "timestamp": time.time()
            }, f, indent=2)
        logger.info(f"Command written: {command}")
        return True
    except Exception as e:
        logger.error(f"Error writing command: {e}")
        return False

def process_update(update):
    """Process a single update from Telegram."""
    try:
        # Check if this is a message with text
        if 'message' in update:
            # Check if this message has a photo
            has_photo = 'photo' in update['message']
            
            # Get the text (either caption or message text)
            message_text = ""
            if 'text' in update['message']:
                message_text = update['message']['text']
            elif 'caption' in update['message']:
                message_text = update['message']['caption']
            
            # Skip empty messages
            if not message_text and not has_photo:
                return
                
            # Process slash commands
            if message_text.startswith('/'):
                command = message_text.split(' ')[0].split('@')[0].lower()
                
                # Route to the appropriate handler
                if command == '/start':
                    start_command(update)
                elif command == '/help':
                    help_command(update)
                elif command == '/status':
                    status_command(update)
                elif command == '/tweet':
                    tweet_command(update)
                elif command == '/image':
                    image_command(update)
                else:
                    # Unknown command
                    chat_id = update['message']['chat']['id']
                    send_message(chat_id, "Unknown command. Type /help for a list of commands.")
            
            # Check for custom command prefixes in text or caption
            elif message_text.startswith('-yupi'):
                if has_photo:
                    process_photo_with_caption(update, message_text)
                else:
                    yupi_command(update)
            elif message_text.startswith('-upnsby'):
                if has_photo:
                    process_photo_with_caption(update, message_text)
                else:
                    upnsby_command(update)
            elif message_text.startswith('-upnjkt'):
                if has_photo:
                    process_photo_with_caption(update, message_text)
                else:
                    upnjkt_command(update)
            elif message_text.startswith('-upnvy'):
                if has_photo:
                    process_photo_with_caption(update, message_text)
                else:
                    upnvy_command(update)
            elif message_text.startswith('-upnluv'):
                if has_photo:
                    process_photo_with_caption(update, message_text)
                else:
                    upnluv_command(update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")

# Function to check and process responses from the main process
def check_responses():
    """Check for responses from the main process and send them to users."""
    if not os.path.exists(RESPONSE_FILE):
        return
    
    try:
        # Read the response file
        with open(RESPONSE_FILE, 'r') as f:
            response_data = json.load(f)
        
        # Process the response
        user_id = response_data.get("user_id")
        response_type = response_data.get("type")
        response_text = response_data.get("text", "")
        timestamp = response_data.get("timestamp", 0)
        
        # Skip old responses (> 60 seconds)
        if time.time() - timestamp > 60:
            os.remove(RESPONSE_FILE)
            return
        
        logger.info(f"Processing response: {response_type} for user {user_id}")
        
        # Send the response to the user
        if response_type == "rate_limit":
            # Rate limit message
            send_message(user_id, response_text)
        elif response_type == "success":
            # Success message
            send_message(user_id, response_text)
        elif response_type == "error":
            # Error message
            send_message(user_id, f"❌ Error: {response_text}")
        
        # Remove the response file after processing
        os.remove(RESPONSE_FILE)
        
    except Exception as e:
        logger.error(f"Error processing response: {e}")
        # Don't remove the file on error to avoid losing responses

def check_allowed_user(update):
    """Check if the user is allowed to use the bot."""
    # Allow everyone to use the bot publicly
    logger.info("👥 All users are authorized to use this bot (public mode)")
    return True

def main():
    """Main function to start the bot."""
    update_status(running=True, telegram_status="Starting Telegram bot...")
    
    # Initial update ID
    last_update_id = None
    
    logger.info("Starting Telegram bot polling...")
    update_status(telegram_status="Telegram bot polling for updates")
    
    try:
        while True:
            # Get updates from Telegram
            result = get_updates(offset=last_update_id)
            
            if result["ok"]:
                updates = result["result"]
                
                if updates:
                    # Process all updates
                    for update in updates:
                        # Check if the user is allowed
                        if check_allowed_user(update):
                            process_update(update)
                        
                        # Update the last processed update ID
                        last_update_id = update["update_id"] + 1
            else:
                # If there was an error getting updates, log it and wait
                logger.error(f"Error getting updates: {result.get('error', 'Unknown error')}")
                update_status(telegram_status=f"Error getting updates: {result.get('error', 'Unknown error')}")
                time.sleep(5)
                continue
            
            # Check for responses from the main process
            check_responses()
            
            # Sleep briefly to avoid high CPU usage
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
        update_status(running=False, telegram_status="Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        update_status(running=False, telegram_status="Fatal error", error=str(e))

if __name__ == "__main__":
    main()