#!/usr/bin/env python3
"""
Standalone Telegram bot script that handles commands and communicates with main process.
"""

import os
import sys
import time
import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("telegram_bot.log"),
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

# Function to update status
def update_status(running=None, telegram_status=None, twitter_status=None, error=None):
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
    except Exception as e:
        logger.error(f"Error updating status: {e}")

# Function to write a command for the main process
def write_command(command, user_id, text=""):
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

# Command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    user_id = update.effective_user.id
    logger.info(f"Received /start command from user {user_id}")
    
    await update.message.reply_text(
        "Welcome to Telegram-X Integration Bot!\n\n"
        "Use /tweet [message] to post a tweet to X (Twitter).\n"
        "Use /help to see all available commands.\n"
        "Use /status to check bot status."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    user_id = update.effective_user.id
    logger.info(f"Received /help command from user {user_id}")
    
    await update.message.reply_text(
        "📚 *Telegram-X Integration Bot Help* 📚\n\n"
        "*Available Commands:*\n"
        "/tweet [message] - Post a tweet on X\n"
        "/status - Check the bot status\n"
        "/help - Show this help message\n\n"
        "*Examples:*\n"
        "/tweet Hello, world! This is my tweet from Telegram.\n\n"
        "*Notes:*\n"
        "- Tweets are limited to 280 characters\n"
        "- Rate limits apply as per X API restrictions",
        parse_mode="Markdown"
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    user_id = update.effective_user.id
    logger.info(f"Received /status command from user {user_id}")
    
    # Check Telegram connection
    telegram_status = "✅ Telegram bot is online"
    
    # Read current status
    twitter_status = "❓ Unknown"
    rate_status = "❓ Unknown"
    
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
    await update.message.reply_text(
        "📊 *Bot Status Report* 📊\n\n"
        f"*Telegram:* {telegram_status}\n"
        f"*X (Twitter):* {twitter_status}\n",
        parse_mode="Markdown"
    )

async def tweet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tweet command."""
    user_id = update.effective_user.id
    logger.info(f"Received /tweet command from user {user_id}")
    
    # Check if we have any text to tweet
    if not context.args:
        await update.message.reply_text(
            "Please provide a message to tweet. Usage: /tweet [your message]"
        )
        return
    
    # Get the tweet content
    tweet_text = ' '.join(context.args)
    
    # Send a processing message
    await update.message.reply_text("⏳ Processing your tweet...")
    
    # Write the command for the main process
    if write_command("tweet", user_id, tweet_text):
        # Wait for a response (in a real implementation, you'd use a better mechanism)
        await update.message.reply_text(
            "Your tweet has been sent for processing. "
            "You'll receive a confirmation shortly."
        )
    else:
        await update.message.reply_text(
            "❌ Failed to process your tweet. Please try again later."
        )

async def error_handler(update, context):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error: {context.error}")
    
    # Notify user if possible
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "An error occurred while processing your request. Please try again later."
        )

async def main():
    """Run the bot."""
    # Update status to show we're starting
    update_status(True, "Starting Telegram bot...", None)
    
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("tweet", tweet_command))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    update_status(True, "Telegram bot started", None)
    logger.info("Starting bot...")
    
    # Run the bot until the application is stopped
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        import asyncio
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        update_status(False, "Telegram bot stopped by user", None)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        update_status(False, f"Telegram bot error: {str(e)}", None, str(e))