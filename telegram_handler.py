from telegram import Update, constants
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    ContextTypes,
    filters
)
import logging
import os
from datetime import datetime
from config import (
    TELEGRAM_TOKEN, ALLOWED_USER_IDS, TWEET_COMMAND, 
    HELP_COMMAND, STATUS_COMMAND, MAX_TWEETS_PER_HOUR
)
from models import TweetQueue, db

logger = logging.getLogger(__name__)

class TelegramHandler:
    def __init__(self, twitter_handler):
        """
        Initialize Telegram bot with handlers.
        
        Args:
            twitter_handler: An instance of TwitterHandler for posting tweets
        """
        self.application = None
        self.twitter_handler = twitter_handler
        
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        user_id = update.effective_user.id
        
        if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
            logger.warning(f"Unauthorized access attempt by user {user_id}")
            return
            
        await update.message.reply_text(
            "Welcome to Telegram-X Integration Bot!\n\n"
            f"Use /{TWEET_COMMAND} [message] to post a tweet to X (Twitter).\n"
            f"Use /{HELP_COMMAND} to see all available commands.\n"
            f"Use /{STATUS_COMMAND} to check bot status."
        )
        
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        user_id = update.effective_user.id
        
        if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
            logger.warning(f"Unauthorized access attempt by user {user_id}")
            return
            
        await update.message.reply_text(
            "📚 *Telegram-X Integration Bot Help* 📚\n\n"
            "*Available Commands:*\n"
            f"/{TWEET_COMMAND} [message] - Post a tweet on X\n"
            f"/{STATUS_COMMAND} - Check the bot status\n"
            f"/{HELP_COMMAND} - Show this help message\n\n"
            "*Examples:*\n"
            f"/{TWEET_COMMAND} Hello, world! This is my tweet from Telegram.\n\n"
            "*Notes:*\n"
            "- Tweets are limited to 280 characters\n"
            "- Rate limits apply as per X API restrictions",
            parse_mode="Markdown"
        )
        
    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command to check bot status."""
        user_id = update.effective_user.id
        
        if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
            logger.warning(f"Unauthorized access attempt by user {user_id}")
            return
            
        # Check Telegram connection
        telegram_status = "✅ Telegram bot is online"
        
        # Check Twitter connection
        twitter_success, twitter_message = self.twitter_handler.get_status()
        twitter_status = f"✅ {twitter_message}" if twitter_success else f"❌ {twitter_message}"
        
        # Check rate limiting
        can_tweet = self.twitter_handler.can_tweet()
        rate_status = "✅ Rate limit OK, tweets can be posted" if can_tweet else "⚠️ Rate limit reached, please wait"
        
        # Respond with full status
        await update.message.reply_text(
            "📊 *Bot Status Report* 📊\n\n"
            f"*Telegram:* {telegram_status}\n"
            f"*X (Twitter):* {twitter_status}\n"
            f"*Rate Limits:* {rate_status}\n\n"
            f"Recent tweets in last hour: {len(self.twitter_handler.last_tweets)}/{MAX_TWEETS_PER_HOUR}",
            parse_mode="Markdown"
        )
        
    async def tweet_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /tweet command to post a tweet."""
        user_id = str(update.effective_user.id)
        
        if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
            logger.warning(f"Unauthorized access attempt by user {user_id}: {update.message.text}")
            return
            
        # Check if we have any text to tweet
        if not context.args:
            await update.message.reply_text(
                f"Please provide a message to tweet. Usage: /{TWEET_COMMAND} [your message]"
            )
            return
            
        # Get the tweet content
        tweet_text = ' '.join(context.args)
        
        # Check if we can queue a tweet (rate limiting)
        if not TweetQueue.can_tweet_now():
            # Rate limited, show wait time
            wait_time = TweetQueue.time_until_next_available()
            formatted_time = TweetQueue.format_wait_time(wait_time)
            await update.message.reply_text(
                f"⏳ Rate limit in effect. Please wait {formatted_time} before tweeting again."
            )
            return
        
        # Send a processing message
        await update.message.reply_text("⏳ Adding your tweet to the queue...")
        
        try:
            # Add tweet to the queue
            queue_entry = TweetQueue.add_to_queue(user_id, tweet_text)
            
            # Try to post immediately if possible
            success, result = self.twitter_handler.post_tweet(tweet_text)
            
            if success:
                # Mark as posted in the queue
                TweetQueue.mark_as_posted(queue_entry.id, result)
                
                await update.message.reply_text(
                    f"✅ Tweet posted successfully!\nView it here: https://twitter.com/user/status/{result}"
                )
                logger.info(f"Tweet posted for user {user_id}: {tweet_text[:30]}...")
            else:
                # Tweet failed but is in the queue for retry
                TweetQueue.mark_as_failed(queue_entry.id, result)
                
                await update.message.reply_text(
                    f"⚠️ Tweet added to queue but immediate posting failed: {result}\n" +
                    "The system will retry posting automatically."
                )
                logger.warning(f"Tweet queued (failed immediate post) for user {user_id}: {result}")
        except Exception as e:
            logger.error(f"Error in tweet_command: {str(e)}")
            await update.message.reply_text(
                "❌ An error occurred while processing your tweet. Please try again later."
            )
    
    async def error_handler(self, update, context):
        """Log errors caused by updates."""
        logger.error(f"Update {update} caused error: {context.error}")
        
        # Notify user if possible
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "An error occurred while processing your request. Please try again later."
            )
    
    def setup_handlers(self):
        """Set up all command and message handlers."""
        # Create the Application
        self.application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler(HELP_COMMAND, self.help_command))
        self.application.add_handler(CommandHandler(TWEET_COMMAND, self.tweet_command))
        self.application.add_handler(CommandHandler(STATUS_COMMAND, self.status_command))
        
        # Add error handler
        self.application.add_error_handler(self.error_handler)
        
        logger.info("Telegram bot handlers set up successfully")
        
    async def run(self):
        """Start the bot."""
        logger.info("Starting Telegram bot...")
        try:
            # Make sure we've set up the application
            if not self.application:
                self.setup_handlers()
            
            # Start the bot with polling
            # This runs until the application is stopped with a signal
            await self.application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )
            logger.info("Telegram bot started successfully")
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {str(e)}")
            raise
            
    async def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stopping Telegram bot...")
        if self.application:
            await self.application.stop()
            logger.info("Telegram bot stopped successfully")
