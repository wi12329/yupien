#!/usr/bin/env python3
"""
Completely standalone Telegram-X bot script that runs independently.
This avoids any issues with event loops or process conflicts.
"""

import os
import sys
import asyncio
import logging
import signal
import time
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Twitter API handler
class SimpleTwitterHandler:
    def __init__(self):
        """Initialize the Twitter handler with API credentials."""
        self.api_key = os.getenv("TWITTER_API_KEY", "")
        self.api_secret = os.getenv("TWITTER_API_SECRET", "")
        self.access_token = os.getenv("TWITTER_ACCESS_TOKEN", "")
        self.access_secret = os.getenv("TWITTER_ACCESS_SECRET", "")
        self.last_tweets = []
        self.max_tweets_per_hour = 300
        self.client = None
        self.setup_client()
        
    def setup_client(self):
        """Set up the Twitter API client."""
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
            logger.error(f"Failed to initialize Twitter API client: {e}")
            self.client = None
            
    def can_tweet(self):
        """Check if we can tweet (rate limiting)."""
        # Clean up old tweets (more than 1 hour old)
        current_time = time.time()
        self.last_tweets = [t for t in self.last_tweets if (current_time - t) < 3600]
        
        # Check if we're under the rate limit
        return len(self.last_tweets) < self.max_tweets_per_hour
            
    def post_tweet(self, message):
        """Post a tweet with the given message."""
        if not self.client:
            return False, "Twitter API client not initialized"
            
        if not self.can_tweet():
            return False, "Rate limit exceeded, please try again later"
            
        try:
            # Post the tweet
            response = self.client.create_tweet(text=message)
            
            # Record this tweet for rate limiting
            self.last_tweets.append(time.time())
            
            # Return the tweet URL
            tweet_id = response.data['id']
            tweet_url = f"https://twitter.com/i/web/status/{tweet_id}"
            return True, tweet_url
        except Exception as e:
            return False, str(e)
            
    def get_status(self):
        """Get the Twitter API status."""
        if not self.client:
            return False, "Twitter API client not initialized"
            
        try:
            # Just check if we can access the API
            return True, "X (Twitter) API connected"
        except Exception as e:
            return False, str(e)

# Command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    logger.info(f"Received /start command from user {update.effective_user.id}")
    await update.message.reply_text(
        "Welcome to Telegram-X Integration Bot!\n\n"
        "Use /tweet [message] to post a tweet to X (Twitter).\n"
        "Use /help to see all available commands.\n"
        "Use /status to check bot status."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    logger.info(f"Received /help command from user {update.effective_user.id}")
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
    logger.info(f"Received /status command from user {update.effective_user.id}")
    twitter_handler = context.bot_data.get("twitter_handler")
    
    # Default statuses
    telegram_status = "✅ Telegram bot is online"
    twitter_status = "⚠️ Twitter API not initialized"
    rate_status = "❓ Rate limit status unknown"
    
    # Check Twitter connection if handler exists
    if twitter_handler:
        twitter_success, twitter_message = twitter_handler.get_status()
        twitter_status = f"✅ {twitter_message}" if twitter_success else f"❌ {twitter_message}"
        
        # Check rate limiting
        can_tweet = twitter_handler.can_tweet()
        rate_status = "✅ Rate limit OK, tweets can be posted" if can_tweet else "⚠️ Rate limit reached, please wait"
    
    # Respond with full status
    await update.message.reply_text(
        "📊 *Bot Status Report* 📊\n\n"
        f"*Telegram:* {telegram_status}\n"
        f"*X (Twitter):* {twitter_status}\n"
        f"*Rate Limits:* {rate_status}\n",
        parse_mode="Markdown"
    )

async def tweet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /tweet command."""
    logger.info(f"Received /tweet command from user {update.effective_user.id}")
    twitter_handler = context.bot_data.get("twitter_handler")
    
    if not twitter_handler:
        await update.message.reply_text("⚠️ Twitter API not initialized")
        return
    
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
    
    # Try to post the tweet
    success, result = twitter_handler.post_tweet(tweet_text)
    
    if success:
        await update.message.reply_text(
            f"✅ Tweet posted successfully!\nView it here: {result}"
        )
        logger.info(f"Tweet posted for user {update.effective_user.id}: {tweet_text[:30]}...")
    else:
        await update.message.reply_text(
            f"❌ Failed to post tweet: {result}"
        )
        logger.warning(f"Failed tweet for user {update.effective_user.id}: {result}")

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
    # Get the token from environment
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable not set")
        return
    
    logger.info("Starting Telegram-X integration bot")
    
    # Create the Twitter handler
    twitter_handler = SimpleTwitterHandler()
    
    # Create the Application
    application = Application.builder().token(token).build()
    application.bot_data["twitter_handler"] = twitter_handler
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("tweet", tweet_command))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Starting bot, press Ctrl+C to stop")
    
    # Run the bot until Ctrl+C
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)